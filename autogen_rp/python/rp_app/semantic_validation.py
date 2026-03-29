import json
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core.model_context import BufferedChatCompletionContext

MODEL_CONTEXT_BUFFER_SIZE = 1
DIRECT_ADDRESS_ISSUE_PREFIX = "Selected actor ignored direct address preference"
REPEAT_SPOTLIGHT_ISSUE = (
    "Selected actor repeats the most recent spotlight when alternatives exist"
)
SEMANTIC_SELECTION_ISSUE = (
    "Semantic turn_selection review did not support selected actor for current beat"
)

SEMANTIC_VALIDATOR_SYSTEM_MESSAGE = """You are a semantic validator for a structured roleplay system.

Return JSON only.
Be conservative about flagging contradictions.
Do not infer that someone left the scene from phrases like 'left side', 'looked away', 'peeled away', or similarly local phrasing.
must_remain means the character stays in the cast selection pool; they may be offstage (hallway, another room, etc.) without violating presence.
Only treat scene-presence violations as real when the text falsely claims another must_remain character is absent from the scene (e.g. denying they are present when they are), not when someone merely moves off-camera or steps into an adjacent space.
Treat direct-address failures as real only when the trigger clearly makes one available actor the natural addressed responder.
Treat narrator failures as real only when the render changes quoted dialogue, invents consequential actions for other characters, or materially rewrites the acting character's move.
"""


def _build_validator_agent(model_client: Any) -> AssistantAgent:
    return AssistantAgent(
        name="SemanticValidator",
        description="Semantic validator for scene presence, turn routing, and narrator render integrity.",
        system_message=SEMANTIC_VALIDATOR_SYSTEM_MESSAGE,
        model_client=model_client,
        model_context=BufferedChatCompletionContext(
            buffer_size=MODEL_CONTEXT_BUFFER_SIZE
        ),
    )


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extract_json_object_text(raw_response: str) -> str:
    stripped = str(raw_response or "").strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return stripped[start : end + 1]
    return stripped


async def _run_semantic_validation(
    *,
    model_client: Any,
    cancellation_token: Any,
    prompt: str,
) -> dict[str, Any] | None:
    if model_client is None:
        return None

    agent = _build_validator_agent(model_client)
    result = await agent.on_messages(
        [TextMessage(content=prompt, source="system")], cancellation_token
    )
    raw_response = str(result.chat_message.content or "")
    json_text = _extract_json_object_text(raw_response)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        return {
            "parse_error": str(exc),
            "raw_response": raw_response,
        }

    if not isinstance(data, dict):
        return {
            "parse_error": "Semantic validator response was not a JSON object",
            "raw_response": raw_response,
        }

    data["raw_response"] = raw_response
    return data


def reconcile_turn_selection_issues(
    issues: list[str],
    semantic_assessment: dict[str, Any] | None,
) -> list[str]:
    if semantic_assessment is None:
        return issues

    reconciled = [
        issue
        for issue in issues
        if semantic_assessment.get("should_flag_direct_address_miss")
        or not issue.startswith(DIRECT_ADDRESS_ISSUE_PREFIX)
    ]

    if semantic_assessment.get("should_flag_direct_address_miss"):
        direct_address_target = str(
            semantic_assessment.get("direct_address_target", "") or ""
        ).strip()
        issue = (
            f"{DIRECT_ADDRESS_ISSUE_PREFIX} for {direct_address_target}"
            if direct_address_target
            else DIRECT_ADDRESS_ISSUE_PREFIX
        )
        if issue not in reconciled:
            reconciled.append(issue)

    if (
        semantic_assessment.get("should_flag_repeat_spotlight")
        and REPEAT_SPOTLIGHT_ISSUE not in reconciled
    ):
        reconciled.append(REPEAT_SPOTLIGHT_ISSUE)

    if (
        not semantic_assessment.get("supports_selected_actor", True)
        and SEMANTIC_SELECTION_ISSUE not in reconciled
    ):
        reconciled.append(SEMANTIC_SELECTION_ISSUE)

    return reconciled


def should_override_presence_rejection(
    rejection_reason: str,
    semantic_assessment: dict[str, Any] | None,
) -> bool:
    if not rejection_reason.startswith("[SCENE_PRESENCE]"):
        return False
    if not isinstance(semantic_assessment, dict):
        return False
    return bool(semantic_assessment.get("is_valid"))


def should_use_narrator_fallback(semantic_assessment: dict[str, Any] | None) -> bool:
    if not isinstance(semantic_assessment, dict):
        return False
    return bool(semantic_assessment.get("should_use_fallback"))


async def assess_presence_violation_semantics(
    *,
    model_client: Any,
    speaker: str,
    content: str,
    move: dict[str, Any] | None,
    scene_state: dict[str, Any] | None,
    rejection_reason: str,
    cancellation_token: Any,
) -> dict[str, Any] | None:
    payload = {
        "speaker": speaker,
        "rejection_reason": rejection_reason,
        "scene_state": scene_state or {},
        "attempted_move": {
            "content": content,
            "action": str((move or {}).get("action", "") or ""),
            "dialogue": str((move or {}).get("dialogue", "") or ""),
            "motivation": (move or {}).get("motivation", {}),
        },
    }
    prompt = (
        "Assess whether the attempted move actually violates must_remain obligations "
        "(must_remain = character must stay in the cast selection pool; moving offstage or into an adjacent space is allowed). "
        "Return JSON only with keys is_valid, explicit_absence_claim, explicit_exit_attempt, reason, confidence.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    data = await _run_semantic_validation(
        model_client=model_client,
        cancellation_token=cancellation_token,
        prompt=prompt,
    )
    if data is None:
        return None

    return {
        "is_valid": bool(data.get("is_valid")),
        "explicit_absence_claim": bool(data.get("explicit_absence_claim")),
        "explicit_exit_attempt": bool(data.get("explicit_exit_attempt")),
        "reason": str(data.get("reason", "") or ""),
        "confidence": _coerce_float(data.get("confidence")),
        "parse_error": str(data.get("parse_error", "") or ""),
        "raw_response": str(data.get("raw_response", "") or ""),
    }


async def assess_turn_selection_decision_semantics(
    *,
    model_client: Any,
    trigger_text: str,
    participant_names: list[str],
    available_actors: list[str],
    decision: dict[str, Any],
    spotlight_history: list[str],
    scene_state: dict[str, Any] | None,
    recent_dialogue_history: list[dict[str, Any]],
    cancellation_token: Any,
    beat_shift_active: bool = False,
) -> dict[str, Any] | None:
    payload = {
        "trigger_text": trigger_text,
        "participant_names": participant_names,
        "available_actors": available_actors,
        "decision": decision,
        "spotlight_history": spotlight_history,
        "scene_state": scene_state or {},
        "recent_dialogue_history": recent_dialogue_history,
        "beat_shift_active": beat_shift_active,
    }
    beat_shift_clause = ""
    if beat_shift_active:
        beat_shift_clause = (
            "A beat-shift signal is active: repeating the most recent spotlight can be justified when that actor is the natural executor of a concrete scene-state shift; "
            "set should_flag_repeat_spotlight false when that applies. "
        )
    prompt = (
        "Assess whether the selected actor is semantically the right choice for the current beat. "
        f"{beat_shift_clause}"
        "Consider clear direct address, whether repeating the most recent spotlight is justified, whether another available actor is more responsible for the beat, and whether the selected actor still fits the smallest relevant pressure core. "
        "Return JSON only with keys supports_selected_actor, direct_address_target, should_flag_direct_address_miss, should_flag_repeat_spotlight, reason, confidence.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    data = await _run_semantic_validation(
        model_client=model_client,
        cancellation_token=cancellation_token,
        prompt=prompt,
    )
    if data is None:
        return None

    return {
        "supports_selected_actor": bool(data.get("supports_selected_actor", True)),
        "direct_address_target": str(data.get("direct_address_target", "") or ""),
        "should_flag_direct_address_miss": bool(
            data.get("should_flag_direct_address_miss")
        ),
        "should_flag_repeat_spotlight": bool(data.get("should_flag_repeat_spotlight")),
        "reason": str(data.get("reason", "") or ""),
        "confidence": _coerce_float(data.get("confidence")),
        "parse_error": str(data.get("parse_error", "") or ""),
        "raw_response": str(data.get("raw_response", "") or ""),
    }


async def assess_narrator_render_semantics(
    *,
    model_client: Any,
    char_name: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    rendered: str,
    scene_context: str,
    cancellation_token: Any,
) -> dict[str, Any] | None:
    payload = {
        "character": char_name,
        "move": {
            "action": str(move.get("action", "") or ""),
            "dialogue": str(move.get("dialogue", "") or ""),
            "motivation": move.get("motivation", {}),
        },
        "director_decision": {
            "environment_event": str(
                director_decision.get("environment_event", "") or ""
            ),
            "tension_shift": str(director_decision.get("tension_shift", "") or ""),
        },
        "rendered": rendered,
        "scene_context": scene_context,
    }
    prompt = (
        "Assess whether the narrator render faithfully preserves the acting character move. "
        "Return JSON only with keys valid, dialogue_preserved, stayed_in_scope, should_use_fallback, issues, reason, confidence.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    data = await _run_semantic_validation(
        model_client=model_client,
        cancellation_token=cancellation_token,
        prompt=prompt,
    )
    if data is None:
        return None

    issues = data.get("issues", [])
    if not isinstance(issues, list):
        issues = []

    return {
        "valid": bool(data.get("valid", True)),
        "dialogue_preserved": bool(data.get("dialogue_preserved", True)),
        "stayed_in_scope": bool(data.get("stayed_in_scope", True)),
        "should_use_fallback": bool(data.get("should_use_fallback")),
        "issues": [str(issue) for issue in issues],
        "reason": str(data.get("reason", "") or ""),
        "confidence": _coerce_float(data.get("confidence")),
        "parse_error": str(data.get("parse_error", "") or ""),
        "raw_response": str(data.get("raw_response", "") or ""),
    }

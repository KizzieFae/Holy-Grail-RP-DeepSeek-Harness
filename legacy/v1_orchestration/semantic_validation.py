import json
import os
import re
from collections.abc import Callable
from typing import Any

from character_move_adapters import (
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)

from autogen_agentchat.agents import AssistantAgent

from turn_selection_preference import (
    resolve_participant_key,
    sanitize_semantic_turn_selection_assessment,
)
from autogen_agentchat.messages import TextMessage
from autogen_core.model_context import BufferedChatCompletionContext

MODEL_CONTEXT_BUFFER_SIZE = 1
DIRECT_ADDRESS_ISSUE_PREFIX = "Selected actor ignored direct address preference"
SEMANTIC_ADDRESSEE_MISMATCH_PREFIX = "Addressee advisory mismatch (semantic):"
REPEAT_SPOTLIGHT_ISSUE = (
    "Selected actor repeats the most recent spotlight when alternatives exist"
)
SEMANTIC_SELECTION_ISSUE = (
    "Semantic turn_selection review did not support selected actor for current beat"
)


def _is_semantic_addressee_style_issue(issue: str) -> bool:
    s = str(issue or "")
    return s.startswith(DIRECT_ADDRESS_ISSUE_PREFIX) or s.startswith(
        SEMANTIC_ADDRESSEE_MISMATCH_PREFIX
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
    *,
    selected_actor: str = "",
    participant_names: list[str] | None = None,
    display_name_for_key: Callable[[str], str] | None = None,
) -> list[str]:
    if semantic_assessment is None:
        return issues

    effective: dict[str, Any] | None = semantic_assessment
    names = list(participant_names or [])
    pick = str(selected_actor or "").strip()
    if (
        names
        and pick
        and isinstance(semantic_assessment, dict)
        and not semantic_assessment.get("parse_error")
    ):
        sanitized = sanitize_semantic_turn_selection_assessment(
            semantic_assessment,
            selected_actor=pick,
            participant_names=names,
            display_name_for_key=display_name_for_key,
        )
        if sanitized is not None:
            effective = sanitized

    reconciled = [
        issue
        for issue in issues
        if effective.get("should_flag_direct_address_miss")
        or not _is_semantic_addressee_style_issue(issue)
    ]

    if effective.get("should_flag_direct_address_miss"):
        target_key = resolve_participant_key(
            str(effective.get("direct_address_target") or ""),
            names,
            display_name_for_key=display_name_for_key,
        )
        if target_key and pick and target_key != pick:
            issue = (
                f"{SEMANTIC_ADDRESSEE_MISMATCH_PREFIX} preferred {target_key} "
                f"vs selected {pick}"
            )
            if issue not in reconciled:
                reconciled.append(issue)

    if (
        effective.get("should_flag_repeat_spotlight")
        and REPEAT_SPOTLIGHT_ISSUE not in reconciled
    ):
        reconciled.append(REPEAT_SPOTLIGHT_ISSUE)

    if (
        not effective.get("supports_selected_actor", True)
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
    routing_preference: dict[str, Any] | None = None,
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
        "routing_preference": routing_preference or {},
    }
    beat_shift_clause = ""
    if beat_shift_active:
        beat_shift_clause = (
            "A beat-shift signal is active: repeating the most recent spotlight can be justified when that actor is the natural executor of a concrete scene-state shift; "
            "set should_flag_repeat_spotlight false when that applies. "
        )
    routing_clause = (
        "The routing_preference object is deterministic orchestration context: "
        "preference_candidate (if any) is an advisory hint from responder_obligation or action_responsibility. "
        "It is not forced routing. "
        "direct_address_target must be an exact string from available_actors when a single clear addressee exists, else empty string. "
        "should_flag_direct_address_miss must be false when decision.next_actor equals direct_address_target. "
        "supports_selected_actor should be true when the selected actor is that clear addressee. "
        "Do not flag a direct-address miss when the selected actor matches the natural addressee. "
    )
    prompt = (
        "Assess whether the selected actor is semantically the right choice for the current beat. "
        f"{beat_shift_clause}"
        f"{routing_clause}"
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
    from character_move_adapters import (
        is_canonical_v2_move,
        legacy_flat_action_text,
        legacy_flat_dialogue_text,
    )

    if is_canonical_v2_move(move):
        move_payload: dict[str, Any] = {
            "move_schema_version": 2,
            "beats": move.get("beats"),
            "action_flat": legacy_flat_action_text(move),
            "dialogue_flat": legacy_flat_dialogue_text(move),
            "motivation": move.get("motivation", {}),
        }
    else:
        move_payload = {
            "action": str(move.get("action", "") or ""),
            "dialogue": str(move.get("dialogue", "") or ""),
            "motivation": move.get("motivation", {}),
        }

    payload = {
        "character": char_name,
        "move": move_payload,
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


# Human-facing Director log lines (selector_decisions / decision["reason"]): display
# names and mild suppression of low-confidence semantic-only notes. Does not change
# next_actor or other machine fields beyond optional reason text formatting.
SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD = 0.5


def apply_gated_addressee_alignment_under_progression_enforcement(
    *,
    decision: dict[str, Any],
    progression_enforcement_gate: bool,
    effective_semantic_assessment: dict[str, Any] | None,
    available_actors: list[str],
    participant_names: list[str],
    display_name_for_key: Callable[[str], str],
) -> tuple[bool, str, str]:
    """Override Director ``next_actor`` with resolved addressee when all gates pass.

    Activation (all required): progression enforcement gate active; sanitized semantic
    assessment has no ``parse_error``; ``confidence`` >=
    :data:`SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD`; ``should_flag_direct_address_miss``
    is true; resolved ``direct_address_target`` is non-empty and in ``available_actors``;
    current pick differs from that target.

    Returns ``(applied, previous_next_actor, resolved_target_or_empty)``. Mutates only
    ``decision['next_actor']`` when applied — merge the reason suffix via
    ``director_reason_projection.merge_addressee_alignment_reason`` (GitHub #210 C-A).
    """
    if not progression_enforcement_gate:
        return (False, "", "")
    if not isinstance(decision, dict) or bool(decision.get("end_round")):
        return (False, "", "")
    sem = effective_semantic_assessment
    if not isinstance(sem, dict) or sem.get("parse_error"):
        return (False, "", "")
    try:
        conf = float(sem.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if conf < SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD:
        return (False, "", "")
    if not bool(sem.get("should_flag_direct_address_miss")):
        return (False, "", "")
    prev = str(decision.get("next_actor") or "").strip()
    target_raw = str(sem.get("direct_address_target") or "").strip()
    resolved = resolve_participant_key(
        target_raw,
        participant_names,
        display_name_for_key=display_name_for_key,
    )
    if not resolved:
        return (False, prev, "")
    avail = {str(a or "").strip() for a in available_actors if str(a or "").strip()}
    if resolved not in avail:
        return (False, prev, "")
    if resolved == prev:
        return (False, prev, resolved)
    decision["next_actor"] = resolved
    return (True, prev, resolved)


def filter_selection_issues_for_human_log(
    *,
    base_issues: list[str],
    reconciled_issues: list[str],
    semantic_assessment: dict[str, Any] | None,
    confidence_threshold: float = SEMANTIC_SELECTION_LOG_CONFIDENCE_THRESHOLD,
) -> list[str]:
    """When deterministic validation is clean, omit reconciled issues if semantic confidence is low.

    If ``base_issues`` is non-empty, always return ``reconciled_issues``. If ``base_issues``
    is empty and semantic assessment is missing, keep ``reconciled_issues`` (deterministic-only
    reconcile path). If ``base_issues`` is empty and assessment exists, keep reconciled issues
    only when ``confidence >= confidence_threshold``.
    """
    if base_issues:
        return list(reconciled_issues)
    if semantic_assessment is None:
        return list(reconciled_issues)
    try:
        conf = float(semantic_assessment.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    if conf >= confidence_threshold:
        return list(reconciled_issues)
    return []


def substitute_agent_keys_with_display_names(
    text: str,
    participant_names: list[str],
    display_name_for_key: Callable[[str], str],
) -> str:
    """Replace whole-token agent keys with card display names (longest keys first).

    Identifier-like boundaries: ASCII alnum + underscore so short keys do not substitute
    inside longer identifiers.
    """
    if not text or not participant_names:
        return text
    keys = sorted(
        {str(k).strip() for k in participant_names if str(k or "").strip()},
        key=len,
        reverse=True,
    )
    out = text
    for key in keys:
        disp = str(display_name_for_key(key) or "").strip()
        if not disp or disp == key:
            continue
        pattern = re.compile(
            r"(?<![0-9A-Za-z_])" + re.escape(key) + r"(?![0-9A-Za-z_])"
        )
        out = pattern.sub(disp, out)
    return out


PROPOSAL_COHERENCE_VALIDATOR_SYSTEM_MESSAGE = """You are a semantic validator for character move proposal coherence.

The semantic_proposals array is the declared semantic commit intent (authoritative for intent).
The beats[] text is narrative prose only.

Return JSON only with keys: status, reason_code, explanation (optional short string).

status must be exactly one of:
- aligned — beats are consistent with the typed proposal(s), or no clear contradiction
- contradicted — beats clearly contradict the typed proposal(s)
- unclear — ambiguous, borderline, or insufficient evidence; do NOT treat as contradiction

reason_code when status is contradicted should be one of:
off_focal_vs_beats, reentry_vs_beats, excursion_open_vs_beats, excursion_close_vs_beats
Use proposal_set_conflict or scope_non_self only if the JSON proposals themselves conflict (rare).

Be conservative: if the contradiction is not clear, return unclear.
Do not infer proposal intent from prose alone — use the typed semantic_proposals as given.
Do not judge prose quality, continuity legality, or SceneState.
"""


def proposal_coherence_llm_enabled() -> bool:
    """Production default on; set RP_PROPOSAL_COHERENCE_LLM=0 to skip checker (CI/headless)."""
    v = os.environ.get("RP_PROPOSAL_COHERENCE_LLM", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _normalize_proposal_coherence_status(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("aligned", "contradicted", "unclear"):
        return s
    return "unclear"


async def assess_proposal_beat_contradiction(
    *,
    model_client: Any,
    acting_character: str,
    move: dict[str, Any] | None,
    cancellation_token: Any,
) -> dict[str, Any]:
    """Conservative beats↔typed-proposal check. Fail-open on parse/client errors."""
    proposals_raw = (move or {}).get("semantic_proposals")
    if not isinstance(proposals_raw, list) or not proposals_raw:
        return {"status": "aligned", "reason_code": "", "skipped": True}

    beats_action = legacy_flat_action_text(move)
    beats_dialogue = legacy_flat_dialogue_text(move)

    if not proposal_coherence_llm_enabled():
        return {
            "status": "unclear",
            "reason_code": "checker_disabled",
            "skipped": True,
            "explanation": "RP_PROPOSAL_COHERENCE_LLM disabled",
        }

    payload = {
        "acting_character": acting_character,
        "semantic_proposals": proposals_raw,
        "beats_action_text": beats_action,
        "beats_dialogue_text": beats_dialogue,
        "beats_combined_text": f"{beats_action} {beats_dialogue}".strip(),
    }
    prompt = (
        f"{PROPOSAL_COHERENCE_VALIDATOR_SYSTEM_MESSAGE}\n\n"
        "Assess whether the beat prose clearly contradicts the typed semantic_proposals.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    data = await _run_semantic_validation(
        model_client=model_client,
        cancellation_token=cancellation_token,
        prompt=prompt,
    )
    if data is None:
        return {
            "status": "unclear",
            "reason_code": "checker_parse_error",
            "parse_error": "model_client unavailable",
        }

    if data.get("parse_error"):
        return {
            "status": "unclear",
            "reason_code": "checker_parse_error",
            "parse_error": str(data.get("parse_error", "") or ""),
            "raw_response": str(data.get("raw_response", "") or ""),
        }

    status = _normalize_proposal_coherence_status(data.get("status"))
    reason_code = str(data.get("reason_code", "") or "").strip()
    return {
        "status": status,
        "reason_code": reason_code,
        "explanation": str(data.get("explanation", "") or ""),
        "raw_response": str(data.get("raw_response", "") or ""),
    }


def record_proposal_coherence_stats(
    st_module: Any,
    assessment: dict[str, Any] | None,
) -> None:
    """Session counters for checker invocations and status distribution (#231)."""
    if st_module is None:
        return
    ss = getattr(st_module, "session_state", None)
    if not isinstance(ss, dict):
        return
    stats = ss.setdefault(
        "proposal_coherence_stats",
        {
            "invocations": 0,
            "aligned": 0,
            "contradicted": 0,
            "unclear": 0,
            "skipped": 0,
            "checker_disabled": 0,
        },
    )
    if not isinstance(stats, dict):
        return
    if assessment is None:
        return
    if assessment.get("skipped"):
        stats["skipped"] = int(stats.get("skipped", 0) or 0) + 1
        if assessment.get("reason_code") == "checker_disabled":
            stats["checker_disabled"] = int(stats.get("checker_disabled", 0) or 0) + 1
        return
    stats["invocations"] = int(stats.get("invocations", 0) or 0) + 1
    st = str(assessment.get("status", "") or "unclear")
    if st in stats:
        stats[st] = int(stats.get(st, 0) or 0) + 1
    else:
        stats["unclear"] = int(stats.get("unclear", 0) or 0) + 1

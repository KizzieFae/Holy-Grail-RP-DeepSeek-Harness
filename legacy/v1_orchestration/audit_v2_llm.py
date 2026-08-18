"""Audit V2 optional LLM advisory passes (log-only, closed artifacts)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core.model_context import BufferedChatCompletionContext

AUDIT_V2_LLM_SYSTEM = """You are an audit advisor for a roleplay pipeline. Return JSON only.
You must NOT infer scene state, continuity, issues, or director intent beyond the text given.
Use only the provided artifacts. Do not add facts from outside them.
For narrator/prose tasks, apply the allowed-expansion policy text exactly.
Respond with a single JSON object:
{
  "findings": [{"code": "<snake_case>", "severity": "info|low|medium", "summary": "<short>", "materiality": "material|non_material|n/a"}],
  "confidence": <0.0-1.0>,
  "confidence_bucket": "low|medium|high",
  "uncertainty": "<short enum or phrase>",
  "verdict_vs_deterministic": "supports|contradicts|inconclusive|null"
}
If nothing to report, findings may be empty. Be conservative."""


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


def build_llm_skipped_payload(
    *,
    llm_audit_enabled: bool,
    escalation_qualified: bool,
    escalation_reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    would_escalate = bool(escalation_qualified)
    reasons = list(escalation_reasons or [])
    if not llm_audit_enabled:
        return {
            "status": "skipped",
            "skip_reason": "llm_disabled",
            "would_escalate": would_escalate,
            "escalation_reasons_if_enabled": reasons,
        }
    return {
        "status": "skipped",
        "skip_reason": "no_escalation_required",
        "would_escalate": False,
        "escalation_reasons_if_enabled": [],
    }


async def run_audit_v2_llm(
    *,
    layer: str,
    model_client: Any,
    cancellation_token: Any,
    user_prompt: str,
    model_id: str = "",
) -> dict[str, Any]:
    """Execute synchronous LLM audit call; returns completed or error status."""
    if model_client is None:
        return {
            "status": "error",
            "skip_reason": "model_client_unavailable",
            "error": "no_model_client",
            "would_escalate": True,
            "escalation_reasons_if_enabled": [],
        }

    agent = AssistantAgent(
        name="AuditV2Advisor",
        description="Non-authoritative audit V2 LLM advisor.",
        system_message=AUDIT_V2_LLM_SYSTEM,
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=1),
    )
    raw_response = ""
    try:
        result = await agent.on_messages(
            [TextMessage(content=user_prompt, source="system")],
            cancellation_token,
        )
        raw_response = str(result.chat_message.content or "")
        json_text = _extract_json_object_text(raw_response)
        data = json.loads(json_text)
    except Exception as exc:  # noqa: BLE001 — audit path; capture all
        return {
            "status": "error",
            "skip_reason": "llm_parse_or_call_failed",
            "error": str(exc),
            "raw_response_excerpt": raw_response[:2000],
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "skip_reason": "invalid_llm_shape",
            "error": "response_not_object",
        }

    data["status"] = "completed"
    data["model_meta"] = {
        "model_id": model_id or getattr(model_client, "model_id", "") or "",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return data


def build_character_llm_prompt(*, move_json: str, escalation_reasons: list[dict[str, Any]]) -> str:
    return (
        "LAYER: character_decision\n"
        "TASK: Detect textual/logical contradictions WITHIN the structured move JSON only. "
        "Do not judge scene fit, issues, or director compliance.\n"
        f"STRUCTURED_MOVE_JSON:\n{move_json}\n"
        f"DETERMINISTIC_ESCALATION_REASONS:\n{json.dumps(escalation_reasons, ensure_ascii=False)}\n"
    )


def build_narrator_llm_prompt(
    *,
    move_json: str,
    rendered_final: str,
    environment_event: str,
    allowed_expansion_policy: str,
    escalation_reasons: list[dict[str, Any]],
) -> str:
    return (
        "LAYER: narrator_output\n"
        "TASK: Assess whether rendered prose introduces MATERIAL new facts not grounded in "
        "the move or allowed expansion (policy below). Assess semantic equivalence of DECLARED "
        "ACTION only vs render (not stylistic quality). Use materiality: material if it would "
        "change continuity, add entities/relationships, or become referenceable truth.\n"
        f"ALLOWED_EXPANSION_POLICY:\n{allowed_expansion_policy}\n"
        f"ENVIRONMENT_EVENT_TEXT (narrator-render input only):\n{environment_event}\n"
        f"STRUCTURED_MOVE_JSON:\n{move_json}\n"
        f"RENDERED_FINAL:\n{rendered_final[:8000]}\n"
        f"DETERMINISTIC_ESCALATION_REASONS:\n{json.dumps(escalation_reasons, ensure_ascii=False)}\n"
    )


def build_prose_llm_prompt(
    *,
    move_dialogue: str,
    move_action_excerpt: str,
    rendered_final: str,
    prior_assistant_excerpt: str | None,
    acting_label: str,
    escalation_reasons: list[dict[str, Any]],
) -> str:
    prior = prior_assistant_excerpt or ""
    return (
        "LAYER: prose_dialogue\n"
        "TASK: Surface prose only — redundancy vs prior line, pronoun attribution ambiguity. "
        "No narrative truth, continuity, or director intent.\n"
        f"ACTING_LABEL: {acting_label}\n"
        f"MOVE_ACTION_EXCERPT: {move_action_excerpt[:2000]}\n"
        f"MOVE_DIALOGUE: {move_dialogue[:2000]}\n"
        f"RENDERED_FINAL:\n{rendered_final[:8000]}\n"
        f"PRIOR_ASSISTANT_EXCERPT:\n{prior[:4000]}\n"
        f"DETERMINISTIC_ESCALATION_REASONS:\n{json.dumps(escalation_reasons, ensure_ascii=False)}\n"
    )

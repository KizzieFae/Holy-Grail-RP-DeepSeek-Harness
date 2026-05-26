"""Issue #250 — schema-recoverable parse repair prompts (repair lane only)."""

from __future__ import annotations

import json

_MAX_PRIOR_EMISSION_CHARS = 12_000


def format_schema_repair_retry_note(
    *,
    prior_raw_emission: str,
    ingress_error: str,
) -> str:
    raw = str(prior_raw_emission or "").strip()
    if len(raw) > _MAX_PRIOR_EMISSION_CHARS:
        raw = raw[: _MAX_PRIOR_EMISSION_CHARS - 3] + "..."
    err = str(ingress_error or "").strip()
    lines = [
        "IMPORTANT: Your previous character move JSON was rejected for schema/container "
        "errors only. REPAIR that emission — do not invent new RP behavior.",
        "Preserve verbatim: beats[] (all action/speech text), motivation, scene_state_updates "
        "when present, semantic_evaluation.decision, and proposal kind(s) unless the error "
        "requires omission.",
        "Change only invalid or forbidden fields (extra proposal helper keys, missing "
        "character, mutual exclusivity between semantic_evaluation and root semantic_proposals).",
        "Output a single JSON object: move_schema_version 2 — no markdown fences or prose.",
    ]
    if err:
        lines.append(f"Ingress/schema error: {err}")
    if raw:
        lines.append("YOUR PREVIOUS EMISSION (REPAIR ONLY):")
        lines.append(raw)
    return "\n".join(lines)

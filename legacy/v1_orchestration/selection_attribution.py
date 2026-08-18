"""Selection attribution for architecture-quality assessment.

Records one event per ``choose_next_actor`` outcome via the same simulation buffer as
progression metrics: ``maybe_record_sim_progression_metric`` with ``kind: selection_attribution``.

Payloads may include ``director_model_reason`` (GitHub #207): verbatim model rationale
when present on the runtime ``decision``; see ``ARCHITECTURE.md``.
"""

from __future__ import annotations

import json
from typing import Any


def record_selection_attribution_event(st_module: Any, record: dict[str, Any]) -> None:
    from progression_run_metrics import maybe_record_sim_progression_metric

    payload = {"kind": "selection_attribution", **dict(record)}
    maybe_record_sim_progression_metric(st_module, payload)


def format_operator_selector_decision_line(
    *,
    attribution_chain: list[str],
    lead: str,
    reason: str = "",
) -> str:
    """Build a session-visible selector log line with explicit attribution chain.

    ``lead`` is the full human-readable clause after the chain prefix
    (e.g. ``Director selected Alice`` or ``Director override to …: Bob``).
    ``reason`` is appended after a colon when non-empty (Director rationale path).

    Phase A (#206): surface ``attribution_chain`` without changing ``decision`` fields.
    """

    chain = " > ".join(str(x).strip() for x in attribution_chain if str(x).strip())
    if not chain:
        chain = "unknown"
    base = f"[attribution: {chain}] {str(lead or '').strip()}"
    reason_t = str(reason or "").strip()
    if reason_t:
        return f"{base}: {reason_t}"
    return base


def semantic_flag_summary(assessment: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(assessment, dict):
        return {"semantic_validation_ran": False}
    if assessment.get("parse_error"):
        return {
            "semantic_validation_ran": True,
            "parse_error": True,
            "parse_error_detail": str(assessment.get("parse_error") or ""),
        }
    return {
        "semantic_validation_ran": True,
        "supports_selected_actor": assessment.get("supports_selected_actor"),
        "should_flag_direct_address_miss": assessment.get(
            "should_flag_direct_address_miss"
        ),
        "should_flag_repeat_spotlight": assessment.get("should_flag_repeat_spotlight"),
        "direct_address_target": str(assessment.get("direct_address_target") or ""),
        "confidence": assessment.get("confidence"),
    }


def summarize_selection_attribution_logs(
    logs: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    if not logs:
        return {
            "selection_events": 0,
            "hard_route_events": 0,
            "progression_override_applied_count": 0,
            "fairness_rotation_count": 0,
            "attribution_chain_counts": {},
        }
    hard = sum(1 for x in logs if x.get("hard_route"))
    ov = sum(
        1
        for x in logs
        if (x.get("after_progression_override") or {}).get("applied") is True
    )
    fair = sum(
        1 for x in logs if (x.get("after_fairness") or {}).get("rotated") is True
    )
    chain_counts: dict[str, int] = {}
    for x in logs:
        chain = x.get("attribution_chain")
        key = (
            json.dumps(chain, ensure_ascii=False)
            if isinstance(chain, list)
            else "[]"
        )
        chain_counts[key] = chain_counts.get(key, 0) + 1
    return {
        "selection_events": len(logs),
        "hard_route_events": hard,
        "progression_override_applied_count": ov,
        "fairness_rotation_count": fair,
        "attribution_chain_counts": chain_counts,
    }


def summarize_selection_attribution_from_sim_events(
    events: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Filter ``sim_progression_metrics`` rows to attribution events."""
    if not events:
        return summarize_selection_attribution_logs([])
    rows = [
        {k: v for k, v in e.items() if k != "kind"}
        for e in events
        if e.get("kind") == "selection_attribution"
    ]
    return summarize_selection_attribution_logs(rows)

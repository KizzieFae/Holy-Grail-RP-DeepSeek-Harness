"""Optional capture of progression outcomes for headless scenario runs (simulation only).

When ``session_state["sim_progression_metrics"]`` is a list, ``turn_runner_turn`` appends
events. Streamlit sessions omit this key; no overhead in production.
"""

from __future__ import annotations

from typing import Any

# Short labels for manual triage (maps to checklist: gate ≈ gate/threshold, retry ≈ retry behavior).
FAILURE_CLASSIFICATIONS = frozenset(
    {
        "contract",
        "gate",
        "selection",
        "retry",
        "continuity",
        "other",
    }
)


def maybe_record_sim_progression_metric(st_module: Any, payload: dict[str, Any]) -> None:
    buf = st_module.session_state.get("sim_progression_metrics")
    if isinstance(buf, list):
        buf.append(dict(payload))


def summarize_sim_progression_metrics(
    events: list[dict[str, Any]] | None,
    *,
    progression_enforcement_enabled: bool,
    arch_quality_variant: str | None = None,
) -> dict[str, Any]:
    """Aggregate captured events into a compact metrics dict."""
    from selection_attribution import summarize_selection_attribution_from_sim_events

    events = events or []
    retries = sum(1 for e in events if e.get("kind") == "progression_retry")
    failures = sum(1 for e in events if e.get("kind") == "progression_failure")
    accepted = [e for e in events if e.get("kind") == "accepted_turn"]
    qualifying = sum(1 for e in accepted if e.get("qualifies"))
    non_qualifying = sum(1 for e in accepted if not e.get("qualifies"))

    first_qual: int | None = None
    for e in accepted:
        if not e.get("qualifies"):
            continue
        ti = e.get("continuity_turn_index")
        if isinstance(ti, int):
            first_qual = ti if first_qual is None else min(first_qual, ti)

    out: dict[str, Any] = {
        "first_qualifying_progression_delta_turn_index": first_qual,
        "progression_retries_triggered": retries,
        "failed_progression_attempts": failures,
        "qualifying_turns": qualifying,
        "non_qualifying_turns": non_qualifying,
        "accepted_character_turns": len(accepted),
        "progression_enforcement_enabled": progression_enforcement_enabled,
        "selection_attribution_summary": summarize_selection_attribution_from_sim_events(
            events,
        ),
    }
    if arch_quality_variant:
        out["arch_quality_variant"] = arch_quality_variant
    return out


def build_structured_eval_payload(
    *,
    scenario_id: str | None,
    verdict: str | None,
    failure_classification: str | None,
    metrics: dict[str, Any],
    audit_session_number: int | None = None,
    audit_summary_report_path: str | None = None,
    expected_pressure_profile: str | None = None,
    retrieval_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single JSON-serializable object for run comparison (manual verdict/classification)."""
    out: dict[str, Any] = {
        "scenario_id": scenario_id,
        "verdict": verdict,
        "failure_classification": failure_classification,
        "metrics": metrics,
        "audit_session_number": audit_session_number,
        "audit_summary_report_path": audit_summary_report_path,
        "expected_pressure_profile": expected_pressure_profile,
    }
    if retrieval_session is not None:
        out["retrieval_session"] = dict(retrieval_session)
    return out

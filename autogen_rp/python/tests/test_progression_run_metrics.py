"""progression_run_metrics summarization (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from progression_run_metrics import (  # noqa: E402
    build_structured_eval_payload,
    summarize_sim_progression_metrics,
)
from selection_attribution import format_operator_selector_decision_line  # noqa: E402


def test_summarize_empty() -> None:
    s = summarize_sim_progression_metrics([], progression_enforcement_enabled=True)
    assert s["first_qualifying_progression_delta_turn_index"] is None
    assert s["progression_retries_triggered"] == 0
    assert s["failed_progression_attempts"] == 0
    assert s["qualifying_turns"] == 0
    assert s["non_qualifying_turns"] == 0
    assert s["progression_enforcement_enabled"] is True
    assert s["selection_attribution_summary"]["selection_events"] == 0


def test_summarize_includes_arch_quality_variant_when_requested() -> None:
    s = summarize_sim_progression_metrics(
        [],
        progression_enforcement_enabled=True,
        arch_quality_variant="a1",
    )
    assert s["arch_quality_variant"] == "a1"


def test_summarize_selection_attribution_mixed_with_progression() -> None:
    events = [
        {"kind": "accepted_turn", "continuity_turn_index": 1, "qualifies": True},
        {
            "kind": "selection_attribution",
            "final_next_actor": "Ayame",
            "attribution_chain": ["director", "participation_fairness"],
            "hard_route": False,
        },
    ]
    s = summarize_sim_progression_metrics(events, progression_enforcement_enabled=True)
    assert s["selection_attribution_summary"]["selection_events"] == 1
    assert s["qualifying_turns"] == 1


def test_summarize_mixed_events() -> None:
    events = [
        {"kind": "accepted_turn", "continuity_turn_index": 1, "qualifies": False},
        {"kind": "progression_retry", "continuity_turn_index": 1},
        {"kind": "accepted_turn", "continuity_turn_index": 1, "qualifies": True},
        {"kind": "accepted_turn", "continuity_turn_index": 2, "qualifies": True},
        {"kind": "progression_failure", "continuity_turn_index": 3},
    ]
    s = summarize_sim_progression_metrics(events, progression_enforcement_enabled=True)
    assert s["first_qualifying_progression_delta_turn_index"] == 1
    assert s["progression_retries_triggered"] == 1
    assert s["failed_progression_attempts"] == 1
    assert s["qualifying_turns"] == 2
    assert s["non_qualifying_turns"] == 1
    assert s["accepted_character_turns"] == 3


def test_build_structured_eval_payload() -> None:
    m = summarize_sim_progression_metrics([], progression_enforcement_enabled=False)
    p = build_structured_eval_payload(
        scenario_id="emotional_loop_2char",
        verdict="WARN",
        failure_classification="retry",
        metrics=m,
        audit_session_number=5,
        audit_summary_report_path=None,
        sim_progression_metrics_events=[{"kind": "accepted_turn", "qualifies": True}],
    )
    assert p["scenario_id"] == "emotional_loop_2char"
    assert p["verdict"] == "WARN"
    assert p["failure_classification"] == "retry"
    assert p["metrics"]["progression_enforcement_enabled"] is False
    assert p["expected_pressure_profile"] is None
    assert "retrieval_session" not in p
    assert p["sim_progression_metrics_events"][0]["kind"] == "accepted_turn"

    p2 = build_structured_eval_payload(
        scenario_id="s",
        verdict=None,
        failure_classification=None,
        metrics=m,
        expected_pressure_profile="high",
    )
    assert p2["expected_pressure_profile"] == "high"


def test_build_structured_eval_payload_retrieval_session() -> None:
    m = summarize_sim_progression_metrics([], progression_enforcement_enabled=True)
    rs = {"retrieval_mode": "on", "retrieval_verified_active": True}
    p = build_structured_eval_payload(
        scenario_id="x",
        verdict=None,
        failure_classification=None,
        metrics=m,
        retrieval_session=rs,
    )
    assert p["retrieval_session"] == rs


def test_format_operator_selector_decision_line_reason_suffix() -> None:
    line = format_operator_selector_decision_line(
        attribution_chain=["director", "participation_fairness"],
        lead="Director selected Ayame",
        reason="pick Ayame",
    )
    assert line.startswith("[attribution: director > participation_fairness]")
    assert "Director selected Ayame" in line
    assert line.endswith(": pick Ayame")


def test_format_operator_selector_decision_line_empty_chain_uses_unknown() -> None:
    line = format_operator_selector_decision_line(
        attribution_chain=[],
        lead="Director selected Bob",
        reason="r",
    )
    assert "[attribution: unknown]" in line

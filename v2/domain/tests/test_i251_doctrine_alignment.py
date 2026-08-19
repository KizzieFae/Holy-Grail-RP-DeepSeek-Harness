"""Tests for Issue #251 L3 doctrine-alignment overlay."""

from __future__ import annotations

import sys
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "issue251"
if str(_FIXTURES) not in sys.path:
    sys.path.insert(0, str(_FIXTURES))

from i251_doctrine_alignment import (  # noqa: E402
    evaluate_doctrine_alignment,
    summarize_doctrine_alignment,
)


def test_l3_exit_aligned() -> None:
    out = evaluate_doctrine_alignment(
        doctrine_arm="B",
        doctrine_schema_version="physical_severance_v1",
        doctrine_expected="off_focal",
        attempt={
            "parse_ok": True,
            "decision": "covered_change",
            "proposal_kinds": ["off_focal"],
        },
        expected_label="covered_change + off_focal",
    )
    assert out["doctrine_aligned"] is True
    assert out["doctrine_arm"] == "B"


def test_l3_non_exit_false_positive() -> None:
    out = evaluate_doctrine_alignment(
        doctrine_arm="B",
        doctrine_schema_version="physical_severance_v1",
        doctrine_expected="no_covered_change",
        attempt={
            "parse_ok": True,
            "decision": "covered_change",
            "proposal_kinds": ["off_focal"],
        },
    )
    assert out["doctrine_aligned"] is False
    assert "False positive" in out["rationale"]


def test_l3_guarded_rubric() -> None:
    out = evaluate_doctrine_alignment(
        doctrine_arm="physical_severance_guarded",
        doctrine_schema_version="physical_severance_guarded_v1",
        doctrine_expected="no_covered_change",
        attempt={
            "parse_ok": True,
            "decision": "no_covered_change",
            "proposal_kinds": [],
        },
    )
    assert out["doctrine_aligned"] is True
    assert "do not complete exits the beat does not complete" in out["rubric_summary"]


def test_summarize_by_arm() -> None:
    rows = [
        {
            "doctrine_arm": "A",
            "case_id": "EXIT-C-GM3",
            "cohort": "exit",
            "preflight": {"contamination_clean": True},
            "first_attempt": {
                "S1_semantic_intent_correct": False,
                "S2_structural_legality_pass": True,
                "decision": "no_covered_change",
                "proposal_kinds": [],
            },
            "doctrine_alignment": {"doctrine_aligned": False},
        },
        {
            "doctrine_arm": "B",
            "case_id": "EXIT-C-GM3",
            "cohort": "exit",
            "preflight": {"contamination_clean": True},
            "first_attempt": {
                "S1_semantic_intent_correct": True,
                "S2_structural_legality_pass": True,
                "decision": "covered_change",
                "proposal_kinds": ["off_focal"],
            },
            "doctrine_alignment": {"doctrine_aligned": True},
        },
    ]
    summary = summarize_doctrine_alignment(rows)
    assert "A" in summary["by_arm"]
    assert "B" in summary["by_arm"]
    assert summary["A_vs_B_delta"].get("GM3_L3_alignment_rate_delta_B_minus_A") == 1.0

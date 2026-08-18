"""Tests for Issue #251 replay semantic adjudication adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PY = Path(__file__).resolve().parents[1]
_REPO = Path(__file__).resolve().parents[3]
_AUDIT_ROOT = _REPO / "legacy" / "v1_orchestration" / "data" / "rp_audits"
sys.path.insert(0, str(_PY / "validation_runs" / "issue251"))

from i251_replay_adjudication import (  # noqa: E402
    adjudicate_replay_row,
    classify_failure_lane,
    fiction_expects_scene_departure,
    merge_adjudication_into_matrix,
)


def test_classify_lane_structural() -> None:
    assert (
        classify_failure_lane(
            {
                "parse_ok": True,
                "route_to_249": True,
                "S1_semantic_intent_correct": True,
                "S2_structural_legality_pass": False,
            }
        )
        == "issue249_structural"
    )


def test_adjudicate_exit_row_908p01() -> None:
    audit = _AUDIT_ROOT / "session_908/round_001"
    hits = sorted(audit.glob("*turn03_willow_reeves_full.json"))
    hits = [p for p in hits if "parse_retry" not in p.name]
    if not hits:
        pytest.skip("908-P01 audit missing")
    row = {
        "case_id": "EXIT-A-908P01",
        "cohort": "exit",
        "doctrine_expected": "off_focal",
        "expected_result_label": "covered_change + off_focal",
        "source_artifact": str(hits[0]),
        "first_attempt": {
            "parse_ok": True,
            "ingress_pass": True,
            "decision": "covered_change",
            "proposal_kinds": ["off_focal"],
            "S1_semantic_intent_correct": True,
            "S2_structural_legality_pass": True,
        },
    }
    adj = adjudicate_replay_row(row)
    assert adj["adjudicated"]["adjudicated_semantically_correct"] is True
    assert fiction_expects_scene_departure(adj["boundary_signals"]) is True


def test_merge_matrix_minimal() -> None:
    payload = {
        "all_samples": [
            {
                "case_id": "NE-P02",
                "cohort": "non_exit",
                "doctrine_expected": "no_covered_change",
                "source_artifact": str(
                    _AUDIT_ROOT
                    / "session_908/round_001"
                    / sorted(
                        (_AUDIT_ROOT / "session_908/round_001").glob(
                            "*turn05_willow_reeves_full.json"
                        )
                    )[0]
                ),
                "first_attempt": {
                    "parse_ok": True,
                    "ingress_pass": True,
                    "decision": "no_covered_change",
                    "proposal_kinds": [],
                    "S1_semantic_intent_correct": True,
                    "S2_structural_legality_pass": False,
                },
            }
        ]
    }
    merged = merge_adjudication_into_matrix(payload)
    assert "adjudication_summary" in merged
    assert merged["all_samples"][0]["adjudication"]["failure_lane"] in {
        "issue249_structural",
        "none",
    }

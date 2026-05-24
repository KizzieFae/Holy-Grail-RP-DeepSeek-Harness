"""Tests for Issue #246 participation adjudication."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_RP = Path(__file__).resolve().parents[1] / "rp_app"
if str(_RP) not in sys.path:
    sys.path.insert(0, str(_RP))

from participation_adjudication_llm import build_llm_prompt, parse_llm_response  # noqa: E402
from participation_adjudication_v1 import (  # noqa: E402
    CALIBRATION_ANCHORS,
    AdjudicationInputBundle,
    adjudicate_suspicions,
    build_adjudication_bundle,
    summarize_adjudication_report,
)
from participation_suspicion_extract import row_dict_to_suspicion  # noqa: E402


def _suspicion(**overrides):
    row = {
        "audit_session_number": 899,
        "turn_number": 7,
        "actor": "Willow_Reeves",
        "probe_id": "P03",
        "transition_type": "remote_garage_phone",
        "expected_rubric": "covered_change",
        "rubric_class": "C3_missed_covered_change",
        "semantic_decision": "no_covered_change",
        "proposal_count": 0,
        "F_no_proposal": True,
        "F_remote_cue": True,
        "F_suspect_miss": True,
        "present_characters": ["Willow_Reeves"],
        "offstage_characters": [],
        "character_presence_status": {"Willow_Reeves": "onstage"},
        "effective_user_trigger": "go to garage",
        "source_artifact": "/tmp/x.json",
    }
    row.update(overrides)
    rec = row_dict_to_suspicion(row)
    assert rec is not None
    return rec


def test_calibration_anchor_case_11_is_failure():
    s = _suspicion()
    adjs = adjudicate_suspicions([s], mode="mock")
    assert len(adjs) == 1
    assert adjs[0].adjudication_outcome == "adjudicated_failure"
    assert adjs[0].human_calibration_anchor is True


def test_tether_topology_non_failure():
    s = _suspicion(
        audit_session_number=905,
        turn_number=13,
        actor="Selina_Kyle",
        probe_id="P06",
        F_remote_cue=False,
        F_suspect_miss=False,
        F_tether_cue=True,
        F_in_room_focus=True,
        F_fiction_roster_drift=False,
    )
    adjs = adjudicate_suspicions([s], mode="mock", corpus_lookup={})
    assert adjs[0].adjudication_outcome == "adjudicated_non_failure"


def test_reporting_summary_fields():
    suspicions = [
        _suspicion(),
        _suspicion(audit_session_number=905, turn_number=13, actor="Selina_Kyle", probe_id="P06"),
    ]
    adjs = adjudicate_suspicions(suspicions, mode="mock", corpus_lookup={})
    summary = summarize_adjudication_report(suspicions, adjs)
    for key in (
        "raw_deterministic_suspicion_count",
        "adjudicated_failure_count",
        "adjudicated_non_failure_count",
        "deterministic_policy_reviewed_count",
    ):
        assert key in summary
    assert summary["raw_deterministic_suspicion_count"] == 2
    assert summary["adjudicated_failure_count"] == 1


def test_llm_parse_low_confidence_escalates():
    raw = json.dumps(
        {
            "adjudication_outcome": "adjudicated_failure",
            "adjudication_confidence": "low",
            "adjudication_rationale": "unsure",
        }
    )
    rec = parse_llm_response(raw, suspicion_id="x")
    assert rec.adjudication_outcome == "needs_human_review"


def test_bundle_truncation():
    s = _suspicion()
    bundle = build_adjudication_bundle(
        s,
        row={"beats_action_text": "x" * 2000, "participation_arc_lines": ["a", "b"]},
    )
    assert len(bundle.beats_excerpt) <= 1200
    assert bundle.suspicion_id == s.suspicion_id


def test_known_anchor_keys_present():
    assert "899:7:Willow_Reeves:P03" in CALIBRATION_ANCHORS
    assert "902:7:Hannah_Lovelace:P03" in CALIBRATION_ANCHORS

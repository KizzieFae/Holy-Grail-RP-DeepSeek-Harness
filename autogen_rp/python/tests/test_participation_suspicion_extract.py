"""Tests for Issue #246 participation suspicion extraction."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_RP = Path(__file__).resolve().parents[1] / "rp_app"
if str(_RP) not in sys.path:
    sys.path.insert(0, str(_RP))

from participation_suspicion_extract import (  # noqa: E402
    POSITIVE_SUSPICION_RUBRIC_CLASSES,
    make_suspicion_id,
    row_dict_to_suspicion,
    suspicions_from_row_dicts,
)


def _c3_row(**overrides):
    base = {
        "audit_session_number": 902,
        "turn_number": 7,
        "actor": "Hannah_Lovelace",
        "probe_id": "P03",
        "transition_type": "remote_relocation",
        "expected_rubric": "covered_change",
        "rubric_class": "C3_missed_covered_change",
        "semantic_decision": "no_covered_change",
        "proposal_count": 0,
        "F_no_proposal": True,
        "F_suspect_miss": False,
        "F_in_room_focus": True,
        "present_characters": ["Ayame", "Hannah_Lovelace"],
        "offstage_characters": [],
        "character_presence_status": {"Hannah_Lovelace": "onstage"},
        "target_presence_constraint": "must_remain",
        "source_artifact": "/tmp/test.json",
    }
    base.update(overrides)
    return base


def test_c3_row_emits_suspicion():
    rec = row_dict_to_suspicion(_c3_row())
    assert rec is not None
    assert rec.deterministic_rubric_class == "C3_missed_covered_change"
    assert rec.adjudication_status == "pending"
    assert rec.suspicion_id == make_suspicion_id(
        audit_session_number=902, turn_number=7, actor="Hannah_Lovelace", probe_id="P03"
    )


def test_non_c3_row_skipped():
    assert row_dict_to_suspicion(_c3_row(rubric_class="C1_correct_no_covered_change")) is None


def test_suspicion_batch_count():
    rows = [
        _c3_row(),
        _c3_row(probe_id="P04", turn_number=9),
        _c3_row(rubric_class="C7_ambiguous"),
    ]
    suspicions = suspicions_from_row_dicts(rows)
    assert len(suspicions) == 2


def test_positive_suspicion_classes_c3_only():
    assert POSITIVE_SUSPICION_RUBRIC_CLASSES == frozenset({"C3_missed_covered_change"})

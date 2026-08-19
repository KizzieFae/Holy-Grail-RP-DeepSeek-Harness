"""Issue #79 Slice 3 — continuity audit origin (pipeline vs bypass)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


from continuity_audit_origin import (
    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API,
    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION,
    CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_RAW_LOCATION,
    CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN,
    build_continuity_audit_origin_row_metadata,
    flush_continuity_audit_origin_export_payload,
)
from continuity_manager import ContinuityManager
from continuity_reintegration import apply_excursion_close_reintegration_mutation
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from continuity_state import ExcursionStatus


def _fresh_manager() -> ContinuityManager:
    m = ContinuityManager()
    m.initialize_scene(
        location="Dorm",
        opening_description="x",
        present_characters=["A", "B"],
    )
    complete_setup_seam_for_test_manager(m, cast=["A", "B"])
    return m


def test_pipeline_turn_no_bypass_flush() -> None:
    m = _fresh_manager()
    m.process_turn(
        acting_character="A",
        move={
            "action": "speak",
            "dialogue": "hi",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )
    kinds = [e["kind"] for e in m.continuity_audit_origin_log]
    assert CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN in kinds
    assert CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API not in kinds

    out = flush_continuity_audit_origin_export_payload(m)
    assert out["has_bypass"] is False
    assert out["bypass_beats"] == []
    assert m.continuity_audit_origin_log == []


def test_direct_open_excursion_is_bypass_not_pipeline() -> None:
    m = _fresh_manager()
    m.open_excursion(participant_character_ids=["B"], excursion_id="ex1")
    assert any(
        e["kind"] == CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API
        for e in m.continuity_audit_origin_log
    )
    out = flush_continuity_audit_origin_export_payload(m)
    assert out["has_bypass"] is True
    assert len(out["bypass_beats"]) == 1
    assert out["bypass_beats"][0]["kind"] == (
        CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API
    )


def test_process_turn_excursion_open_does_not_emit_direct_bypass() -> None:
    m = _fresh_manager()
    m.process_turn(
        acting_character="A",
        move={
            "action": "x",
            "dialogue": "",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex1",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )
    assert not any(
        e["kind"] == CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API
        for e in m.continuity_audit_origin_log
    )
    assert any(
        e["kind"] == CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN
        for e in m.continuity_audit_origin_log
    )


def test_raw_location_bypass() -> None:
    m = _fresh_manager()
    m.notify_raw_location_bypass_for_audit(continuity_turn_index=0)
    assert any(
        e["kind"] == CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_RAW_LOCATION
        for e in m.continuity_audit_origin_log
    )


def test_oor_reintegration_apply_records_once_not_double_with_close() -> None:
    m = _fresh_manager()
    m.process_turn(
        acting_character="A",
        move={
            "action": "x",
            "dialogue": "",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex_oor",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )
    m.continuity_audit_origin_log.clear()
    ts = datetime.now(timezone.utc)
    apply_excursion_close_reintegration_mutation(
        m,
        "ex_oor",
        {"reintegration": None},
        commit_turn_index=2,
        timestamp=ts,
    )
    kinds = [e["kind"] for e in m.continuity_audit_origin_log]
    assert kinds.count(CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION) == 1
    assert CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_DIRECT_EXCURSION_API not in kinds


def test_row_metadata_pipeline_only_when_pending_matches() -> None:
    m = _fresh_manager()
    assert build_continuity_audit_origin_row_metadata(m) is None
    m.process_turn(
        acting_character="A",
        move={
            "action": "speak",
            "dialogue": "hi",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )
    meta = build_continuity_audit_origin_row_metadata(m)
    assert meta == {
        "kind": CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN,
        "continuity_turn_index": 1,
    }


def test_pipeline_apply_reintegration_no_oor_bypass() -> None:
    m = _fresh_manager()
    m.process_turn(
        acting_character="A",
        move={
            "action": "x",
            "dialogue": "",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
            "excursion_lifecycle": {
                "operation": "open",
                "excursion_id": "ex1",
                "participant_character_ids": ["B"],
            },
        },
        director_decision={"next_actor": "B"},
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )
    m.process_turn(
        acting_character="B",
        move={
            "action": "x",
            "dialogue": "",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
            "excursion_lifecycle": {
                "operation": "close",
                "excursion_id": "ex1",
            },
        },
        director_decision={"next_actor": "A"},
        other_characters=["A"],
        timestamp=datetime.now(timezone.utc),
    )
    assert not any(
        e["kind"] == CONTINUITY_AUDIT_ORIGIN_KIND_BYPASS_OOR_REINTEGRATION
        for e in m.continuity_audit_origin_log
    )
    rec = m.excursions["ex1"]
    assert rec.status == ExcursionStatus.CLOSED

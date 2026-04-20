"""Issue #79 Slice 2 — runtime mirrors and excursion digest."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_runtime_mirrors import (
    build_excursion_audit_digest_v1,
    scene_state_after_runtime_mirror,
)
from continuity_manager import ContinuityManager
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from continuity_state import ExcursionRecord, ExcursionStatus
from turn_runner_audit import log_character_turn_audit


def test_scene_state_after_mirror_is_to_dict_only() -> None:
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Lab",
        opening_description="o",
        present_characters=["A", "B"],
    )
    assert mgr.scene_state is not None
    d1 = scene_state_after_runtime_mirror(mgr.scene_state)
    d2 = mgr.scene_state.to_dict()
    assert d1 == d2
    for key in (
        "location",
        "present_characters",
        "offstage_characters",
        "character_presence_status",
    ):
        assert key in d1


def test_excursion_digest_none_without_scene() -> None:
    m = SimpleNamespace(scene_state=None, excursions={})
    assert build_excursion_audit_digest_v1(m) is None


def test_excursion_digest_sorted_ids_and_status_only() -> None:
    r_b = ExcursionRecord(
        excursion_id="b",
        participant_character_ids=["A"],
        status=ExcursionStatus.ACTIVE,
        opened_at_turn=1,
    )
    r_a = ExcursionRecord(
        excursion_id="a",
        participant_character_ids=["A", "B"],
        status=ExcursionStatus.CLOSED,
        opened_at_turn=1,
        closed_at_turn=2,
    )
    m = SimpleNamespace(
        scene_state=object(),
        excursions={"b": r_b, "a": r_a},
    )
    dig = build_excursion_audit_digest_v1(m)
    assert dig == [
        {"excursion_id": "a", "status": "closed"},
        {"excursion_id": "b", "status": "active"},
    ]


def test_log_character_includes_excursion_digest_and_scene_mirror() -> None:
    captured: dict = {}

    class _Logger:
        def create_entry(self, **kwargs):
            captured.clear()
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry) -> None:
            pass

    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test",
        present_characters=["A", "B"],
    )
    mgr.scene_state.role_assignments = {"A": "guest", "B": "staff"}
    complete_setup_seam_for_test_manager(mgr, cast=["A", "B"])

    mgr.process_turn(
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
        director_decision={
            "next_actor": "B",
            "environment_event": "",
            "tension_shift": "none",
            "reason": "test",
        },
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )

    log_character_turn_audit(
        next_actor="A",
        move={"action": "x", "dialogue": ""},
        task_prompt="sys",
        char_raw_response="{}",
        decision={"next_actor": "B"},
        char_names=["A", "B"],
        continuity_manager=mgr,
        round_number=1,
        turn_number=1,
        character_summary_block_audit={
            "summary_generation_eligible": False,
            "summary_blocks_generated_total": 0,
            "generated_summary_block_ids": [],
            "summary_blocks_available_count": 0,
            "available_summary_block_ids": [],
            "summary_blocks_selected_count": 0,
            "selected_summary_block_ids": [],
            "excluded_summary_block_ids": [],
            "selection_reason": "",
            "skipped_reason": "",
            "fallback_used": False,
            "summary_limit": None,
            "has_binding_constraints": False,
            "scene_binding_constraints_section": "",
        },
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
        effective_user_trigger="",
    )

    meta = captured.get("metadata") or {}
    assert "excursion_audit_digest_v1" in meta
    dig = meta["excursion_audit_digest_v1"]
    assert isinstance(dig, list) and len(dig) >= 1
    by_id = {r["excursion_id"]: r for r in dig}
    assert "ex1" in by_id
    row = by_id["ex1"]
    assert set(row.keys()) == {"excursion_id", "status"}
    assert "participant_character_ids" not in row
    snap = captured.get("context_snapshot") or {}
    assert "excursion_audit_digest_v1" not in snap
    ssa = snap.get("scene_state_after") or {}
    assert ssa.get("location") == mgr.scene_state.location
    assert ssa.get("present_characters") == list(mgr.scene_state.present_characters)
    assert isinstance(ssa.get("character_presence_status"), dict)

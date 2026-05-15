"""Issue #77 — excursion authority scaffolding (no presence / reintegration)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from continuity_state import ExcursionStatus


def test_open_update_close_excursion_record_only() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A", "B"],
    )
    complete_setup_seam_for_test_manager(m)
    eid = m.open_excursion(participant_character_ids=["A"])
    assert eid in m.excursions
    assert m.excursions[eid].status == ExcursionStatus.ACTIVE
    assert m.active_excursion_character_ids() == {"A"}
    assert set(m.scene_state.present_characters or []) == {"B"}
    assert (
        set(m.scene_state.present_characters or [])
        & m.active_excursion_character_ids()
        == set()
    )
    m.update_excursion(eid, participant_character_ids=["A", "B"])
    assert m.active_excursion_character_ids() == {"A", "B"}
    assert m.scene_state.present_characters == []
    assert (
        set(m.scene_state.present_characters or [])
        & m.active_excursion_character_ids()
        == set()
    )
    m.close_excursion(eid)
    assert m.excursions[eid].status == ExcursionStatus.CLOSED
    assert m.excursions[eid].closed_at_turn == m.turn_counter
    assert m.active_excursion_character_ids() == set()
    assert set(m.scene_state.present_characters or []) == {"A", "B"}
    assert (
        set(m.scene_state.present_characters or [])
        & m.active_excursion_character_ids()
        == set()
    )


def test_initialize_scene_clears_excursions() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A"],
    )
    complete_setup_seam_for_test_manager(m)
    m.open_excursion(participant_character_ids=["A"])
    m.initialize_scene(
        location="Y",
        opening_description="p",
        present_characters=["B"],
    )
    assert m.excursions == {}


def test_excursions_roundtrip_serialization() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A", "B"],
    )
    complete_setup_seam_for_test_manager(m)
    m.open_excursion(participant_character_ids=["A"], excursion_id="ex1")
    m.close_excursion("ex1")
    m.open_excursion(participant_character_ids=["B"], excursion_id="ex2")
    loaded = ContinuityManager.from_dict(m.to_dict())
    assert len(loaded.excursions) == 2
    assert loaded.excursions["ex1"].status == ExcursionStatus.CLOSED
    assert loaded.excursions["ex2"].status == ExcursionStatus.ACTIVE
    assert loaded.active_excursion_character_ids() == {"B"}


def test_open_excursion_duplicate_id_raises() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A"],
    )
    complete_setup_seam_for_test_manager(m)
    m.open_excursion(participant_character_ids=["A"], excursion_id="same")
    with pytest.raises(ValueError, match="already exists"):
        m.open_excursion(participant_character_ids=["A"], excursion_id="same")


def test_active_excursion_character_ids_is_pure() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A", "B", "C"],
    )
    complete_setup_seam_for_test_manager(m)
    m.open_excursion(participant_character_ids=["A"], excursion_id="e1")
    m.open_excursion(participant_character_ids=["B", "C"], excursion_id="e2")
    s1 = m.active_excursion_character_ids()
    s2 = m.active_excursion_character_ids()
    assert s1 == s2 == {"A", "B", "C"}
    s1.add("Z")
    assert "Z" not in m.active_excursion_character_ids()


def test_excursion_focal_boundary_after_open_all_cast_on_excursion() -> None:
    """P_focal ∩ E_active = ∅; all on excursion may leave present empty."""
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A", "B"],
    )
    complete_setup_seam_for_test_manager(m)
    m.open_excursion(participant_character_ids=["A", "B"], excursion_id="ex1")
    assert m.scene_state.present_characters == []
    assert m.active_excursion_character_ids() == {"A", "B"}


def test_ensure_one_does_not_reintroduce_excursion_participants() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A"],
    )
    complete_setup_seam_for_test_manager(m, cast=["A", "B"])
    m.scene_state.present_characters = []
    m.scene_state.offstage_characters = ["A", "B"]
    m.scene_state.character_presence_status = {
        "A": "temporary_offstage",
        "B": "temporary_offstage",
    }
    m.open_excursion(participant_character_ids=["A"], excursion_id="ex1")
    assert m.scene_state.present_characters == ["B"]
    assert m.scene_state.present_characters[0] not in m.active_excursion_character_ids()


def test_close_excursion_resync_may_restore_focal_eligible_character() -> None:
    """After close, E_active is empty so ensure-one may re-enter a non-excursion cast member."""
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="o",
        present_characters=["A"],
    )
    complete_setup_seam_for_test_manager(m)
    # Single-cast finalize can leave role_assignments empty; ensure-one tiers need cast keys.
    m.scene_state.role_assignments.setdefault("A", "guest")
    eid = m.open_excursion(participant_character_ids=["A"])
    assert m.scene_state.present_characters == []
    m.close_excursion(eid)
    assert m.scene_state.present_characters == ["A"]
    assert m.active_excursion_character_ids() == set()

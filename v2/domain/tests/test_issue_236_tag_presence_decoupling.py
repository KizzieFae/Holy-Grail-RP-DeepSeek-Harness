"""GitHub #236 — classifier tag→presence commit decoupling."""

from __future__ import annotations

import sys
from pathlib import Path


from continuity_manager import ContinuityManager  # noqa: E402
from continuity_presence_helpers import (  # noqa: E402
    apply_canonical_reentry_scratch,
    presence_scratch_from_scene_state,
)
from continuity_scene_state_update import run_update_scene_state  # noqa: E402
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402


def _minimal_v2(**extra: object) -> dict:
    base = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "blinks."}],
        "motivation": {
            "goal": "idle",
            "tactic": "wait",
            "emotional_driver": "flat",
            "risk_level": "low",
        },
    }
    base.update(extra)
    return base


def test_exit_tag_helper_removed_from_presence_helpers() -> None:
    import continuity_presence_helpers as mod

    assert not hasattr(mod, "apply_canonical_exit_offstage_transition_scratch")


def test_tag_only_run_update_scene_state_does_not_commit() -> None:
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    before = list(mgr.scene_state.present_characters)
    run_update_scene_state(
        mgr,
        actor,
        _minimal_v2(),
        {"next_actor": other},
        None,
        {"tags": ["exit"]},
    )
    assert list(mgr.scene_state.present_characters) == before


def test_tag_only_process_turn_does_not_commit() -> None:
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    before = list(mgr.scene_state.present_characters)
    mgr.process_turn(
        acting_character=actor,
        move=_minimal_v2(),
        director_decision={"next_actor": other, "tags": ["exit"]},
        other_characters=[other],
    )
    assert list(mgr.scene_state.present_characters) == before


def test_accepted_off_focal_proposal_still_commits() -> None:
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    mgr.process_turn(
        acting_character=actor,
        move=_minimal_v2(semantic_proposals=[{"kind": "off_focal", "character": actor}]),
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert actor not in mgr.scene_state.present_characters
    assert actor in mgr.scene_state.offstage_characters


def test_reentry_scratch_helper_unchanged() -> None:
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Bob"],
    )
    scratch = presence_scratch_from_scene_state(mgr.scene_state)
    scratch.offstage_characters = ["Alice"]
    scratch.character_presence_status["Alice"] = "temporary_offstage"
    apply_canonical_reentry_scratch(scratch, "Alice")
    assert "Alice" in scratch.present_characters
    assert "Alice" not in scratch.offstage_characters

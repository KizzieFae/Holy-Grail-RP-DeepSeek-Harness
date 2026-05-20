"""GitHub #235 — remove reconstruction-era covered presence commits."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_consequence_classifier_move_tools import (  # noqa: E402
    move_with_flat_text_for_deterministic_tools,
)
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_scene_state_update import run_update_scene_state  # noqa: E402
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402
from scene_exit_detection import detect_exit_from_scene, has_scene_reentry_evidence  # noqa: E402


def _minimal_v2(**extra: object) -> dict:
    base = {
        "move_schema_version": 2,
        "beats": [
            {
                "type": "action",
                "action": "She left the room and shut the door behind her.",
            }
        ],
        "motivation": {
            "goal": "leave",
            "tactic": "exit",
            "emotional_driver": "resolve",
            "risk_level": "medium",
        },
    }
    base.update(extra)
    return base


def test_prose_detect_exit_does_not_commit_without_proposal() -> None:
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    move = _minimal_v2()
    flat = move_with_flat_text_for_deterministic_tools(move)
    assert mgr.scene_state is not None
    assert detect_exit_from_scene(flat, mgr.scene_state.to_dict(), actor)
    before = list(mgr.scene_state.present_characters)
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert list(mgr.scene_state.present_characters) == before


def test_flatten_reentry_evidence_does_not_commit_without_proposal() -> None:
    move = _minimal_v2(
        beats=[
            {
                "type": "action",
                "action": "She walked back into the dorm room and shut the door.",
            }
        ],
    )
    flat = move_with_flat_text_for_deterministic_tools(move)
    assert has_scene_reentry_evidence(flat)
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[other],
    )
    complete_setup_seam_for_test_manager(mgr)
    assert mgr.scene_state is not None
    mgr.scene_state.offstage_characters = [actor]
    mgr.scene_state.character_presence_status[actor] = "temporary_offstage"
    before_present = list(mgr.scene_state.present_characters)
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert list(mgr.scene_state.present_characters) == before_present
    assert actor not in mgr.scene_state.present_characters


def test_accepted_proposal_still_commits_off_focal() -> None:
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
        move=_minimal_v2(
            semantic_proposals=[{"kind": "off_focal", "character": actor}],
        ),
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert actor not in mgr.scene_state.present_characters
    assert actor in mgr.scene_state.offstage_characters


def test_run_update_scene_state_has_no_reconstruction_imports() -> None:
    import continuity_scene_state_update as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "_SUPPRESS_RECONSTRUCTION_COVERED_COMMITS" not in source
    assert "has_scene_reentry_evidence" not in source
    assert "apply_canonical_exit_offstage_transition_scratch" not in source

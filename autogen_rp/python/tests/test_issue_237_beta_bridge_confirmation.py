"""GitHub #237 — confirm β′ / flatten / detect covered commit paths absent; proposal authority intact."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager  # noqa: E402
from continuity_scene_state_update import run_update_scene_state  # noqa: E402
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402


def _minimal_v2(**extra: object) -> dict:
    base = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "She left the room and shut the door."}],
        "motivation": {
            "goal": "leave",
            "tactic": "exit",
            "emotional_driver": "resolve",
            "risk_level": "medium",
        },
    }
    base.update(extra)
    return base


def test_no_beta_prime_symbol_in_presence_helpers() -> None:
    import continuity_presence_helpers as mod

    assert not hasattr(mod, "apply_canonical_exit_offstage_transition_scratch")
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "beta_prime" not in source
    assert "β" not in source


def test_run_update_scene_state_has_no_covered_reconstruction_or_beta_commits() -> None:
    import continuity_scene_state_update as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    forbidden = (
        "has_scene_reentry_evidence",
        "detect_exit_from_scene",
        "has_hard_scene_departure_evidence",
        "move_with_flat_text_for_deterministic_tools",
        "apply_canonical_exit_offstage_transition_scratch",
        "beta_prime",
        "_SUPPRESS_RECONSTRUCTION_COVERED_COMMITS",
    )
    for token in forbidden:
        assert token not in source
    assert "apply_accepted_proposal_presence_to_scratch" in source


def test_classifier_still_imports_detect_exit_observationally() -> None:
    import continuity_consequence_classifier as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "detect_exit_from_scene" in source


def test_detect_only_flatten_does_not_commit_without_proposal() -> None:
    from continuity_consequence_classifier_move_tools import (  # noqa: E402
        move_with_flat_text_for_deterministic_tools,
    )
    from scene_exit_detection import detect_exit_from_scene  # noqa: E402

    actor = "Willow_Reeves"
    other = "Marlene_Fletcher"
    move = _minimal_v2()
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    flat = move_with_flat_text_for_deterministic_tools(move)
    assert detect_exit_from_scene(flat, mgr.scene_state.to_dict(), actor)
    before = list(mgr.scene_state.present_characters)
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert list(mgr.scene_state.present_characters) == before


def test_proposal_off_focal_still_commits_after_237_posture() -> None:
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


def test_run_update_scene_state_proposal_only_entrypoint() -> None:
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

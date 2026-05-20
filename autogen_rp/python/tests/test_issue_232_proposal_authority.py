"""GitHub #232 — continuity authority for semantic proposals."""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager  # noqa: E402
from continuity_semantic_proposals import (  # noqa: E402
    REASON_ILLEGAL_ALREADY_OFF_FOCAL,
    REASON_MUST_REMAIN_OFF_FOCAL,
    REASON_SCOPE_NON_SELF,
    ContinuityProposalLegalityError,
    ProposalAuthorityOutcome,
    evaluate_proposal_legality,
)
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402


def _minimal_v2(**extra: object) -> dict:
    base = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "steps toward the door"}],
        "motivation": {
            "goal": "leave focal",
            "tactic": "move",
            "emotional_driver": "tired",
            "risk_level": "low",
        },
    }
    base.update(extra)
    return base


def test_legality_no_proposal() -> None:
    ctx = evaluate_proposal_legality(
        _minimal_v2(),
        acting_character="Alice",
        scene_state={"present_characters": ["Alice"]},
    )
    assert ctx.outcome == ProposalAuthorityOutcome.NO_PROPOSAL


def test_legality_reject_must_remain_off_focal() -> None:
    ctx = evaluate_proposal_legality(
        _minimal_v2(
            semantic_proposals=[{"kind": "off_focal", "character": "Alice"}],
        ),
        acting_character="Alice",
        scene_state={
            "present_characters": ["Alice"],
            "character_presence_constraints": {"Alice": "must_remain"},
        },
    )
    assert ctx.outcome == ProposalAuthorityOutcome.REJECT
    assert ctx.reason_code == REASON_MUST_REMAIN_OFF_FOCAL


def test_legality_reject_scope_non_self() -> None:
    ctx = evaluate_proposal_legality(
        _minimal_v2(
            semantic_proposals=[{"kind": "off_focal", "character": "Bob"}],
        ),
        acting_character="Alice",
        scene_state={"present_characters": ["Alice", "Bob"]},
    )
    assert ctx.outcome == ProposalAuthorityOutcome.REJECT
    assert ctx.reason_code == REASON_SCOPE_NON_SELF


def test_legality_accept_off_focal() -> None:
    ctx = evaluate_proposal_legality(
        _minimal_v2(
            semantic_proposals=[{"kind": "off_focal", "character": "Alice"}],
        ),
        acting_character="Alice",
        scene_state={"present_characters": ["Alice", "Bob"]},
    )
    assert ctx.outcome == ProposalAuthorityOutcome.ACCEPT


def test_process_turn_accept_off_focal_commits() -> None:
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    move = _minimal_v2(
        semantic_proposals=[{"kind": "off_focal", "character": actor}],
    )
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert actor not in mgr.scene_state.present_characters
    assert actor in mgr.scene_state.offstage_characters


def test_process_turn_no_proposal_no_covered_commit() -> None:
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
    move = _minimal_v2()
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": other, "tags": ["exit"]},
        other_characters=[other],
    )
    assert list(mgr.scene_state.present_characters) == before


def test_process_turn_reject_raises_without_commit() -> None:
    actor = "Alice"
    other = "Bob"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    assert mgr.scene_state is not None
    mgr.scene_state.character_presence_constraints = {actor: "must_remain"}
    complete_setup_seam_for_test_manager(mgr)
    move = _minimal_v2(
        semantic_proposals=[{"kind": "off_focal", "character": actor}],
    )
    before = list(mgr.scene_state.present_characters)
    with pytest.raises(ContinuityProposalLegalityError):
        mgr.process_turn(
            acting_character=actor,
            move=move,
            director_decision={"next_actor": other},
            other_characters=[other],
        )
    assert list(mgr.scene_state.present_characters) == before


def test_suppression_exit_tag_does_not_commit_without_proposal() -> None:
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
    turn_consequences = {"tags": ["exit"]}
    from continuity_scene_state_update import run_update_scene_state

    run_update_scene_state(
        mgr,
        actor,
        move,
        {"next_actor": other},
        None,
        turn_consequences,
    )
    assert actor in mgr.scene_state.present_characters


def test_legality_reject_already_off_focal() -> None:
    ctx = evaluate_proposal_legality(
        _minimal_v2(
            semantic_proposals=[{"kind": "off_focal", "character": "Alice"}],
        ),
        acting_character="Alice",
        scene_state={
            "present_characters": ["Bob"],
            "offstage_characters": ["Alice"],
        },
    )
    assert ctx.outcome == ProposalAuthorityOutcome.REJECT
    assert ctx.reason_code == REASON_ILLEGAL_ALREADY_OFF_FOCAL

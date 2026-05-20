"""GitHub #230 Phase A — semantic_proposals wire, ingress, non-consumption."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_loader import CharacterLoader  # noqa: E402
from character_move_ingress import (  # noqa: E402
    MAX_V2_SEMANTIC_PROPOSALS,
    ingest_character_move_json_object,
    validate_canonical_v2,
)
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_semantic_proposals import ContinuityProposalLegalityError  # noqa: E402
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402


def _minimal_v2(**extra: object) -> dict:
    base = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "glances around the room"}],
        "motivation": {
            "goal": "observe",
            "tactic": "wait",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
    }
    base.update(extra)
    return base


def test_ingress_accepts_semantic_proposals_and_retains_on_handoff() -> None:
    d = _minimal_v2(
        semantic_proposals=[
            {"kind": "off_focal", "character": "Celina"},
            {"kind": "excursion_lifecycle", "character": "Kizzie", "operation": "open"},
        ]
    )
    m, err = ingest_character_move_json_object(d)
    assert err == ""
    assert m is not None
    assert m.get("semantic_proposals") == d["semantic_proposals"]


@pytest.mark.parametrize(
    "illegal_root",
    ["presence_changes", "excursion_lifecycle", "spatial_transition"],
)
def test_ingress_rejects_reconstruction_era_root_carriers(illegal_root: str) -> None:
    d = _minimal_v2(**{illegal_root: [] if illegal_root == "presence_changes" else {}})
    m, err = ingest_character_move_json_object(d)
    assert m is None
    assert err and "unknown" in err.lower()


def test_validate_excursion_lifecycle_requires_operation() -> None:
    d = _minimal_v2(
        semantic_proposals=[{"kind": "excursion_lifecycle", "character": "A"}]
    )
    assert "operation" in validate_canonical_v2(d)


def test_validate_off_focal_rejects_operation() -> None:
    d = _minimal_v2(
        semantic_proposals=[
            {"kind": "off_focal", "character": "A", "operation": "open"},
        ]
    )
    assert "must not include operation" in validate_canonical_v2(d)


def test_validate_semantic_proposals_cap() -> None:
    items = [{"kind": "off_focal", "character": f"C{i}"} for i in range(MAX_V2_SEMANTIC_PROPOSALS + 1)]
    d = _minimal_v2(semantic_proposals=items)
    assert "exceeds cap" in validate_canonical_v2(d)


def test_process_turn_no_proposal_no_covered_commit() -> None:
    """#232: without proposals, covered semantics do not commit (legacy suppressed)."""
    actor = "Ayame"
    other = "Celina"
    base_move = _minimal_v2()

    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    before = (
        list(mgr.scene_state.present_characters or []),
        list(mgr.scene_state.offstage_characters or []),
    )
    mgr.process_turn(
        acting_character=actor,
        move=base_move,
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    after = (
        list(mgr.scene_state.present_characters or []),
        list(mgr.scene_state.offstage_characters or []),
    )
    assert before == after


def test_process_turn_wrong_scope_proposal_rejects() -> None:
    actor = "Ayame"
    other = "Celina"
    with_proposals = _minimal_v2(
        semantic_proposals=[{"kind": "off_focal", "character": other}],
    )
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    with pytest.raises(ContinuityProposalLegalityError):
        mgr.process_turn(
            acting_character=actor,
            move=with_proposals,
            director_decision={"next_actor": other},
            other_characters=[other],
        )


@patch("character_loader.AssistantAgent")
def test_character_loader_system_prompt_teaches_proposals_not_illegal_roots(
    mock_agent_cls: MagicMock,
) -> None:
    mock_agent_cls.return_value = MagicMock()
    loader = CharacterLoader()
    loader.create_agent(
        {"name": "Ayame", "description": "Test character."},
        MagicMock(),
    )
    system = str(mock_agent_cls.call_args.kwargs["system_message"])
    assert "semantic_proposals" in system
    assert "semantic commit intent" in system.lower()
    assert "MUST emit when this turn has off-focal" in system
    assert "prose implication is insufficient" in system
    assert "continuity evaluates and accepts or rejects this turn" in system
    assert "emission alone is not proof of commit" in system
    assert "committing later" not in system.lower()
    assert "#232" not in system
    assert "Do not use root presence_changes" in system
    assert "ingress rejects them" in system
    assert "excursion_lifecycle on the move" not in system
    assert "presence_changes for explicit reentry" not in system
    assert "spatial_transition when committing location" not in system

"""Presence and eligibility projection tests for the V2 Domain API."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    DirectorDecisionValidationRequest,
    EligibleActorsRequest,
    RoundStartRequest,
    ValidationRequest,
)
from domain_api.fixture_store import FixtureStore
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_ALICE_OFFSTAGE_MOVE,
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_DIRECTOR_DECISION_BOB,
    DomainKernel,
)


@pytest.fixture
def kernel() -> DomainKernel:
    k = DomainKernel.for_fixture_store()
    scene = k.create_scene()
    k.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
    return k


def _scene_and_round(kernel: DomainKernel) -> tuple[str, str]:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    assert fixture.rounds
    return fixture.hg_scene_id, fixture.rounds[-1].hg_round_id


def _commit_move(
    kernel: DomainKernel,
    *,
    character_id: str,
    move: dict,
    director_decision: dict,
    expected_turn_index: int,
) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id=f"inf-{character_id}",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id=character_id,
            role="guest",
            turn_index=expected_turn_index,
            attempt_index=0,
            proposed_move=move,
            raw_model_output=json.dumps(move),
        )
    )
    assert validation.accepted is True
    assert validation.normalized_move is not None
    commit = kernel.commit_move(
        CommitRequest(
            inference_id=f"inf-{character_id}",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id=character_id,
            validated_move=validation.normalized_move,
            director_decision=director_decision,
            expected_turn_index=expected_turn_index,
        )
    )
    assert commit.committed is True


def test_eligible_actors_projection_includes_presence_fields(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    result = kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )
    assert result.present_characters == ("Alice", "Bob")
    assert result.offstage_characters == ()
    assert result.absent_but_relevant == ()
    assert len(result.actors) == 2
    by_id = {entry.character_id: entry for entry in result.actors}
    assert by_id["Alice"].eligibility_status == "eligible"
    assert by_id["Alice"].presence_status == "present"
    assert by_id["Alice"].exclusion_reason is None


def test_offstage_actor_is_ineligible(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    mgr = fixture.manager
    assert mgr.scene_state is not None
    mgr.scene_state.offstage_characters = ["Alice"]
    result = kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )
    assert "Alice" not in result.eligible_actors
    assert "Bob" in result.eligible_actors
    alice = next(a for a in result.actors if a.character_id == "Alice")
    assert alice.eligibility_status == "ineligible"
    assert alice.presence_status == "offstage"
    assert alice.exclusion_reason == "offstage"


def test_absent_but_relevant_actor_is_ineligible(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    mgr = fixture.manager
    assert mgr.scene_state is not None
    mgr.scene_state.present_characters = ["Bob"]
    mgr.scene_state.absent_but_relevant = ["Alice"]
    result = kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )
    assert "Alice" not in result.eligible_actors
    alice = next(a for a in result.actors if a.character_id == "Alice")
    assert alice.presence_status == "absent_but_relevant"
    assert alice.exclusion_reason == "absent_but_relevant"


def test_off_focal_commit_updates_later_eligibility(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    before = kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )
    assert before.eligible_actors == ("Alice", "Bob")

    _commit_move(
        kernel,
        character_id="Alice",
        move=PROTOTYPE_ALICE_OFFSTAGE_MOVE,
        director_decision=PROTOTYPE_DIRECTOR_DECISION,
        expected_turn_index=0,
    )

    after = kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )
    assert "Alice" in after.actors_used_this_round
    assert "Alice" not in after.eligible_actors
    assert "Bob" in after.eligible_actors
    assert "Alice" in after.offstage_characters
    alice = next(a for a in after.actors if a.character_id == "Alice")
    assert alice.exclusion_reason == "already_used_this_round"


def test_director_rejects_offstage_actor(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    mgr = fixture.manager
    assert mgr.scene_state is not None
    mgr.scene_state.offstage_characters = ["Alice"]
    result = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-offstage",
            turn_index=0,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION,
            raw_model_output=json.dumps(PROTOTYPE_DIRECTOR_DECISION),
        )
    )
    assert result.accepted is False
    assert "offstage" in (result.reason or "")


def test_director_rejects_offstage_actor_after_off_focal_commit(kernel: DomainKernel) -> None:
    _commit_move(
        kernel,
        character_id="Alice",
        move=PROTOTYPE_ALICE_OFFSTAGE_MOVE,
        director_decision=PROTOTYPE_DIRECTOR_DECISION,
        expected_turn_index=0,
    )
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    result = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-offstage-after-commit",
            turn_index=1,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION,
            raw_model_output=json.dumps(PROTOTYPE_DIRECTOR_DECISION),
        )
    )
    assert result.accepted is False
    assert "already_used_this_round" in (result.reason or "")

    bob_only = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-bob",
            turn_index=1,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION_BOB,
            raw_model_output=json.dumps(PROTOTYPE_DIRECTOR_DECISION_BOB),
        )
    )
    assert bob_only.accepted is True


def test_scene_snapshot_reflects_authoritative_presence(kernel: DomainKernel) -> None:
    hg_scene_id, _ = _scene_and_round(kernel)
    _commit_move(
        kernel,
        character_id="Alice",
        move=PROTOTYPE_ALICE_OFFSTAGE_MOVE,
        director_decision=PROTOTYPE_DIRECTOR_DECISION,
        expected_turn_index=0,
    )
    snapshot = kernel.scene_snapshot(hg_scene_id)
    assert "Alice" not in snapshot.present_characters
    assert "Bob" in snapshot.present_characters

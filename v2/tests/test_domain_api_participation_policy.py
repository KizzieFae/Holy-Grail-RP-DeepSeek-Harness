"""Participation policy and ParticipationDecision tests for the V2 Domain API."""

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
    EligibleActorEntry,
    EligibleActorsRequest,
    EligibleActorsResponse,
    ParticipationDecisionRequest,
    RoundStartRequest,
    ValidationRequest,
)
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_ALICE_BLUEPRINT_MOVE,
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_DIRECTOR_DECISION_BOB,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.participation_policy import (  # noqa: E402
    evaluate_participation_policy,
    resolve_continuation_actor,
)


@pytest.fixture
def kernel() -> DomainKernel:
    k = DomainKernel()
    scene = k.create_scene()
    k.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
    return k


def _scene_and_round(kernel: DomainKernel) -> tuple[str, str]:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    assert fixture.rounds
    return fixture.hg_scene_id, fixture.rounds[-1].hg_round_id


def _eligibility(kernel: DomainKernel, hg_scene_id: str, hg_round_id: str):
    return kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )


def _participation(
    kernel: DomainKernel,
    hg_scene_id: str,
    hg_round_id: str,
    *,
    forced_designation: str | None = None,
):
    eligibility = _eligibility(kernel, hg_scene_id, hg_round_id)
    return kernel.participation_decision(
        ParticipationDecisionRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            eligibility_snapshot_id=eligibility.eligibility_snapshot_id,
            forced_designation=forced_designation,
        )
    )


def _commit(kernel: DomainKernel, character_id: str, move: dict, director_decision: dict) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    turn_index = int(fixture.manager.turn_counter)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id=f"inf-{character_id}",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id=character_id,
            role="guest",
            turn_index=turn_index,
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
            expected_turn_index=turn_index,
        )
    )
    assert commit.committed is True


def test_eligibility_includes_snapshot_id(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    eligibility = _eligibility(kernel, hg_scene_id, hg_round_id)
    assert eligibility.eligibility_snapshot_id.endswith(":0")


def test_forced_designation_selects_eligible_actor_directly(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    decision = _participation(kernel, hg_scene_id, hg_round_id, forced_designation="Alice")
    assert decision.selection_mode == "direct"
    assert decision.selected_actor == "Alice"
    assert decision.director_required is False
    assert decision.participation_sources == ("forced_designation",)


def test_forced_designation_ignored_when_already_used(kernel: DomainKernel) -> None:
    _commit(kernel, "Alice", PROTOTYPE_VALID_MOVE, PROTOTYPE_DIRECTOR_DECISION)
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    decision = _participation(kernel, hg_scene_id, hg_round_id, forced_designation="Alice")
    assert decision.selection_mode == "director"
    assert decision.selected_actor is None
    assert decision.forced_designation_ignored is True
    assert decision.forced_designation_ignore_reason == "already_used_this_round"


def test_forced_designation_ignored_when_offstage(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.offstage_characters = ["Alice"]
    decision = _participation(kernel, hg_scene_id, hg_round_id, forced_designation="Alice")
    assert decision.selection_mode == "director"
    assert decision.forced_designation_ignored is True
    assert decision.forced_designation_ignore_reason == "offstage"


def test_forced_designation_ignored_when_not_in_cast(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    decision = _participation(kernel, hg_scene_id, hg_round_id, forced_designation="Carol")
    assert decision.forced_designation_ignored is True
    assert decision.forced_designation_ignore_reason == "not_in_cast"


def test_forced_designation_takes_priority_over_continuation(kernel: DomainKernel) -> None:
    _commit(kernel, "Alice", PROTOTYPE_ALICE_BLUEPRINT_MOVE, PROTOTYPE_DIRECTOR_DECISION)
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    decision = _participation(kernel, hg_scene_id, hg_round_id, forced_designation="Bob")
    assert decision.selection_mode == "direct"
    assert decision.selected_actor == "Bob"
    assert decision.participation_sources == ("forced_designation",)


def test_continuation_suppressed_when_present_peer_unheard(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    rnd.character_turns.append(
        type("Turn", (), {
            "character_id": "Alice",
            "committed_move": PROTOTYPE_ALICE_BLUEPRINT_MOVE,
            "domain_commit_id": "x",
            "continuity_turn_index": 1,
            "director_decision": PROTOTYPE_DIRECTOR_DECISION,
        })()
    )
    rnd.spotlight_history = ["Alice"]
    rnd.actors_used_this_round = ["Alice"]
    decision = _participation(kernel, hg_scene_id, hg_round_id)
    assert decision.selection_mode == "director"
    assert "continuation_preference" not in decision.participation_sources


def test_continuation_c2_skip_defers_to_director(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    rnd.character_turns.append(
        type("Turn", (), {
            "character_id": "Alice",
            "committed_move": PROTOTYPE_ALICE_BLUEPRINT_MOVE,
            "domain_commit_id": "x",
            "continuity_turn_index": 1,
            "director_decision": PROTOTYPE_DIRECTOR_DECISION,
        })()
    )
    rnd.spotlight_history = ["Bob", "Alice"]
    rnd.actors_used_this_round = ["Alice", "Bob"]
    eligibility = EligibleActorsResponse(
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        eligibility_snapshot_id=kernel._eligibility_snapshot_id(rnd),
        eligible_actors=("Alice",),
        actors_used_this_round=("Alice", "Bob"),
        character_roles={"Alice": "guest", "Bob": "staff"},
        actors=(
            EligibleActorEntry("Alice", "eligible", "present"),
            EligibleActorEntry("Bob", "eligible", "present"),
        ),
        present_characters=("Alice", "Bob"),
        offstage_characters=(),
        absent_but_relevant=(),
    )
    decision = evaluate_participation_policy(
        fixture=fixture,
        rnd=rnd,
        eligibility=eligibility,
        eligibility_snapshot_id=eligibility.eligibility_snapshot_id,
        forced_designation=None,
    )
    assert decision.selection_mode == "director"
    assert decision.continuation_c2_skip is True
    assert decision.participation_sources == ("continuation_preference",)


def test_continuation_direct_when_offstage_peer_unheard(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    rnd.character_turns.append(
        type("Turn", (), {
            "character_id": "Alice",
            "committed_move": PROTOTYPE_ALICE_BLUEPRINT_MOVE,
            "domain_commit_id": "x",
            "continuity_turn_index": 1,
            "director_decision": PROTOTYPE_DIRECTOR_DECISION,
        })()
    )
    rnd.spotlight_history = []
    rnd.actors_used_this_round = ["Alice"]
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.offstage_characters = ["Bob"]
    eligibility = EligibleActorsResponse(
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        eligibility_snapshot_id=kernel._eligibility_snapshot_id(rnd),
        eligible_actors=("Alice",),
        actors_used_this_round=("Alice",),
        character_roles={"Alice": "guest", "Bob": "staff"},
        actors=(
            EligibleActorEntry(
                character_id="Alice",
                eligibility_status="eligible",
                presence_status="present",
            ),
            EligibleActorEntry(
                character_id="Bob",
                eligibility_status="ineligible",
                presence_status="offstage",
                exclusion_reason="offstage",
            ),
        ),
        present_characters=("Alice",),
        offstage_characters=("Bob",),
        absent_but_relevant=(),
    )
    decision = evaluate_participation_policy(
        fixture=fixture,
        rnd=rnd,
        eligibility=eligibility,
        eligibility_snapshot_id=eligibility.eligibility_snapshot_id,
        forced_designation=None,
    )
    assert decision.selection_mode == "direct"
    assert decision.selected_actor == "Alice"
    assert decision.participation_sources == ("continuation_preference",)


def test_director_validation_enforces_participation_constraint(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    eligibility = _eligibility(kernel, hg_scene_id, hg_round_id)
    rejected = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-constraint",
            turn_index=0,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION_BOB,
            raw_model_output=json.dumps(PROTOTYPE_DIRECTOR_DECISION_BOB),
            eligibility_snapshot_id=eligibility.eligibility_snapshot_id,
            director_constraint_actor="Alice",
        )
    )
    assert rejected.accepted is False
    assert "participation constraint" in rejected.reason


def test_director_validation_allows_c2_skip_mismatch(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    eligibility = _eligibility(kernel, hg_scene_id, hg_round_id)
    accepted = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-c2",
            turn_index=0,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION_BOB,
            raw_model_output=json.dumps(PROTOTYPE_DIRECTOR_DECISION_BOB),
            eligibility_snapshot_id=eligibility.eligibility_snapshot_id,
            director_constraint_actor="Alice",
            continuation_c2_skip=True,
        )
    )
    assert accepted.accepted is True


def test_stale_eligibility_snapshot_rejected(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    rejected = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-stale",
            turn_index=0,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION,
            eligibility_snapshot_id="stale-snapshot",
        )
    )
    assert rejected.accepted is False
    assert "stale eligibility snapshot" in rejected.reason


def test_commit_bumps_eligibility_snapshot(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    before = _eligibility(kernel, hg_scene_id, hg_round_id)
    _commit(kernel, "Alice", PROTOTYPE_VALID_MOVE, PROTOTYPE_DIRECTOR_DECISION)
    after = _eligibility(kernel, hg_scene_id, hg_round_id)
    assert before.eligibility_snapshot_id != after.eligibility_snapshot_id


def test_resolve_continuation_actor_matches_v1_offstage_unheard_rule(kernel: DomainKernel) -> None:
    hg_scene_id, _ = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    rnd.character_turns.append(
        type("Turn", (), {
            "character_id": "Alice",
            "committed_move": PROTOTYPE_ALICE_BLUEPRINT_MOVE,
            "domain_commit_id": "x",
            "continuity_turn_index": 1,
            "director_decision": PROTOTYPE_DIRECTOR_DECISION,
        })()
    )
    rnd.spotlight_history = ["Alice"]
    actor = resolve_continuation_actor(
        fixture=fixture,
        rnd=rnd,
        eligible_present=["Alice", "Bob"],
        actors_used_this_round=["Alice"],
        offstage_characters=["Bob"],
    )
    assert actor == "Alice"

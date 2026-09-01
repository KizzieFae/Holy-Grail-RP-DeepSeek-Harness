"""Tests for Director context digests and completeness contract (#26)."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_state import IssueState, IssueStatus  # noqa: E402
from domain_api.contract import (  # noqa: E402
    DirectorContextPrepareRequest,
    PromptContribution,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.director_context_digests import (  # noqa: E402
    MAX_ACTION_CHARS,
    MAX_DIALOGUE_CHARS,
    MAX_ORCHESTRATION_TURNS,
    build_director_authority_references,
    project_actor_suitability_digest,
    project_recent_orchestration_digest,
    project_scene_pressures_digest,
    project_user_turn_source_and_hints,
    validate_director_context_completeness,
)
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import PROTOTYPE_VALID_MOVE, DomainKernel  # noqa: E402
from domain_api.session_state import (  # noqa: E402
    CharacterTurnRecord,
    RoundFixture,
    initialize_live_session,
)


def _fixture_with_round() -> tuple:
    fixture = initialize_live_session(cast=["Alice", "Bob"])
    rnd = RoundFixture(
        hg_round_id="round-1",
        hg_scene_id=fixture.hg_scene_id,
        turn_index=0,
    )
    fixture.rounds.append(rnd)
    return fixture, rnd


def _move_with_dialogue(action: str, dialogue: str) -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": action},
            {"type": "dialogue", "dialogue": dialogue},
        ],
        "motivation": {"goal": "test", "tactic": "test"},
    }


def test_recent_orchestration_digest_bounds_and_refs() -> None:
    fixture, rnd = _fixture_with_round()
    for index in range(8):
        rnd.character_turns.append(
            CharacterTurnRecord(
                character_id="Alice" if index % 2 == 0 else "Bob",
                committed_move=_move_with_dialogue(
                    "a" * (MAX_ACTION_CHARS + 20),
                    "d" * (MAX_DIALOGUE_CHARS + 20),
                ),
                domain_commit_id=f"commit-{index}",
                continuity_turn_index=index,
                director_decision={},
            )
        )

    contribution, refs = project_recent_orchestration_digest(fixture, rnd, "manifest-test")
    assert contribution is not None
    assert contribution.source_kind == "recent_orchestration"
    payload = json.loads(contribution.content.split(":\n", 1)[1])
    assert len(payload["recent_orchestration"]) == MAX_ORCHESTRATION_TURNS
    first = payload["recent_orchestration"][0]
    assert len(first["action"]) <= MAX_ACTION_CHARS
    assert len(first["dialogue"]) <= MAX_DIALOGUE_CHARS
    assert refs[0]["ref_id"].startswith("orch:")
    assert refs[0]["authority_class"] == "authoritative"


def test_actor_suitability_digest_mixed_authority() -> None:
    fixture, rnd = _fixture_with_round()
    rnd.actors_used_this_round = ["Alice"]
    rnd.spotlight_history = ["Alice", "Bob", "Alice", "Bob"]
    rnd.character_turns.append(
        CharacterTurnRecord(
            character_id="Alice",
            committed_move=PROTOTYPE_VALID_MOVE,
            domain_commit_id="commit-1",
            continuity_turn_index=0,
            director_decision={},
        )
    )

    contribution, refs = project_actor_suitability_digest(
        fixture,
        rnd,
        ["Alice", "Bob"],
        "manifest-test",
        participation_mode="director_required",
    )
    assert contribution is not None
    assert contribution.source_kind == "actor_suitability"
    payload = json.loads(contribution.content.split(":\n", 1)[1])
    assert payload["eligible_actors"] == ["Alice", "Bob"]
    assert payload["actors_used_this_round"] == ["Alice"]
    assert payload["spotlight_last_3"] == ["Bob", "Alice", "Bob"]
    assert payload["last_speaker"] == "Alice"
    classes = {ref["authority_class"] for ref in refs}
    assert "authoritative" in classes
    assert "derived" in classes


def test_actor_suitability_omitted_for_single_eligible() -> None:
    fixture, rnd = _fixture_with_round()
    contribution, refs = project_actor_suitability_digest(
        fixture, rnd, ["Alice"], "manifest-test"
    )
    assert contribution is None
    assert refs == []


def test_scene_pressures_claim_specific_authority() -> None:
    fixture, _rnd = _fixture_with_round()
    issue = IssueState(
        issue_id="pressure-1",
        description="A blocked plan needs response.",
        participants=["Alice", "Bob"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.fromisoformat("2026-03-15T12:00:00"),
        pressure_kind="plan_execution",
        blocked_what="The proposed course",
        required_next_step="Someone must respond.",
        last_change="Alice refused.",
    )
    fixture.manager.issues[issue.issue_id] = issue
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.active_issue_ids = [issue.issue_id]

    contribution, refs = project_scene_pressures_digest(fixture, "manifest-test")
    assert contribution is not None
    ref_map = {ref["ref_id"]: ref["authority_class"] for ref in refs}
    assert ref_map["issue:pressure-1:status"] == "authoritative"
    assert ref_map["issue:pressure-1:required_next_step"] == "advisory"
    assert ref_map["issue:pressure-1:blocked_what"] == "derived"


def test_user_turn_source_authoritative_and_steering_hints_derived() -> None:
    fixture, _rnd = _fixture_with_round()
    fixture.rp_history.append(
        {
            "entry_id": "user-entry-1",
            "sequence_index": 0,
            "kind": "user",
            "content": "Bob, what do you think?",
            "metadata": {},
        }
    )

    contributions, refs = project_user_turn_source_and_hints(
        fixture, ["Alice", "Bob"], "manifest-test"
    )
    kinds = {contrib.source_kind for contrib in contributions}
    assert "user_turn_source" in kinds
    assert "user_steering_hints" in kinds
    source = next(c for c in contributions if c.source_kind == "user_turn_source")
    assert source.authority_class == "authoritative"
    assert "Bob, what do you think?" in source.content
    user_ref = next(ref for ref in refs if ref["ref_id"] == "user:user-entry-1")
    assert user_ref["authority_class"] == "authoritative"
    steer_ref = next(ref for ref in refs if ref["ref_id"].startswith("steer:"))
    assert steer_ref["authority_class"] == "derived"


def test_user_turn_source_omitted_after_skip() -> None:
    fixture, _rnd = _fixture_with_round()
    fixture.rp_history.extend(
        [
            {
                "entry_id": "user-entry-1",
                "sequence_index": 0,
                "kind": "user",
                "content": "Open the door.",
                "metadata": {},
            },
            {
                "entry_id": "skip-entry-1",
                "sequence_index": 1,
                "kind": "player_skip",
                "content": "Turn skipped",
                "metadata": {},
            },
        ]
    )
    contributions, refs = project_user_turn_source_and_hints(
        fixture, ["Alice", "Bob"], "manifest-test"
    )
    assert contributions == []
    assert refs == []


def test_build_director_authority_references_deduplicates() -> None:
    refs = build_director_authority_references(
        [
            {
                "ref_id": "orch:0:Alice",
                "kind": "orchestration_turn",
                "authority_class": "authoritative",
                "label": "A",
                "text": "one",
            }
        ],
        [
            {
                "ref_id": "orch:0:Alice",
                "kind": "orchestration_turn",
                "authority_class": "authoritative",
                "label": "B",
                "text": "two",
            },
            {
                "ref_id": "eligible:Alice",
                "kind": "eligibility_fact",
                "authority_class": "authoritative",
                "label": "Eligible",
                "text": "Alice eligible",
            },
        ],
    )
    assert [ref["ref_id"] for ref in refs] == ["orch:0:Alice", "eligible:Alice"]


def test_validate_director_context_completeness_conditional_requirements() -> None:
    base = [
        PromptContribution(
            contribution_id="scene-state",
            source_kind="scene_state",
            authority_class="authoritative",
            knowledge_ids=(),
            priority=1,
            content="scene",
        ),
        PromptContribution(
            contribution_id="scene-progression",
            source_kind="scene_progression",
            authority_class="authoritative",
            knowledge_ids=(),
            priority=2,
            content="progression",
        ),
        PromptContribution(
            contribution_id="instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(),
            priority=3,
            content="instruction",
        ),
    ]

    result = validate_director_context_completeness(
        base,
        has_round_turns=False,
        multiple_eligible=False,
        has_active_issues=False,
        has_user_turn=False,
    )
    assert result["satisfied"] is True

    with pytest.raises(ValueError, match="recent_orchestration"):
        validate_director_context_completeness(
            base,
            has_round_turns=True,
            multiple_eligible=False,
            has_active_issues=False,
            has_user_turn=False,
        )


def test_kernel_prepare_director_context_extended_response() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id = kernel.create_scene().hg_scene_id
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=scene_id,
            content="Bob, respond.",
            speaker="Player",
            hg_round_id=round_id,
        )
    )

    response = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-26",
            turn_index=0,
            attempt_index=0,
        )
    )
    kinds = {contrib.source_kind for contrib in response.contributions}
    assert "user_turn_source" in kinds
    assert "user_turn_trigger" not in kinds
    assert "actor_suitability" in kinds
    assert response.context_completeness["satisfied"] is True
    assert response.authority_references

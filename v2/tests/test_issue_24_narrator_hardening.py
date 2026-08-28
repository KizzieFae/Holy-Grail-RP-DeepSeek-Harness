"""Issue #24 Narrator hardening integration and scenario-grade tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.modules.progression_simulation_scenarios import load_scenario  # noqa: E402
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    DirectorDecisionValidationRequest,
    NarratorContextPrepareRequest,
    NarratorPresentationValidationRequest,
    PresentationRecordRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import DomainKernel, PROTOTYPE_VALID_MOVE  # noqa: E402
from domain_api.session_history import (  # noqa: E402
    INFERENCE_OUTCOME_OUTPUT_LIMIT,
    PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC,
    project_history_to_transcript,
)


def _validate_director(kernel: DomainKernel, scene_id: str, round_id: str, actor: str) -> dict:
    result = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-director-24",
            turn_index=0,
            attempt_index=0,
            proposed_decision={
                "next_actor": actor,
                "end_round": False,
                "reason": "eligible",
                "tension_shift": "steady",
                "environment_event": "",
            },
        )
    )
    assert result.accepted is True
    assert result.normalized_decision is not None
    return dict(result.normalized_decision)


def test_terminal_output_limit_uses_degraded_deterministic_fallback_for_ui() -> None:
    kernel = DomainKernel.for_fixture_store()
    created = kernel.create_session(cast=["Alice", "Bob"])
    session_id = created.hg_session_id
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id
    decision = _validate_director(kernel, session_id, round_id, "Alice")
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-24",
            hg_scene_id=session_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision=decision,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    kernel.record_presentation(
        PresentationRecordRequest(
            hg_session_id=session_id,
            domain_commit_id=str(commit.domain_commit_id),
            hg_round_id=round_id,
            character_id="Alice",
            presentation_text=None,
            presentation_failed=True,
            inference_outcome=INFERENCE_OUTCOME_OUTPUT_LIMIT,
        )
    )
    fixture = kernel.store.require(session_id)
    transcript = project_history_to_transcript(fixture.rp_history)
    presentation = next(entry for entry in fixture.rp_history if entry["kind"] == "presentation")
    assert presentation["presentation_status"] == "failed"
    assert presentation["metadata"]["presentation_source"] == PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC
    assert presentation["metadata"]["presentation_degraded"] is True
    assert transcript[-1]["presentation_failed"] is True
    assert "nods thoughtfully" in transcript[-1]["content"]


def test_kernel_validate_narrator_presentation_uses_committed_move() -> None:
    kernel = DomainKernel.for_fixture_store()
    created = kernel.create_session(cast=["Alice"])
    session_id = created.hg_session_id
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id
    decision = _validate_director(kernel, session_id, round_id, "Alice")
    move = {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "nods"},
            {"type": "speech", "dialogue": "hello there"},
        ],
        "motivation": {
            "goal": "greet",
            "tactic": "speech",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-speech",
            hg_scene_id=session_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=move,
            director_decision=decision,
            expected_turn_index=0,
        )
    )
    rejected = kernel.validate_narrator_presentation(
        NarratorPresentationValidationRequest(
            hg_scene_id=session_id,
            domain_commit_id=str(commit.domain_commit_id),
            presentation_text="Alice nodded without speech.",
        )
    )
    assert rejected.accepted is False
    accepted = kernel.validate_narrator_presentation(
        NarratorPresentationValidationRequest(
            hg_scene_id=session_id,
            domain_commit_id=str(commit.domain_commit_id),
            presentation_text='Alice nodded and said "hello there".',
        )
    )
    assert accepted.accepted is True


@pytest.mark.parametrize("scenario_id", ["arrival_setup", "strong_user_steer", "conflict_3char"])
def test_scenario_grade_narrator_hardening(scenario_id: str) -> None:
    scenario = load_scenario(scenario_id)
    kernel = DomainKernel.for_fixture_store()
    info = kernel.create_session(cast=list(scenario["character_card_ids"]))
    scene_id = info.hg_scene_id
    fixture = kernel.store.require(scene_id)
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.opening_description = str(scenario["opening_description"])
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=scene_id,
            content=str(scenario["trigger_text"]),
            hg_round_id=round_id,
        )
    )
    actor = str(scenario["character_card_ids"][0])
    decision = _validate_director(kernel, scene_id, round_id, actor)
    commit = kernel.commit_move(
        CommitRequest(
            inference_id=f"inf-commit-{scenario_id}",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id=actor,
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision=decision,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    manifest = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id=f"inf-narrator-{scenario_id}",
            character_id=actor,
            domain_commit_id=str(commit.domain_commit_id),
            continuity_turn_index=int(commit.continuity_turn_index),
        )
    )
    director = next(c for c in manifest.contributions if c.source_kind == "director_decision")
    committed = next(c for c in manifest.contributions if c.source_kind == "committed_move")
    assert director.authority_class == "derived"
    assert committed.authority_class == "authoritative"
    validation = kernel.validate_narrator_presentation(
        NarratorPresentationValidationRequest(
            hg_scene_id=scene_id,
            domain_commit_id=str(commit.domain_commit_id),
            presentation_text="Alice nodded thoughtfully, taking in the workshop around her.",
        )
    )
    assert validation.accepted is True

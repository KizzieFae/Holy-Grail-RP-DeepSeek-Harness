"""Issue #23 Host/continuity integration contracts."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.modules.continuity_state_public_event import PublicEvent  # noqa: E402
from domain.modules.progression_simulation_scenarios import load_scenario  # noqa: E402
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionValidationRequest,
    NarratorContextPrepareRequest,
    PlayerSkipRecordRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import PROTOTYPE_VALID_MOVE, DomainKernel  # noqa: E402


def _kernel_scene_round() -> tuple[DomainKernel, str, str]:
    kernel = DomainKernel(store=FixtureStore())
    scene_id = kernel.create_scene().hg_scene_id
    round_id = kernel.start_round(
        RoundStartRequest(hg_scene_id=scene_id)
    ).hg_round_id
    return kernel, scene_id, round_id


def _validate(
    kernel: DomainKernel,
    scene_id: str,
    round_id: str,
    decision: dict,
):
    return kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-director-23",
            turn_index=0,
            attempt_index=0,
            proposed_decision=decision,
            raw_model_output=json.dumps(decision),
        )
    )


def test_auxiliary_normalization_accepts_selection_without_retry() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    fixture = kernel.store.require(scene_id)
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.recent_environment_events = ["A chime rings inside."]
    result = _validate(
        kernel,
        scene_id,
        round_id,
        {
            "next_actor": "Alice",
            "end_round": False,
            "reason": "eligible",
            "tension_shift": "unsettle",
            "environment_event": "  A CHIME   rings inside. ",
        },
    )
    assert result.accepted is True
    assert result.retryable is False
    assert result.normalized_decision is not None
    assert result.normalized_decision["tension_shift"] == "steady"
    assert result.normalized_decision["environment_event"] == ""


def test_unique_environment_event_remains_available_for_commit() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    result = _validate(
        kernel,
        scene_id,
        round_id,
        {
            "next_actor": "Alice",
            "end_round": False,
            "reason": "eligible",
            "tension_shift": "escalate",
            "environment_event": "Rain begins against the windows.",
        },
    )
    assert result.accepted is True
    assert result.normalized_decision is not None
    assert result.normalized_decision["environment_event"] == (
        "Rain begins against the windows."
    )


def test_environment_dedup_reads_environment_public_events() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    fixture = kernel.store.require(scene_id)
    fixture.manager.public_events.append(
        PublicEvent(
            event_id="evt-environment-23",
            timestamp=datetime.now(UTC),
            event_type="environment",
            participants=[],
            summary="The hall lights flicker.",
            turn_index=0,
        )
    )
    result = _validate(
        kernel,
        scene_id,
        round_id,
        {
            "next_actor": "Alice",
            "end_round": False,
            "reason": "eligible",
            "tension_shift": "steady",
            "environment_event": "THE HALL LIGHTS FLICKER.",
        },
    )
    assert result.accepted is True
    assert result.normalized_decision is not None
    assert result.normalized_decision["environment_event"] == ""


def test_commit_boundary_defensively_normalizes_auxiliary_fields() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    fixture = kernel.store.require(scene_id)
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.recent_environment_events = ["A chime rings inside."]
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-direct-commit-23",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision={
                "next_actor": "Alice",
                "end_round": False,
                "reason": "direct boundary call",
                "tension_shift": "unsettle",
                "environment_event": " A CHIME rings inside. ",
            },
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    stored = fixture.rounds[-1].character_turns[-1].director_decision
    assert stored["tension_shift"] == "steady"
    assert stored["environment_event"] == ""
    assert fixture.manager.scene_state.recent_environment_events == [
        "A chime rings inside."
    ]


def test_director_gets_unredacted_trigger_and_committed_environment() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    secret = "Whisper to Alice only: OPEN THE RED DOOR"
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=scene_id,
            content=secret,
            speaker="Player",
            hg_round_id=round_id,
        )
    )
    fixture = kernel.store.require(scene_id)
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.recent_environment_events = ["A chime rings inside."]
    manifest = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-context-23",
            turn_index=0,
            attempt_index=0,
        )
    )
    trigger = next(c for c in manifest.contributions if c.source_kind == "user_turn_trigger")
    environment = next(
        c for c in manifest.contributions if c.source_kind == "recent_environment"
    )
    assert trigger.authority_class == "derived"
    assert trigger.provenance["visibility"] == "orchestration_projection"
    assert trigger.provenance["trigger_redacted"] is False
    assert secret in trigger.content
    assert environment.authority_class == "authoritative"
    assert "A chime rings inside." in environment.content


def test_director_trigger_is_skip_aware() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=scene_id,
            content="Open the door.",
            hg_round_id=round_id,
        )
    )
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=scene_id))
    manifest = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-context-skip-23",
            turn_index=0,
            attempt_index=0,
        )
    )
    assert "user_turn_trigger" not in {
        contribution.source_kind for contribution in manifest.contributions
    }


def test_parser_uses_current_eligible_pool() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    fixture = kernel.store.require(scene_id)
    fixture.rounds[-1].actors_used_this_round.append("Alice")
    result = _validate(
        kernel,
        scene_id,
        round_id,
        {
            "next_actor": "Alice",
            "end_round": False,
            "reason": "already used",
            "tension_shift": "steady",
            "environment_event": "",
        },
    )
    assert result.accepted is False
    assert result.validation_class == "domain_rule"
    assert "already_used_this_round" in result.reason


def test_progression_excludes_recent_delta_and_narrator_marks_director_derived() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    fixture = kernel.store.require(scene_id)
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.recent_delta = "legacy raw Director prose"
    before = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-before-23",
            turn_index=0,
            attempt_index=0,
        )
    )
    progression = next(
        c for c in before.contributions if c.source_kind == "scene_progression"
    )
    assert "legacy raw Director prose" not in progression.content
    assert "Recent delta:" not in progression.content

    decision = {
        "next_actor": "Alice",
        "end_round": False,
        "reason": "eligible",
        "tension_shift": "steady",
        "environment_event": "Rain begins against the windows.",
    }
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-23",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision=decision,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    assert fixture.manager.scene_state.recent_delta != decision["environment_event"]
    narrator = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-narrator-23",
            character_id="Alice",
            domain_commit_id=str(commit.domain_commit_id),
            continuity_turn_index=int(commit.continuity_turn_index),
        )
    )
    director = next(
        c for c in narrator.contributions if c.source_kind == "director_decision"
    )
    committed = next(
        c for c in narrator.contributions if c.source_kind == "committed_move"
    )
    assert director.authority_class == "derived"
    assert director.provenance["visibility"] == "orchestration_projection"
    assert committed.authority_class == "authoritative"


@pytest.mark.parametrize(
    ("scenario_id", "proposed_environment", "expected_environment"),
    [
        ("arrival_setup", "Rain begins against the windows.", "Rain begins against the windows."),
        ("strong_user_steer", "  A BELL   RINGS. ", ""),
        ("conflict_3char", "A bell rings.", ""),
    ],
)
def test_scenario_grade_director_hardening(
    scenario_id: str,
    proposed_environment: str,
    expected_environment: str,
) -> None:
    scenario = load_scenario(scenario_id)
    kernel = DomainKernel(store=FixtureStore())
    info = kernel.create_session(cast=list(scenario["character_card_ids"]))
    scene_id = info.hg_scene_id
    fixture = kernel.store.require(scene_id)
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.opening_description = str(
        scenario["opening_description"]
    )
    fixture.manager.scene_state.recent_environment_events = ["A bell rings."]
    round_id = kernel.start_round(
        RoundStartRequest(hg_scene_id=scene_id)
    ).hg_round_id
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=scene_id,
            content=str(scenario["trigger_text"]),
            hg_round_id=round_id,
        )
    )

    manifest = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id=f"inf-{scenario_id}",
            turn_index=0,
            attempt_index=0,
        )
    )
    trigger = next(c for c in manifest.contributions if c.source_kind == "user_turn_trigger")
    assert str(scenario["trigger_text"]) in trigger.content
    assert any(c.source_kind == "recent_environment" for c in manifest.contributions)

    actor = str(scenario["character_card_ids"][0])
    result = _validate(
        kernel,
        scene_id,
        round_id,
        {
            "next_actor": actor,
            "end_round": False,
            "reason": "mechanically eligible",
            "tension_shift": "unsettle",
            "environment_event": proposed_environment,
        },
    )
    assert result.accepted is True
    assert result.selected_character_id == actor
    assert result.normalized_decision is not None
    assert result.normalized_decision["tension_shift"] == "steady"
    assert result.normalized_decision["environment_event"] == expected_environment

    commit = kernel.commit_move(
        CommitRequest(
            inference_id=f"inf-commit-{scenario_id}",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id=actor,
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision=dict(result.normalized_decision),
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    after = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id=f"inf-after-{scenario_id}",
            turn_index=1,
            attempt_index=0,
        )
    )
    progression = next(
        c for c in after.contributions if c.source_kind == "scene_progression"
    )
    assert "Recent delta:" not in progression.content
    if expected_environment:
        assert "[turn 1]" in progression.content
        assert expected_environment in fixture.manager.scene_state.recent_environment_events
    else:
        assert "No committed public events yet." in progression.content
        assert fixture.manager.scene_state.recent_environment_events == ["A bell rings."]

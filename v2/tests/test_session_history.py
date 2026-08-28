"""Durable RP history projection and restart tests."""

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
    PresentationRecordRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
    ValidationRequest,
)
from domain_api.character_conversation_projection import (  # noqa: E402
    project_character_conversation_for_manifest,
)
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.session_history import (  # noqa: E402
    INFERENCE_OUTCOME_EMPTY_OUTPUT,
    INFERENCE_OUTCOME_INFERENCE_ERROR,
    INFERENCE_OUTCOME_OUTPUT_LIMIT,
    INFERENCE_OUTCOME_SUCCEEDED,
    PRESENTATION_SOURCE_COMMITTED_FALLBACK,
    PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC,
    PRESENTATION_SOURCE_NARRATOR,
    append_history_entry,
    presentation_uses_narrator_prose_for_character,
    project_history_to_character_context_chat,
    project_history_to_transcript,
)
from domain_api.session_repository import SessionRepository  # noqa: E402
from perception_audibility_constants import REDACTED_SPEECH_STUB  # noqa: E402


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    return tmp_path / "sessions"


@pytest.fixture
def repository(sessions_dir: Path) -> SessionRepository:
    return SessionRepository(sessions_dir)


@pytest.fixture
def kernel(repository: SessionRepository) -> DomainKernel:
    return DomainKernel.for_repository(repository)


def _speech_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": "nods"},
            {"type": "speech", "dialogue": "for everyone"},
            {
                "type": "speech",
                "dialogue": "for Bob only",
                "audibility": "directed",
                "audience": ["Bob"],
            },
        ],
        "motivation": {
            "goal": "share",
            "tactic": "mixed speech",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }


def _commit_round(
    kernel: DomainKernel,
    hg_scene_id: str,
    hg_round_id: str,
    *,
    move: dict | None = None,
) -> str:
    proposed = move or PROTOTYPE_VALID_MOVE
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-history",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=proposed,
            raw_model_output=json.dumps(proposed),
        )
    )
    assert validation.accepted
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-history",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=validation.normalized_move,
            director_decision=PROTOTYPE_DIRECTOR_DECISION,
            expected_turn_index=0,
        )
    )
    assert commit.committed
    assert commit.domain_commit_id
    return commit.domain_commit_id


def test_user_turn_and_presentation_survive_restart(kernel: DomainKernel, repository: SessionRepository) -> None:
    created = kernel.create_session(cast=["Alice"])
    session_id = created.hg_session_id
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=session_id,
            content="Alice, please respond.",
            speaker="Player",
            forced_designation="Alice",
        )
    )
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id
    commit_id = _commit_round(kernel, session_id, hg_round_id)
    kernel.record_presentation(
        PresentationRecordRequest(
            hg_session_id=session_id,
            domain_commit_id=commit_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            presentation_text="Alice nodded thoughtfully.",
            presentation_failed=False,
            inference_outcome=INFERENCE_OUTCOME_SUCCEEDED,
        )
    )

    repository.clear_cache()
    reopened = repository.open_session(session_id)
    history = kernel.get_session_history(session_id)
    assert len(history.entries) == 3
    assert history.entries[0]["kind"] == "user"
    assert history.entries[1]["kind"] == "committed_turn"
    assert history.entries[2]["kind"] == "presentation"
    presentation = history.entries[2]
    assert presentation["metadata"]["presentation_source"] == PRESENTATION_SOURCE_NARRATOR
    assert presentation["metadata"]["inference_outcome"] == INFERENCE_OUTCOME_SUCCEEDED
    committed = history.entries[1]
    assert "structured_move" in committed["metadata"]
    assert committed["metadata"]["structured_move"]["beats"]
    transcript = project_history_to_transcript(reopened.rp_history)
    assert len(transcript) == 2
    assert transcript[0]["role"] == "user"
    assert transcript[1]["role"] == "assistant"
    assert "nodded" in transcript[1]["content"]


def test_presentation_failure_uses_committed_turn_fallback(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice"])
    session_id = created.hg_session_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id
    commit_id = _commit_round(kernel, session_id, hg_round_id)
    kernel.record_presentation(
        PresentationRecordRequest(
            hg_session_id=session_id,
            domain_commit_id=commit_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            presentation_text=None,
            presentation_failed=True,
            inference_outcome=INFERENCE_OUTCOME_EMPTY_OUTPUT,
        )
    )
    entries = kernel.get_session_history(session_id).entries
    presentation = entries[-1]
    assert presentation["metadata"]["presentation_source"] == PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC
    assert presentation["metadata"]["presentation_degraded"] is True
    assert presentation["metadata"]["inference_outcome"] == INFERENCE_OUTCOME_EMPTY_OUTPUT
    transcript = project_history_to_transcript(entries)
    assert len(transcript) == 1
    assert transcript[0]["presentation_failed"] is True
    assert "nods thoughtfully" in transcript[0]["content"]


def test_failed_presentation_character_context_uses_structured_move_not_fallback_summary(
    kernel: DomainKernel,
) -> None:
    created = kernel.create_session(cast=["Alice", "Bob", "Carol"])
    session_id = created.hg_scene_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id
    commit_id = _commit_round(kernel, session_id, hg_round_id, move=_speech_move())
    kernel.record_presentation(
        PresentationRecordRequest(
            hg_session_id=session_id,
            domain_commit_id=commit_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            presentation_text=None,
            presentation_failed=True,
            inference_outcome=INFERENCE_OUTCOME_EMPTY_OUTPUT,
        )
    )
    fixture = kernel.store.require(session_id)
    transcript_ui = project_history_to_transcript(fixture.rp_history)
    assert "for everyone" in transcript_ui[0]["content"]
    assert transcript_ui[0]["presentation_failed"] is True
    carol_transcript, _, prov = project_character_conversation_for_manifest(
        fixture,
        character_id="Carol",
    )
    assert prov["transcript_message_count"] == 1
    assert "for everyone" in carol_transcript
    assert "for Bob only" not in carol_transcript
    assert REDACTED_SPEECH_STUB in carol_transcript


def test_output_limit_terminal_failure_uses_committed_fallback_for_ui(
    kernel: DomainKernel,
) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    session_id = created.hg_session_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id
    commit_id = _commit_round(kernel, session_id, hg_round_id, move=_speech_move())
    kernel.record_presentation(
        PresentationRecordRequest(
            hg_session_id=session_id,
            domain_commit_id=commit_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            presentation_text=None,
            presentation_failed=True,
            inference_outcome=INFERENCE_OUTCOME_OUTPUT_LIMIT,
        )
    )
    fixture = kernel.store.require(session_id)
    ui = project_history_to_transcript(fixture.rp_history)
    assert "for everyone" in ui[0]["content"]
    assert "nods" in ui[0]["content"]
    assert ui[0]["presentation_failed"] is True
    from domain_api.session_history import history_entries

    presentation_entry = history_entries(fixture.rp_history)[-1]
    assert presentation_entry.presentation_status == "failed"
    assert not presentation_uses_narrator_prose_for_character(presentation_entry)
    bob_transcript, _, _ = project_character_conversation_for_manifest(
        fixture,
        character_id="Bob",
    )
    assert "for Bob only" in bob_transcript


def test_legacy_rendered_without_metadata_uses_narrator_prose(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice"])
    session_id = created.hg_session_id
    fixture = kernel.store.require(session_id)
    append_history_entry(
        fixture.rp_history,
        kind="presentation",
        content="Legacy narrator line.",
        presentation_status="rendered",
        metadata={"renderer": "narrator"},
    )
    chat = project_history_to_character_context_chat(
        fixture.rp_history,
        character_id="Alice",
        character_names=["Alice"],
        present_characters=["Alice"],
        get_character_display_name_fn=lambda x: x,
    )
    assert chat[0]["content"] == "Legacy narrator line."


def test_legacy_failed_without_structured_move_uses_committed_content(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice"])
    session_id = created.hg_session_id
    fixture = kernel.store.require(session_id)
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="nods thoughtfully",
        domain_commit_id="commit-legacy",
        actor_id="Alice",
    )
    append_history_entry(
        fixture.rp_history,
        kind="presentation",
        content="nods thoughtfully",
        domain_commit_id="commit-legacy",
        actor_id="Alice",
        presentation_status="failed",
        metadata={"renderer": "narrator"},
    )
    chat = project_history_to_character_context_chat(
        fixture.rp_history,
        character_id="Alice",
        character_names=["Alice"],
        present_characters=["Alice"],
        get_character_display_name_fn=lambda x: x,
    )
    assert chat[0]["content"] == "Alice: nods thoughtfully"


def test_inference_error_outcome_on_failed_presentation(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice"])
    session_id = created.hg_session_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=session_id)).hg_round_id
    commit_id = _commit_round(kernel, session_id, hg_round_id)
    kernel.record_presentation(
        PresentationRecordRequest(
            hg_session_id=session_id,
            domain_commit_id=commit_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            presentation_text="partial junk",
            presentation_failed=True,
            inference_outcome=INFERENCE_OUTCOME_INFERENCE_ERROR,
        )
    )
    presentation = kernel.get_session_history(session_id).entries[-1]
    assert presentation["metadata"]["inference_outcome"] == INFERENCE_OUTCOME_INFERENCE_ERROR

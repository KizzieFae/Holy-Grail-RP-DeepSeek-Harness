"""Skip Turn (#13) — durable intent, trigger suppression, and round advancement."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    PlayerSkipRecordRequest,
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
    PLAYER_SKIP_CONTENT,
    PLAYER_SKIP_KIND,
    project_history_to_character_context_chat,
    project_history_to_transcript,
    substantive_user_entry_for_trigger,
)
from domain_api.session_repository import SessionRepository  # noqa: E402


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    return tmp_path / "sessions"


@pytest.fixture
def repository(sessions_dir: Path) -> SessionRepository:
    return SessionRepository(sessions_dir)


@pytest.fixture
def kernel(repository: SessionRepository) -> DomainKernel:
    return DomainKernel(repository=repository)


def test_record_player_skip_persists_without_user_entry(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    entry = kernel.record_player_skip(
        PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler")
    )
    assert entry["kind"] == PLAYER_SKIP_KIND
    assert entry["content"] == PLAYER_SKIP_CONTENT
    history = kernel.get_session_history(sid).entries
    assert len(history) == 1
    assert history[0]["kind"] == PLAYER_SKIP_KIND
    assert not any(e.get("kind") == "user" for e in history)


def test_record_player_skip_does_not_write_user_memory(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice"])
    sid = created.hg_session_id
    memory = MagicMock()
    memory.snapshot_character_states.return_value = {}
    memory.write_user_turn_memory = MagicMock()
    kernel._memory_service = lambda: memory  # type: ignore[method-assign]
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    memory.write_user_turn_memory.assert_not_called()


def test_player_skip_survives_reload(kernel: DomainKernel, repository: SessionRepository) -> None:
    created = kernel.create_session(cast=["Alice"])
    sid = created.hg_session_id
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    repository.clear_cache()
    reopened = repository.open_session(sid)
    assert any(e.get("kind") == PLAYER_SKIP_KIND for e in reopened.rp_history)


def test_substantive_user_trigger_suppressed_after_skip(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=sid,
            content="Why is the bat on your shoulder?",
            speaker="Traveler",
        )
    )
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    assert substantive_user_entry_for_trigger(kernel.get_session_history(sid).entries) is None


def test_substantive_user_trigger_restored_after_later_user_turn(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=sid,
            content="First question",
            speaker="Traveler",
        )
    )
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=sid,
            content="Second question",
            speaker="Traveler",
        )
    )
    trigger_entry = substantive_user_entry_for_trigger(kernel.get_session_history(sid).entries)
    assert trigger_entry is not None
    assert trigger_entry["content"] == "Second question"


def test_double_skip_keeps_trigger_suppressed(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=sid,
            content="Old question",
            speaker="Traveler",
        )
    )
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    assert substantive_user_entry_for_trigger(kernel.get_session_history(sid).entries) is None


def test_skip_not_in_character_context_chat(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=sid,
            content="Hello everyone",
            speaker="Traveler",
        )
    )
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    fixture = kernel.store.require(sid)
    chat = project_history_to_character_context_chat(
        fixture.rp_history,
        character_id="Alice",
        character_names=["Alice", "Bob"],
        present_characters=["Alice", "Bob"],
        get_character_display_name_fn=lambda x: x,
    )
    assert len(chat) == 1
    assert chat[0]["content"] == "Hello everyone"
    assert PLAYER_SKIP_CONTENT not in str(chat)


def test_skip_visible_in_ui_transcript(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice"])
    sid = created.hg_session_id
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    transcript = project_history_to_transcript(kernel.get_session_history(sid).entries)
    assert len(transcript) == 1
    assert transcript[0]["player_skip"] is True
    assert transcript[0]["content"] == PLAYER_SKIP_CONTENT


def test_user_turn_trigger_omitted_after_skip(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=sid)).hg_round_id
    old_question = "Why is the bat on your shoulder?"
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=sid,
            content=old_question,
            speaker="Traveler",
            hg_round_id=hg_round_id,
        )
    )
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-skip",
            hg_scene_id=sid,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=PROTOTYPE_VALID_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_VALID_MOVE),
        )
    )
    assert validation.accepted
    kernel.commit_move(
        CommitRequest(
            inference_id="inf-skip",
            hg_scene_id=sid,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=validation.normalized_move,
            director_decision=PROTOTYPE_DIRECTOR_DECISION,
            expected_turn_index=0,
        )
    )
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    rnd2 = kernel.start_round(RoundStartRequest(hg_scene_id=sid)).hg_round_id
    manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=sid,
            hg_round_id=rnd2,
            inference_id="inf-alice-skip",
            character_id="Alice",
            role="guest",
            turn_index=1,
            attempt_index=0,
        )
    )
    kinds = {c.source_kind for c in manifest.contributions}
    assert "recent_scene_transcript" in kinds
    assert "user_turn_trigger" not in kinds
    transcript = next(c for c in manifest.contributions if c.source_kind == "recent_scene_transcript")
    assert old_question in transcript.content


def test_normal_user_turn_still_yields_trigger(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=sid)).hg_round_id
    question = "What do you think?"
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=sid,
            content=question,
            speaker="Traveler",
            hg_round_id=hg_round_id,
        )
    )
    manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=sid,
            hg_round_id=hg_round_id,
            inference_id="inf-alice",
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
        )
    )
    trigger = next(c for c in manifest.contributions if c.source_kind == "user_turn_trigger")
    assert question in trigger.content


def test_character_manifest_without_trigger_when_only_skip(kernel: DomainKernel) -> None:
    created = kernel.create_session(cast=["Alice", "Bob"])
    sid = created.hg_session_id
    kernel.record_player_skip(PlayerSkipRecordRequest(hg_session_id=sid, speaker="Traveler"))
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=sid)).hg_round_id
    fixture = kernel.store.require(sid)
    transcript_content, trigger_content, _ = project_character_conversation_for_manifest(
        fixture,
        character_id="Alice",
    )
    assert trigger_content is None

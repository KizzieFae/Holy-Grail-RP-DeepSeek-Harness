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
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.session_history import project_history_to_transcript  # noqa: E402
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


def _commit_round(kernel: DomainKernel, hg_scene_id: str, hg_round_id: str) -> str:
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-history",
            hg_scene_id=hg_scene_id,
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
        )
    )

    repository.clear_cache()
    reopened = repository.open_session(session_id)
    history = kernel.get_session_history(session_id)
    assert len(history.entries) == 3
    assert history.entries[0]["kind"] == "user"
    assert history.entries[1]["kind"] == "committed_turn"
    assert history.entries[2]["kind"] == "presentation"
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
        )
    )
    transcript = project_history_to_transcript(kernel.get_session_history(session_id).entries)
    assert len(transcript) == 1
    assert transcript[0]["presentation_failed"] is True
    assert transcript[0]["content"]

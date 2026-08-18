"""SessionRepository persistence, restart, idempotency, and failure tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    RoundStartRequest,
    ValidationRequest,
)
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.session_repository import PersistenceError, SessionRepository  # noqa: E402


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    return tmp_path / "sessions"


@pytest.fixture
def repository(sessions_dir: Path) -> SessionRepository:
    return SessionRepository(sessions_dir)


@pytest.fixture
def kernel(repository: SessionRepository) -> DomainKernel:
    return DomainKernel(repository=repository)


def _start_round(kernel: DomainKernel, hg_scene_id: str) -> str:
    response = kernel.start_round(RoundStartRequest(hg_scene_id=hg_scene_id))
    return response.hg_round_id


def test_create_session_persists_and_returns_identity(repository: SessionRepository) -> None:
    session = repository.create_session(cast=["Alice", "Bob"], location="Lab")
    assert session.hg_session_id == session.hg_scene_id
    session_file = repository.sessions_dir / f"{session.hg_session_id}.json"
    assert session_file.exists()
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    assert payload["session_id"] == session.hg_session_id
    assert payload["metadata"]["continuity_state"] is not None


def test_open_session_reconstructs_live_state(repository: SessionRepository) -> None:
    created = repository.create_session(cast=["Alice"])
    repository.clear_cache()
    opened = repository.open_session(created.hg_session_id)
    assert opened.hg_scene_id == created.hg_scene_id
    assert opened.manager.turn_counter == 0
    assert opened.cast == ["Alice"]


def test_commit_survives_repository_restart(kernel: DomainKernel, repository: SessionRepository) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)

    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-restart",
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
    assert validation.accepted is True
    assert validation.normalized_move is not None

    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-restart",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=validation.normalized_move,
            director_decision=PROTOTYPE_DIRECTOR_DECISION,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    assert commit.continuity_turn_index == 1

    session_id = info.hg_session_id
    repository.clear_cache()
    restarted = DomainKernel(repository=SessionRepository(repository.sessions_dir))
    reopened = restarted.open_session(session_id)
    assert reopened.turn_counter == 1
    assert reopened.committed_move_count == 1

    snapshot = restarted.scene_snapshot(hg_scene_id)
    assert snapshot.turn_counter == 1
    assert snapshot.committed_move_count == 1
    assert snapshot.hg_session_id == session_id


def test_commit_idempotent_retry(kernel: DomainKernel, repository: SessionRepository) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-idem",
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
    assert validation.normalized_move is not None
    request = CommitRequest(
        inference_id="inf-idem",
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Alice",
        validated_move=validation.normalized_move,
        director_decision=PROTOTYPE_DIRECTOR_DECISION,
        expected_turn_index=0,
    )
    first = kernel.commit_move(request)
    second = kernel.commit_move(request)
    assert first.committed is True
    assert second.committed is True
    assert first.domain_commit_id == second.domain_commit_id
    assert kernel.scene_snapshot(hg_scene_id).turn_counter == 1


def test_persistence_failure_rolls_back_live_state(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-fail",
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
    assert validation.normalized_move is not None
    before_turn = kernel.scene_snapshot(hg_scene_id).turn_counter

    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(
            CommitRequest(
                inference_id="inf-fail",
                hg_scene_id=hg_scene_id,
                hg_round_id=hg_round_id,
                character_id="Alice",
                validated_move=validation.normalized_move,
                director_decision=PROTOTYPE_DIRECTOR_DECISION,
                expected_turn_index=0,
            )
        )

    assert result.committed is False
    assert kernel.scene_snapshot(hg_scene_id).turn_counter == before_turn

    repository.clear_cache()
    reopened = DomainKernel(repository=SessionRepository(repository.sessions_dir)).open_session(
        info.hg_session_id
    )
    assert reopened.turn_counter == before_turn


def test_commit_dedup_survives_repository_restart(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-restart-idem",
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
    assert validation.normalized_move is not None
    request = CommitRequest(
        inference_id="inf-restart-idem",
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Alice",
        validated_move=validation.normalized_move,
        director_decision=PROTOTYPE_DIRECTOR_DECISION,
        expected_turn_index=0,
    )
    first = kernel.commit_move(request)
    assert first.committed is True
    dedup_key = repository.commit_dedup_key(
        hg_scene_id=hg_scene_id,
        inference_id=request.inference_id,
        expected_turn_index=request.expected_turn_index,
        character_id=request.character_id,
        validated_move=dict(request.validated_move),
        director_decision=dict(request.director_decision),
    )
    session_id = info.hg_session_id
    sessions_dir = repository.sessions_dir
    repository.clear_cache()
    restarted_repo = SessionRepository(sessions_dir)
    session = restarted_repo.open_session(session_id)
    assert dedup_key in session.commit_dedup_index
    record = restarted_repo.get_commit_dedup(dedup_key)
    assert record is not None
    assert record.domain_commit_id == first.domain_commit_id


def test_health_endpoint_via_kernel_store(repository: SessionRepository) -> None:
    assert repository.health_ok() is True


def test_http_health_and_session_lifecycle(sessions_dir: Path) -> None:
    import threading
    from http.server import ThreadingHTTPServer

    from domain_api.http_transport import DomainApiHandler
    from domain_api.kernel import DomainKernel

    kernel = DomainKernel(repository=SessionRepository(sessions_dir))
    handler = type("H", (DomainApiHandler,), {"kernel": kernel})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health") as resp:
            health = json.loads(resp.read().decode("utf-8"))
        assert health["status"] == "ok"

        create_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/sessions/create",
            data=json.dumps({"cast": ["Alice"], "location": "Lab"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(create_req) as resp:
            created = json.loads(resp.read().decode("utf-8"))
        session_id = created["hg_session_id"]
        assert created["hg_scene_id"] == session_id

        open_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/sessions/open",
            data=json.dumps({"hg_session_id": session_id}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(open_req) as resp:
            opened = json.loads(resp.read().decode("utf-8"))
        assert opened["hg_session_id"] == session_id
        assert opened["turn_counter"] == 0
    finally:
        server.shutdown()
        server.server_close()

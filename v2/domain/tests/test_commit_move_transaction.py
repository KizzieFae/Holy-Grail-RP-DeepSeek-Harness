"""Focused C3-F commit transaction seam tests (#55)."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_mutation_pipeline import ContinuityMutationError  # noqa: E402
from domain.tests.test_storyteller_packaging_s3b import _package  # noqa: E402
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
from domain_api.commit_move_transaction import CommitTransactionDeps, execute_commit_move  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_state import RoundFixture  # noqa: E402
from domain_api.storyteller_contract import advisory_package_to_dict  # noqa: E402


@pytest.fixture
def repository(tmp_path: Path) -> SessionRepository:
    return SessionRepository(tmp_path / "sessions")


@pytest.fixture
def kernel(repository: SessionRepository) -> DomainKernel:
    return DomainKernel.for_repository(repository)


def _start_round(kernel: DomainKernel, hg_scene_id: str) -> str:
    return kernel.start_round(RoundStartRequest(hg_scene_id=hg_scene_id)).hg_round_id


def _validated_commit_request(
    kernel: DomainKernel,
    *,
    hg_scene_id: str,
    hg_round_id: str,
    inference_id: str = "inf-c3",
    expected_turn_index: int = 0,
) -> CommitRequest:
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id=inference_id,
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=expected_turn_index,
            attempt_index=0,
            proposed_move=PROTOTYPE_VALID_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_VALID_MOVE),
        )
    )
    assert validation.accepted is True
    assert validation.normalized_move is not None
    return CommitRequest(
        inference_id=inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Alice",
        validated_move=validation.normalized_move,
        director_decision=PROTOTYPE_DIRECTOR_DECISION,
        expected_turn_index=expected_turn_index,
    )


def _bound_storyteller_package(*, hg_scene_id: str, hg_round_id: str):
    package = _package()
    invalidation_keys = tuple(
        replace(key, key_value=hg_round_id)
        if key.key_kind == "hg_round_id"
        else key
        for key in package.validity.invalidation_keys
    )
    validity = replace(
        package.validity,
        bound_hg_round_id=hg_round_id,
        invalidation_keys=invalidation_keys,
    )
    return advisory_package_to_dict(
        replace(
            package,
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            validity=validity,
        )
    )


def test_dedup_hit_returns_cached_response_without_mutation(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    first = kernel.commit_move(request)
    assert first.committed is True
    before_turn = kernel.scene_snapshot(hg_scene_id).turn_counter
    second = kernel.commit_move(request)
    assert second.committed is True
    assert second.domain_commit_id == first.domain_commit_id
    assert kernel.scene_snapshot(hg_scene_id).turn_counter == before_turn


def test_anchor_mismatch_does_not_mutate(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    request = replace(request, expected_turn_index=99)
    before = kernel.scene_snapshot(hg_scene_id)
    result = kernel.commit_move(request)
    assert result.committed is False
    assert "anchor mismatch" in (result.reason or "")
    after = kernel.scene_snapshot(hg_scene_id)
    assert after.turn_counter == before.turn_counter
    assert after.committed_move_count == before.committed_move_count


def test_legality_failure_preserves_existing_behavior(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    fixture = kernel.store.require(hg_scene_id)
    before_turn = fixture.manager.turn_counter
    with patch.object(
        fixture.manager,
        "process_turn",
        side_effect=ContinuityMutationError("illegal turn"),
    ):
        with pytest.raises(ContinuityMutationError, match="illegal turn"):
            kernel.commit_move(request)
    assert fixture.manager.turn_counter == before_turn


def test_successful_commit_mutates_authoritative_state(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    result = kernel.commit_move(request)
    assert result.committed is True
    assert result.continuity_turn_index == 1
    snapshot = kernel.scene_snapshot(hg_scene_id)
    assert snapshot.turn_counter == 1
    assert snapshot.committed_move_count == 1


def test_domain_commit_id_propagates_to_all_consumers(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    result = kernel.commit_move(request)
    assert result.committed is True
    commit_id = result.domain_commit_id
    assert commit_id is not None

    fixture = repository.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    assert rnd.domain_commit_id == commit_id
    assert fixture.commit_ids[-1] == commit_id
    assert rnd.character_turns[-1].domain_commit_id == commit_id
    history = [entry for entry in fixture.rp_history if entry.get("kind") == "committed_turn"]
    assert history
    assert history[-1]["domain_commit_id"] == commit_id


def test_character_memory_written_before_persist(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    fixture = repository.require(hg_scene_id)
    before_memory = repository.memory_service.snapshot_character_states(fixture)
    result = kernel.commit_move(request)
    assert result.committed is True
    after_memory = repository.memory_service.snapshot_character_states(fixture)
    assert after_memory != before_memory


def test_round_bookkeeping_updated_on_success(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    fixture = kernel.store.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    before_epoch = rnd.eligibility_epoch
    result = kernel.commit_move(request)
    assert result.committed is True
    assert rnd.committed_character_id == "Alice"
    assert rnd.committed_move is not None
    assert rnd.continuity_turn_index == result.continuity_turn_index
    assert "Alice" in rnd.actors_used_this_round
    assert rnd.eligibility_epoch == before_epoch + 1


def test_committed_turn_history_in_persisted_payload(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    result = kernel.commit_move(request)
    assert result.committed is True
    session_file = repository.sessions_dir / f"{info.hg_session_id}.json"
    payload = json.loads(session_file.read_text(encoding="utf-8"))
    history = payload["metadata"]["v2_host_state"]["rp_history"]
    committed = [entry for entry in history if entry.get("kind") == "committed_turn"]
    assert committed
    assert committed[-1]["domain_commit_id"] == result.domain_commit_id


def test_persistence_failure_restores_continuity_state(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-fail-cont"
    )
    before_turn = kernel.scene_snapshot(hg_scene_id).turn_counter
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(request)
    assert result.committed is False
    assert kernel.scene_snapshot(hg_scene_id).turn_counter == before_turn


def test_persistence_failure_restores_character_memory(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-fail-mem"
    )
    fixture = repository.require(hg_scene_id)
    before_memory = repository.memory_service.snapshot_character_states(fixture)
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(request)
    assert result.committed is False
    after_memory = repository.memory_service.snapshot_character_states(fixture)
    assert after_memory == before_memory


def test_persistence_failure_restores_round_bookkeeping(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-fail-round"
    )
    fixture = repository.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    before = {
        "domain_commit_id": rnd.domain_commit_id,
        "character_turns": list(rnd.character_turns),
        "eligibility_epoch": rnd.eligibility_epoch,
    }
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(request)
    assert result.committed is False
    assert rnd.domain_commit_id == before["domain_commit_id"]
    assert rnd.character_turns == before["character_turns"]
    assert rnd.eligibility_epoch == before["eligibility_epoch"]


def test_persistence_failure_restores_dedup_state(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-fail-dedup"
    )
    dedup_key = repository.commit_dedup_key(
        hg_scene_id=hg_scene_id,
        inference_id=request.inference_id,
        expected_turn_index=request.expected_turn_index,
        character_id=request.character_id,
        validated_move=dict(request.validated_move),
        director_decision=dict(request.director_decision),
    )
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(request)
    assert result.committed is False
    assert dedup_key not in repository._commit_dedup
    assert dedup_key not in repository.require(hg_scene_id).commit_dedup_index


def test_persistence_failure_restores_rp_history(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-fail-hist"
    )
    fixture = repository.require(hg_scene_id)
    before_history = list(fixture.rp_history)
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(request)
    assert result.committed is False
    assert fixture.rp_history == before_history


def test_persistence_failure_leaves_storyteller_unchanged(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    kernel.bind_storyteller_advisory_package(
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        package=_bound_storyteller_package(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id),
    )
    before = kernel.get_storyteller_round_state(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    assert before["is_valid"] is True
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-fail-st"
    )
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(request)
    assert result.committed is False
    after = kernel.get_storyteller_round_state(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    assert after["is_valid"] is True
    assert after["invalidation_reason"] is None


def test_storyteller_invalidates_only_after_successful_persistence(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    kernel.bind_storyteller_advisory_package(
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        package=_bound_storyteller_package(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id),
    )
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-st-success"
    )
    call_order: list[str] = []
    original_persist = repository.persist
    from domain_api.storyteller_round_packaging import (
        invalidate_storyteller_package_for_round as real_invalidate,
    )

    def tracking_persist(session):  # type: ignore[no-untyped-def]
        call_order.append("persist")
        return original_persist(session)

    def tracking_invalidate(rnd, *, reason: str):  # type: ignore[no-untyped-def]
        call_order.append("invalidate")
        return real_invalidate(rnd, reason=reason)

    with patch.object(repository, "persist", side_effect=tracking_persist), patch(
        "domain_api.commit_move_transaction.invalidate_storyteller_package_for_round",
        side_effect=tracking_invalidate,
    ):
        result = kernel.commit_move(request)
    assert result.committed is True
    assert call_order.index("persist") < call_order.index("invalidate")
    after = kernel.get_storyteller_round_state(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    assert after["is_valid"] is False
    assert after["invalidation_reason"] == "authoritative_commit"


def test_retry_after_failed_persistence_produces_one_history_lineage(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-retry"
    )
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        failed = kernel.commit_move(request)
    assert failed.committed is False
    success = kernel.commit_move(request)
    assert success.committed is True
    fixture = repository.require(hg_scene_id)
    committed = [entry for entry in fixture.rp_history if entry.get("kind") == "committed_turn"]
    assert len(committed) == 1
    assert committed[0]["domain_commit_id"] == success.domain_commit_id


def test_knowledge_promotion_occurs_only_after_durability(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-k2-order"
    )
    promote = MagicMock(return_value=0)
    repository.knowledge_service.promote_after_commit = promote  # type: ignore[method-assign]
    original_persist = repository.persist
    seen: list[str] = []

    def tracking_persist(session):  # type: ignore[no-untyped-def]
        seen.append("persist")
        return original_persist(session)

    with patch.object(repository, "persist", side_effect=tracking_persist):
        result = kernel.commit_move(request)
    assert result.committed is True
    assert seen == ["persist"]
    promote.assert_called_once()
    assert promote.call_args.kwargs["source_domain_commit_id"] == result.domain_commit_id


def test_knowledge_promotion_failure_remains_warn_only(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-k2-warn"
    )
    with patch.object(
        repository.scope_knowledge_repo,
        "append_records",
        side_effect=OSError("promotion failed"),
    ):
        result = kernel.commit_move(request)
    assert result.committed is True
    assert kernel.scene_snapshot(hg_scene_id).turn_counter == 1


def test_stable_commit_response_shapes(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    success = kernel.commit_move(request)
    assert success.committed is True
    assert success.continuity_turn_index is not None
    assert success.domain_commit_id is not None
    assert success.hg_scene_id == hg_scene_id
    assert success.inference_id == request.inference_id

    mismatch = kernel.commit_move(replace(request, expected_turn_index=99))
    assert mismatch.committed is False
    assert mismatch.continuity_turn_index is None
    assert mismatch.domain_commit_id is None


def test_kernel_facade_delegates_to_transaction(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    from domain_api.contract import CommitResponse

    expected = CommitResponse(
        committed=True,
        continuity_turn_index=1,
        domain_commit_id="hg-commit-delegated",
        hg_scene_id=hg_scene_id,
        inference_id=request.inference_id,
    )
    with patch(
        "domain_api.kernel.execute_commit_move",
        return_value=expected,
    ) as execute_mock:
        response = kernel.commit_move(request)
    execute_mock.assert_called_once()
    assert response.domain_commit_id == "hg-commit-delegated"


def test_restart_durability_remains_correct(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-restart-c3"
    )
    result = kernel.commit_move(request)
    assert result.committed is True
    sessions_dir = repository.sessions_dir
    repository.clear_cache()
    restarted = DomainKernel.for_repository(SessionRepository(sessions_dir))
    reopened = restarted.store.open_session(info.hg_session_id)
    assert reopened.manager.turn_counter == 1
    assert reopened.committed_move_count == 1
    history = [entry for entry in reopened.rp_history if entry.get("kind") == "committed_turn"]
    assert len(history) == 1


def test_successful_commit_persists_exactly_once(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-single-persist"
    )
    with patch.object(repository, "persist", wraps=repository.persist) as persist_mock:
        result = kernel.commit_move(request)
    assert result.committed is True
    assert persist_mock.call_count == 1


def test_dedup_present_before_sole_persist(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-dedup-payload"
    )
    dedup_key = repository.commit_dedup_key(
        hg_scene_id=hg_scene_id,
        inference_id=request.inference_id,
        expected_turn_index=request.expected_turn_index,
        character_id=request.character_id,
        validated_move=dict(request.validated_move),
        director_decision=dict(request.director_decision),
    )
    seen: list[bool] = []
    original_persist = repository.persist

    def tracking_persist(session):  # type: ignore[no-untyped-def]
        seen.append(dedup_key in session.commit_dedup_index)
        return original_persist(session)

    with patch.object(repository, "persist", side_effect=tracking_persist):
        result = kernel.commit_move(request)
    assert result.committed is True
    assert seen == [True]


def test_persist_failure_does_not_invoke_knowledge_promotion(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-no-k2-fail"
    )
    promote = MagicMock(return_value=0)
    repository.knowledge_service.promote_after_commit = promote  # type: ignore[method-assign]
    with patch.object(repository._session_manager, "save_session", side_effect=OSError("disk full")):
        result = kernel.commit_move(request)
    assert result.committed is False
    promote.assert_not_called()


def test_restart_replay_returns_cached_response_without_duplicate_mutation(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-restart-replay"
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
    sessions_dir = repository.sessions_dir
    session_id = info.hg_session_id
    repository.clear_cache()
    restarted_repo = SessionRepository(sessions_dir)
    reopened = restarted_repo.open_session(session_id)
    record = restarted_repo.get_commit_dedup(dedup_key)
    assert record is not None
    assert record.domain_commit_id == first.domain_commit_id
    assert record.response.continuity_turn_index == first.continuity_turn_index

    reopened.rounds.append(
        RoundFixture(hg_round_id=hg_round_id, hg_scene_id=hg_scene_id, turn_index=0)
    )
    rnd = reopened.rounds[-1]
    before_turn = reopened.manager.turn_counter
    before_history = len(reopened.rp_history)
    deps = CommitTransactionDeps(
        repository=restarted_repo,
        memory_service=restarted_repo.memory_service,
        knowledge_service=restarted_repo.knowledge_service,
    )
    replay = execute_commit_move(request, fixture=reopened, rnd=rnd, deps=deps)
    assert replay.committed is True
    assert replay.domain_commit_id == first.domain_commit_id
    assert replay.continuity_turn_index == first.continuity_turn_index
    assert reopened.manager.turn_counter == before_turn
    assert len(reopened.rp_history) == before_history


def test_dedup_hit_wins_over_stale_expected_turn_index(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-dedup-anchor"
    )
    first = kernel.commit_move(request)
    assert first.committed is True
    stale = replace(request, expected_turn_index=0)
    replay = kernel.commit_move(stale)
    assert replay.committed is True
    assert replay.domain_commit_id == first.domain_commit_id
    assert kernel.scene_snapshot(hg_scene_id).turn_counter == 1


def test_storyteller_invalidation_reason_parity_immediate_and_replay(
    kernel: DomainKernel, repository: SessionRepository
) -> None:
    info = kernel.create_session(cast=["Alice"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = _start_round(kernel, hg_scene_id)
    kernel.bind_storyteller_advisory_package(
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        package=_bound_storyteller_package(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id),
    )
    request = _validated_commit_request(
        kernel, hg_scene_id=hg_scene_id, hg_round_id=hg_round_id, inference_id="inf-st-reason"
    )
    first = kernel.commit_move(request)
    assert first.committed is True
    assert first.storyteller_invalidation_reason == "authoritative_commit"
    same_process = kernel.commit_move(request)
    assert same_process.storyteller_invalidation_reason == first.storyteller_invalidation_reason

    dedup_key = repository.commit_dedup_key(
        hg_scene_id=hg_scene_id,
        inference_id=request.inference_id,
        expected_turn_index=request.expected_turn_index,
        character_id=request.character_id,
        validated_move=dict(request.validated_move),
        director_decision=dict(request.director_decision),
    )
    sessions_dir = repository.sessions_dir
    repository.clear_cache()
    restarted_repo = SessionRepository(sessions_dir)
    restarted_repo.open_session(info.hg_session_id)
    record = restarted_repo.get_commit_dedup(dedup_key)
    assert record is not None
    assert record.response.storyteller_invalidation_reason == "authoritative_commit"

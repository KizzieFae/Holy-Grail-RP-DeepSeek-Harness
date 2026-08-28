"""Authoritative commit transaction orchestration (#55 C3-F)."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any

from .commit_input_normalization import prepare_commit_move_inputs
from .contract import CommitRequest, CommitResponse
from .fixture_store import FixtureStore
from .knowledge_service import KnowledgeService
from .memory_service import MemoryService
from .memory_write_policy import (
    apply_character_turn_memory,
    restore_character_states,
    snapshot_character_states,
)
from .session_history import append_history_entry, summarize_committed_move
from .session_repository import CommitDedupRecord, PersistenceError, SessionRepository
from .session_state import CharacterTurnRecord, LiveSession, RoundFixture
from .storyteller_round_packaging import invalidate_storyteller_package_for_round


@dataclass(frozen=True)
class CommitTransactionDeps:
    """Bounded concrete collaborators for a single commit transaction."""

    repository: SessionRepository | FixtureStore
    memory_service: MemoryService | None
    knowledge_service: KnowledgeService | None


@dataclass
class _RollbackSnapshots:
    manager: dict[str, Any] | None
    round_state: dict[str, Any] | None
    host: dict[str, Any] | None
    character_memory: Any
    rp_history: list[dict[str, Any]]
    dedup_key: str | None


def _capture_round_snapshot(rnd: RoundFixture) -> dict[str, Any]:
    return {
        "director_decision": rnd.director_decision,
        "committed_character_id": rnd.committed_character_id,
        "committed_move": copy.deepcopy(rnd.committed_move)
        if rnd.committed_move is not None
        else None,
        "domain_commit_id": rnd.domain_commit_id,
        "continuity_turn_index": rnd.continuity_turn_index,
        "actors_used_this_round": list(rnd.actors_used_this_round),
        "character_turns": copy.deepcopy(rnd.character_turns),
        "spotlight_history": list(rnd.spotlight_history),
        "eligibility_epoch": rnd.eligibility_epoch,
    }


def _restore_round_snapshot(rnd: RoundFixture, snapshot: dict[str, Any]) -> None:
    rnd.director_decision = snapshot["director_decision"]
    rnd.committed_character_id = snapshot["committed_character_id"]
    rnd.committed_move = snapshot["committed_move"]
    rnd.domain_commit_id = snapshot["domain_commit_id"]
    rnd.continuity_turn_index = snapshot["continuity_turn_index"]
    rnd.actors_used_this_round = snapshot["actors_used_this_round"]
    rnd.character_turns = snapshot["character_turns"]
    rnd.spotlight_history = snapshot["spotlight_history"]
    rnd.eligibility_epoch = snapshot["eligibility_epoch"]


def _capture_snapshots(
    fixture: LiveSession,
    rnd: RoundFixture,
    deps: CommitTransactionDeps,
    *,
    dedup_key: str | None,
) -> _RollbackSnapshots:
    repository = deps.repository
    char_snapshot = (
        deps.memory_service.snapshot_character_states(fixture)
        if deps.memory_service is not None
        else snapshot_character_states(fixture)
    )
    manager_snapshot: dict[str, Any] | None = None
    round_snapshot: dict[str, Any] | None = None
    host_snapshot: dict[str, Any] | None = None
    if isinstance(repository, SessionRepository):
        manager_snapshot = repository.snapshot_manager(fixture)
        round_snapshot = _capture_round_snapshot(rnd)
        host_snapshot = {
            "committed_move_count": fixture.committed_move_count,
            "commit_ids": list(fixture.commit_ids),
        }
    return _RollbackSnapshots(
        manager=manager_snapshot,
        round_state=round_snapshot,
        host=host_snapshot,
        character_memory=char_snapshot,
        rp_history=list(fixture.rp_history),
        dedup_key=dedup_key,
    )


def _rollback_transaction(
    fixture: LiveSession,
    rnd: RoundFixture,
    deps: CommitTransactionDeps,
    snapshots: _RollbackSnapshots,
) -> None:
    repository = deps.repository
    if not isinstance(repository, SessionRepository) or snapshots.manager is None:
        return
    repository.restore_manager(fixture, snapshots.manager)
    if deps.memory_service is not None:
        deps.memory_service.restore_character_states(fixture, snapshots.character_memory)
    else:
        restore_character_states(fixture, snapshots.character_memory)
    if snapshots.round_state is not None:
        _restore_round_snapshot(rnd, snapshots.round_state)
    if snapshots.host is not None:
        fixture.committed_move_count = snapshots.host["committed_move_count"]
        fixture.commit_ids = snapshots.host["commit_ids"]
    fixture.rp_history[:] = snapshots.rp_history
    if snapshots.dedup_key is not None:
        fixture.commit_dedup_index.pop(snapshots.dedup_key, None)
        repository._commit_dedup.pop(snapshots.dedup_key, None)


def _write_character_memory(
    fixture: LiveSession,
    deps: CommitTransactionDeps,
    *,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
) -> None:
    if deps.memory_service is not None:
        deps.memory_service.write_character_turn_memory(
            fixture,
            acting_character=acting_character,
            move=move,
            director_decision=director_decision,
        )
    else:
        apply_character_turn_memory(
            fixture,
            acting_character=acting_character,
            move=move,
            director_decision=director_decision,
        )


def execute_commit_move(
    req: CommitRequest,
    *,
    fixture: LiveSession,
    rnd: RoundFixture,
    deps: CommitTransactionDeps,
) -> CommitResponse:
    """Run the authoritative commit transaction (C3-F semantic phases)."""
    mgr = fixture.manager
    repository = deps.repository

    # Phase A — pre-transaction guards
    dedup_key: str | None = None
    if isinstance(repository, SessionRepository):
        dedup_key = repository.commit_dedup_key(
            hg_scene_id=req.hg_scene_id,
            inference_id=req.inference_id,
            expected_turn_index=req.expected_turn_index,
            character_id=req.character_id,
            validated_move=dict(req.validated_move),
            director_decision=dict(req.director_decision),
        )
        existing = repository.get_commit_dedup(dedup_key)
        if existing is not None:
            return existing.response

    if mgr.turn_counter != req.expected_turn_index:
        return CommitResponse(
            committed=False,
            continuity_turn_index=None,
            domain_commit_id=None,
            hg_scene_id=req.hg_scene_id,
            inference_id=req.inference_id,
            reason=(
                f"continuity anchor mismatch: expected {req.expected_turn_index}, "
                f"actual {mgr.turn_counter}"
            ),
        )

    # Phase B — preparation
    move, director_decision = prepare_commit_move_inputs(
        fixture,
        validated_move=dict(req.validated_move),
        director_decision=dict(req.director_decision),
    )
    snapshots = _capture_snapshots(fixture, rnd, deps, dedup_key=dedup_key)

    others = [c for c in fixture.cast if c != req.character_id]

    # Phase C — authoritative continuity mutation
    mgr.process_turn(
        acting_character=req.character_id,
        move=move,
        director_decision=director_decision,
        other_characters=others,
        rp_history=list(fixture.rp_history),
    )

    # Phase D — transactionally coupled state
    _write_character_memory(
        fixture,
        deps,
        acting_character=req.character_id,
        move=move,
        director_decision=director_decision,
    )
    after_turn = mgr.turn_counter
    commit_id = f"hg-commit-{uuid.uuid4()}"
    fixture.committed_move_count += 1
    fixture.commit_ids.append(commit_id)
    rnd.director_decision = director_decision
    rnd.committed_character_id = req.character_id
    rnd.committed_move = dict(req.validated_move)
    rnd.domain_commit_id = commit_id
    rnd.continuity_turn_index = after_turn
    rnd.actors_used_this_round.append(req.character_id)
    rnd.character_turns.append(
        CharacterTurnRecord(
            character_id=req.character_id,
            committed_move=dict(req.validated_move),
            domain_commit_id=commit_id,
            continuity_turn_index=after_turn,
            director_decision=director_decision,
        )
    )
    rnd.spotlight_history.append(req.character_id)
    rnd.eligibility_epoch += 1

    if isinstance(repository, SessionRepository):
        append_history_entry(
            fixture.rp_history,
            kind="committed_turn",
            content=summarize_committed_move(dict(req.validated_move)),
            hg_round_id=req.hg_round_id,
            domain_commit_id=commit_id,
            actor_id=req.character_id,
            metadata={
                "continuity_turn_index": after_turn,
                "structured_move": dict(req.validated_move),
            },
        )

    # Phase E — durability (H1: history already appended)
    if hasattr(repository, "persist"):
        try:
            repository.persist(fixture)
        except PersistenceError as exc:
            _rollback_transaction(fixture, rnd, deps, snapshots)
            return CommitResponse(
                committed=False,
                continuity_turn_index=None,
                domain_commit_id=None,
                hg_scene_id=req.hg_scene_id,
                inference_id=req.inference_id,
                reason=str(exc),
            )

    # Phase F — post-durable effects (S2, K2)
    storyteller_invalidation_reason = invalidate_storyteller_package_for_round(
        rnd,
        reason="authoritative_commit",
    )
    if deps.knowledge_service is not None:
        deps.knowledge_service.promote_after_commit(
            fixture,
            source_domain_commit_id=commit_id,
        )

    response = CommitResponse(
        committed=True,
        continuity_turn_index=after_turn,
        domain_commit_id=commit_id,
        hg_scene_id=req.hg_scene_id,
        inference_id=req.inference_id,
        storyteller_invalidation_reason=storyteller_invalidation_reason,
    )

    if isinstance(repository, SessionRepository) and dedup_key is not None:
        repository.record_commit_dedup(
            dedup_key,
            CommitDedupRecord(
                domain_commit_id=commit_id,
                continuity_turn_index=after_turn,
                response=response,
            ),
            fixture,
        )
        try:
            repository.persist(fixture)
        except PersistenceError:
            # Authoritative commit already durable; dedup remains in-process until next persist.
            pass

    return response

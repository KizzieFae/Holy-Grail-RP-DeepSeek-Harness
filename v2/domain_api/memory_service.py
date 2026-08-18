"""Domain Host memory orchestration: session-local writes + cross-scope projection."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from .cross_scope_memory_repository import (
    CROSS_SCOPE_USER_RELATIONSHIP,
    CrossScopeMemoryRecord,
    CrossScopeMemoryRepository,
)
from .memory_retrieval import build_session_memory_projection
from .memory_write_policy import (
    apply_character_turn_memory,
    apply_user_turn_memory,
    restore_character_states,
    snapshot_character_states,
)
from .memory_scope import new_memory_scope_id, resolve_memory_scope_id
from .session_state import LiveSession

_logger = logging.getLogger(__name__)


def _relationship_history_snapshot(fixture: LiveSession, user_name: str) -> dict[str, list[str]]:
    snapshot: dict[str, list[str]] = {}
    for char_name, state in fixture.character_states.items():
        rel = state.relationships.get(user_name, {})
        history = rel.get("history", []) if isinstance(rel, dict) else []
        snapshot[char_name] = [str(item) for item in history]
    return snapshot


class MemoryService:
    """Backend-independent memory policy orchestration for the Domain Host."""

    def __init__(self, cross_scope_repo: CrossScopeMemoryRepository | None = None) -> None:
        self._cross_scope = cross_scope_repo

    @property
    def cross_scope_repo(self) -> CrossScopeMemoryRepository | None:
        return self._cross_scope

    def snapshot_character_states(self, fixture: LiveSession) -> dict[str, Any]:
        return snapshot_character_states(fixture)

    def restore_character_states(self, fixture: LiveSession, snapshot: dict[str, Any]) -> None:
        restore_character_states(fixture, snapshot)

    def write_character_turn_memory(
        self,
        fixture: LiveSession,
        *,
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
    ) -> None:
        apply_character_turn_memory(
            fixture,
            acting_character=acting_character,
            move=move,
            director_decision=director_decision,
        )

    def relationship_history_snapshot(
        self, fixture: LiveSession, user_name: str
    ) -> dict[str, list[str]]:
        return _relationship_history_snapshot(fixture, user_name)

    def write_user_turn_memory(
        self,
        fixture: LiveSession,
        *,
        user_name: str,
        content: str,
    ) -> None:
        apply_user_turn_memory(fixture, user_name=user_name, content=content)

    def build_user_relationship_projection(
        self,
        fixture: LiveSession,
        *,
        user_name: str,
        history_before: dict[str, list[str]],
        source_hg_round_id: str | None = None,
        source_domain_commit_id: str | None = None,
    ) -> list[CrossScopeMemoryRecord]:
        return self._build_user_relationship_records(
            fixture,
            user_name=user_name,
            history_before=history_before,
            source_hg_round_id=source_hg_round_id,
            source_domain_commit_id=source_domain_commit_id,
        )

    def _build_user_relationship_records(
        self,
        fixture: LiveSession,
        *,
        user_name: str,
        history_before: dict[str, list[str]],
        source_hg_round_id: str | None = None,
        source_domain_commit_id: str | None = None,
    ) -> list[CrossScopeMemoryRecord]:
        if self._cross_scope is None or not fixture.memory_scope_id:
            return []

        projected: list[CrossScopeMemoryRecord] = []
        for char_name, state in fixture.character_states.items():
            file_id = fixture.character_file_ids.get(char_name)
            if not file_id:
                continue
            rel = state.relationships.get(user_name, {})
            if not isinstance(rel, dict):
                continue
            history = [str(item) for item in rel.get("history", []) if str(item).strip()]
            prior = history_before.get(char_name, [])
            new_lines = history[len(prior) :]
            for line in new_lines:
                memory_id = CrossScopeMemoryRepository.make_memory_id(
                    memory_scope_id=fixture.memory_scope_id,
                    subject_character_file_id=file_id,
                    memory_kind=CROSS_SCOPE_USER_RELATIONSHIP,
                    source_session_id=fixture.hg_session_id,
                    content=line,
                    user_persona_id=user_name,
                )
                projected.append(
                    CrossScopeMemoryRecord(
                        memory_id=memory_id,
                        memory_scope_id=fixture.memory_scope_id,
                        subject_character_file_id=file_id,
                        subject_display_name=char_name,
                        memory_kind=CROSS_SCOPE_USER_RELATIONSHIP,
                        content=line,
                        source_session_id=fixture.hg_session_id,
                        source_domain_commit_id=source_domain_commit_id,
                        source_hg_round_id=source_hg_round_id,
                        user_persona_id=user_name,
                        created_at=CrossScopeMemoryRepository.now_iso(),
                        provenance={
                            "projection": "user_relationship_history",
                            "perception_filtered": True,
                        },
                    )
                )
        return projected

    def project_cross_scope_after_persist(
        self,
        fixture: LiveSession,
        records: list[CrossScopeMemoryRecord],
    ) -> None:
        """Best-effort cross-scope persistence after authoritative session commit."""
        if not records or self._cross_scope is None:
            return
        try:
            self._cross_scope.append_records(records)
        except OSError as exc:
            _logger.warning(
                "cross-scope memory projection failed for session %s: %s",
                fixture.hg_session_id,
                exc,
            )

    def retrieve_session_memory(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> tuple[str, dict[str, Any]] | None:
        state = fixture.character_states.get(character_id)
        return build_session_memory_projection(state)

    def retrieve_cross_scope_memory(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> tuple[str, dict[str, Any]] | None:
        if self._cross_scope is None or not fixture.memory_scope_id:
            return None
        file_id = fixture.character_file_ids.get(character_id)
        if not file_id:
            return None
        records = self._cross_scope.list_records(
            fixture.memory_scope_id,
            subject_character_file_id=file_id,
            memory_kinds={CROSS_SCOPE_USER_RELATIONSHIP},
        )
        records = [
            record
            for record in records
            if record.source_session_id != fixture.hg_session_id
        ]
        if not records:
            return None
        lines = [f"  • {record.content}" for record in records]
        content = "Cross-session user relationship memory:\n" + "\n".join(lines)
        provenance = {
            "memory_lane": "cross_scope_relationship",
            "memory_scope_id": fixture.memory_scope_id,
            "subject_character_file_id": file_id,
            "memory_ids": [record.memory_id for record in records],
            "source_session_ids": list(
                dict.fromkeys(record.source_session_id for record in records)
            ),
        }
        return content, provenance

    def retrieve_memory_contributions(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> list[tuple[str, dict[str, Any]]]:
        contributions: list[tuple[str, dict[str, Any]]] = []
        session_local = self.retrieve_session_memory(fixture, character_id=character_id)
        if session_local is not None:
            contributions.append(session_local)
        cross_scope = self.retrieve_cross_scope_memory(fixture, character_id=character_id)
        if cross_scope is not None:
            contributions.append(cross_scope)
        return contributions

    def list_memory_scopes(self) -> list[dict[str, str]]:
        if self._cross_scope is None:
            return []
        return [{"memory_scope_id": scope_id} for scope_id in self._cross_scope.list_scope_ids()]

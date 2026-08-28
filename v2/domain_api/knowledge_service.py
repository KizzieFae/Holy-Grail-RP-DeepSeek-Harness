"""Domain Host knowledge orchestration: authored (M11.1) + scope lanes (M11.2) + retrieval index (M12.7)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .authored_knowledge import (
    AuthoredKnowledgeRecord,
    compile_authored_records_from_snapshot,
    setup_snapshot_hash,
)
from .compiled_index_provider import CompiledIndexRetrievalProvider
from .knowledge_write_policy import (
    ALLOWED_USER_PROFILE_KEYS,
    build_learned_world_records,
    build_user_profile_record,
)
from .scope_knowledge_repository import (
    USER_PROFILE,
    ScopeKnowledgeRecord,
    ScopeKnowledgeRepository,
)
from .session_state import LiveSession
from .story_knowledge_repository import StoryKnowledgeRepository
from .story_knowledge_service import StoryKnowledgeService
from .retrieval_selection import (
    RetrievalDiagnostics,
    RetrievalQueryContext,
    build_viewer_retrieval_request,
    candidate_to_authored_record,
    candidate_to_scope_record,
    character_index_keys,
    select_retrieval_records,
)
from .retrieval_service import RetrievalService

_logger = logging.getLogger(__name__)


def _default_index_path() -> str | None:
    for key in ("HG_RETRIEVAL_INDEX_PATH", "RP_RETRIEVED_CONTEXT_INDEX"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


class KnowledgeService:
    """Backend-independent knowledge retrieval and promotion for ContextAssembly."""

    def __init__(
        self,
        scope_repo: ScopeKnowledgeRepository | None = None,
        *,
        retrieval_provider: CompiledIndexRetrievalProvider | None = None,
        retrieval_index_path: str | Path | None = None,
        story_knowledge_repo: StoryKnowledgeRepository | None = None,
    ) -> None:
        self._scope_repo = scope_repo
        if retrieval_provider is not None:
            self._retrieval_provider = retrieval_provider
        else:
            resolved_path = retrieval_index_path or _default_index_path()
            self._retrieval_provider = (
                CompiledIndexRetrievalProvider(resolved_path)
                if resolved_path
                else CompiledIndexRetrievalProvider()
            )
        self._last_retrieval_diagnostics: dict[str, RetrievalDiagnostics] = {}
        self._story_knowledge_repo = story_knowledge_repo
        self._story_knowledge_service = (
            StoryKnowledgeService(story_knowledge_repo) if story_knowledge_repo is not None else None
        )
        self._retrieval_service = RetrievalService(
            scope_repo=self._scope_repo,
            retrieval_provider=self._retrieval_provider,
            story_knowledge_repo=story_knowledge_repo,
        )

    @property
    def scope_repo(self) -> ScopeKnowledgeRepository | None:
        return self._scope_repo

    @property
    def story_knowledge_service(self) -> StoryKnowledgeService | None:
        return self._story_knowledge_service

    def compile_snapshot_records(self, fixture: LiveSession) -> list[AuthoredKnowledgeRecord]:
        return compile_authored_records_from_snapshot(fixture.setup_snapshot or {})

    def _build_query_context(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> RetrievalQueryContext:
        file_id = fixture.character_file_ids.get(character_id)
        template_id = str(
            (fixture.setup_snapshot or {}).get("scene_template_id") or ""
        ).strip() or None
        return RetrievalQueryContext(
            character_file_id=file_id,
            character_display_name=character_id,
            session_template_id=template_id,
            character_index_keys=character_index_keys(
                character_file_id=file_id,
                character_display_name=character_id,
            ),
        )

    def retrieve_authored(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> tuple[list[AuthoredKnowledgeRecord], list[AuthoredKnowledgeRecord]]:
        request = build_viewer_retrieval_request(
            fixture,
            character_id=character_id,
            information_classes=frozenset({"authored_static", "compiled_index"}),
            audit_reason="knowledge_service_authored",
        )
        response = self._retrieval_service.retrieve(request, fixture)
        authored_candidates = [
            candidate_to_authored_record(candidate)
            for candidate in response.candidates
        ]
        merged = [record for record in authored_candidates if record is not None]
        query_ctx = self._build_query_context(fixture, character_id=character_id)
        diagnostics = RetrievalDiagnostics(
            provider_id=self._retrieval_provider.provider_id,
            index_path=self._retrieval_provider.index_path,
            setup_snapshot_hash=setup_snapshot_hash(fixture.setup_snapshot or {}),
            dedupe_dropped=response.diagnostics.dedupe_dropped,
        )
        character_records, scene_records = select_retrieval_records(
            merged,
            character_file_id=query_ctx.character_file_id,
            session_template_id=query_ctx.session_template_id,
            diagnostics=diagnostics,
        )
        self._last_retrieval_diagnostics[character_id] = diagnostics
        return character_records, scene_records

    def last_retrieval_diagnostics(self, character_id: str) -> dict[str, Any]:
        diag = self._last_retrieval_diagnostics.get(character_id)
        return diag.to_dict() if diag is not None else {}

    def promote_after_commit(
        self,
        fixture: LiveSession,
        *,
        source_domain_commit_id: str,
    ) -> int:
        """Best-effort learned-world promotion after authoritative session persist."""
        promoted = 0
        if self._scope_repo is not None:
            records = build_learned_world_records(
                fixture,
                source_domain_commit_id=source_domain_commit_id,
            )
            if records:
                try:
                    promoted = self._scope_repo.append_records(records)
                except OSError as exc:
                    _logger.warning(
                        "scope knowledge promotion failed for session %s: %s",
                        fixture.hg_session_id,
                        exc,
                    )
        if self._story_knowledge_service is not None:
            try:
                self._story_knowledge_service.project_after_commit(
                    fixture,
                    source_domain_commit_id=source_domain_commit_id,
                )
            except OSError as exc:
                _logger.warning(
                    "story knowledge projection failed for session %s: %s",
                    fixture.hg_session_id,
                    exc,
                )
        return promoted

    def write_user_profile(
        self,
        fixture: LiveSession,
        *,
        profile_key: str,
        content: str,
        user_persona_id: str,
    ) -> dict[str, Any]:
        if self._scope_repo is None:
            raise ValueError("scope knowledge repository is not configured")
        record = build_user_profile_record(
            fixture,
            profile_key=profile_key,
            content=content,
            user_persona_id=user_persona_id,
        )
        try:
            knowledge_id = self._scope_repo.upsert_user_profile(record)
        except OSError as exc:
            _logger.warning(
                "user profile write failed for session %s: %s",
                fixture.hg_session_id,
                exc,
            )
            raise ValueError("failed to persist user profile knowledge") from exc
        return {
            "knowledge_id": knowledge_id,
            "scope_id": record.scope_id,
            "profile_key": record.profile_key,
            "user_persona_id": record.user_persona_id,
            "knowledge_kind": USER_PROFILE,
        }

    def retrieve_scope_knowledge(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> tuple[list[ScopeKnowledgeRecord], list[ScopeKnowledgeRecord]]:
        if self._scope_repo is None or not fixture.memory_scope_id:
            return [], []
        request = build_viewer_retrieval_request(
            fixture,
            character_id=character_id,
            information_classes=frozenset({"promoted_learned_world", "user_profile"}),
            audit_reason="knowledge_service_scope",
        )
        response = self._retrieval_service.retrieve(request, fixture)
        world_records: list[ScopeKnowledgeRecord] = []
        profile_records: list[ScopeKnowledgeRecord] = []
        for candidate in response.candidates:
            record = candidate_to_scope_record(candidate)
            if record is None:
                continue
            if candidate.information_class == "promoted_learned_world":
                world_records.append(record)
            elif candidate.information_class == "user_profile":
                profile_records.append(record)
        return world_records, profile_records

    @staticmethod
    def allowed_user_profile_keys() -> frozenset[str]:
        return ALLOWED_USER_PROFILE_KEYS

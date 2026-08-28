"""Story knowledge orchestration — projection, persistence, and index maintenance (#50)."""

from __future__ import annotations

import logging
from typing import Any

from .session_state import LiveSession
from .story_knowledge_contract import (
    STORY_KNOWLEDGE_SCHEMA_VERSION,
    DerivedStoryRecordSubmission,
    StoryKnowledgeRecord,
)
from .story_knowledge_projection import project_missing_occurrences
from .story_knowledge_repository import StoryKnowledgeRepository
from .story_semantic_index import SemanticIndexBackend

_logger = logging.getLogger(__name__)


class StoryKnowledgeService:
    """Post-commit projection and derived-record submission seam."""

    def __init__(self, repository: StoryKnowledgeRepository) -> None:
        self._repo = repository

    @property
    def repository(self) -> StoryKnowledgeRepository:
        return self._repo

    def semantic_index_for(self, memory_scope_id: str) -> SemanticIndexBackend:
        return SemanticIndexBackend(index_path=self._repo.semantic_index_path(memory_scope_id))

    def list_records(self, memory_scope_id: str) -> list[StoryKnowledgeRecord]:
        return self._repo.list_records(memory_scope_id)

    def project_after_commit(
        self,
        fixture: LiveSession,
        *,
        source_domain_commit_id: str,
    ) -> dict[str, Any]:
        """Project newly committed PublicEvents into durable story knowledge."""
        scope_id = str(fixture.memory_scope_id or "").strip()
        if not scope_id:
            return {"appended": 0, "index_errors": []}

        projected = project_missing_occurrences(
            fixture,
            source_domain_commit_id=source_domain_commit_id,
        )
        appended = 0
        index_errors: list[str] = []
        semantic_index = self.semantic_index_for(scope_id)

        for record in projected:
            try:
                if self._repo.append_record(record):
                    appended += 1
                    try:
                        semantic_index.upsert(
                            record.record_id,
                            text=record.embedding_text(),
                            content_hash=record.content_hash or record.compute_content_hash(),
                        )
                    except OSError as exc:
                        index_errors.append(f"{record.record_id}: {exc}")
                        _logger.warning(
                            "story semantic index update failed for %s: %s",
                            record.record_id,
                            exc,
                        )
            except (OSError, ValueError) as exc:
                _logger.warning(
                    "story knowledge append failed for session %s event %s: %s",
                    fixture.hg_session_id,
                    record.event_id,
                    exc,
                )

        return {"appended": appended, "index_errors": index_errors}

    def backfill_scope(
        self,
        fixture: LiveSession,
        *,
        source_domain_commit_id: str,
    ) -> int:
        """Idempotent backfill of all authoritative PublicEvents for a scope."""
        result = self.project_after_commit(
            fixture,
            source_domain_commit_id=source_domain_commit_id,
        )
        return int(result.get("appended", 0))

    def submit_derived_record(self, submission: DerivedStoryRecordSubmission) -> bool:
        """Neutral derived-record submission — records authorized establishment only."""
        record = StoryKnowledgeRecord(
            schema_version=STORY_KNOWLEDGE_SCHEMA_VERSION,
            record_kind="derived",
            memory_scope_id=submission.memory_scope_id,
            source_session_id=submission.source_session_id,
            source_domain_commit_id=submission.source_domain_commit_id,
            hg_scene_id=submission.hg_scene_id,
            turn_index=submission.turn_index,
            event_type=None,
            participants=list(submission.participants),
            location=submission.location,
            stable_refs=list(submission.stable_refs),
            evidence=submission.evidence,
            related_refs=list(submission.related_refs),
            story_record_id=submission.story_record_id,
            epistemic_authority_ref=submission.epistemic_authority_ref,
            submission_authority_ref=submission.submission_authority_ref,
        )
        record.content_hash = record.compute_content_hash()
        if not self._repo.append_record(record):
            return False
        try:
            index = self.semantic_index_for(submission.memory_scope_id)
            index.upsert(
                record.record_id,
                text=record.embedding_text(),
                content_hash=record.content_hash,
            )
        except OSError as exc:
            _logger.warning("derived record index update failed for %s: %s", record.record_id, exc)
        return True

    def rebuild_semantic_index(self, memory_scope_id: str) -> int:
        """Rebuild semantic index from durable JSONL records only."""
        records = self._repo.list_records(memory_scope_id)
        index = self.semantic_index_for(memory_scope_id)
        tuples = [
            (
                record.record_id,
                record.embedding_text(),
                record.content_hash or record.compute_content_hash(),
            )
            for record in records
        ]
        index.rebuild(tuples)
        return len(tuples)

    def recover_scope(self, memory_scope_id: str) -> int:
        """Recover truncated JSONL tail and rebuild semantic index."""
        count = self._repo.recover_truncated_tail(memory_scope_id)
        self.rebuild_semantic_index(memory_scope_id)
        return count

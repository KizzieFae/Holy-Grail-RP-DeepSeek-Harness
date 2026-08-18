"""Domain Host knowledge orchestration: authored (M11.1) + scope lanes (M11.2)."""

from __future__ import annotations

import logging
from typing import Any

from .authored_knowledge import (
    AuthoredKnowledgeRecord,
    compile_authored_records_from_snapshot,
    format_knowledge_content,
    select_authored_records,
    setup_snapshot_hash,
)
from .knowledge_write_policy import (
    ALLOWED_USER_PROFILE_KEYS,
    build_learned_world_records,
    build_user_profile_record,
    filter_active_learned_world_records,
)
from .scope_knowledge_repository import (
    DEFAULT_LEARNED_WORLD_LIMIT,
    DEFAULT_USER_PROFILE_LIMIT,
    LEARNED_WORLD_KNOWLEDGE,
    USER_PROFILE,
    ScopeKnowledgeRecord,
    ScopeKnowledgeRepository,
)
from .session_state import LiveSession

_logger = logging.getLogger(__name__)


class KnowledgeService:
    """Backend-independent knowledge retrieval and promotion for ContextAssembly."""

    def __init__(self, scope_repo: ScopeKnowledgeRepository | None = None) -> None:
        self._scope_repo = scope_repo

    @property
    def scope_repo(self) -> ScopeKnowledgeRepository | None:
        return self._scope_repo

    def compile_snapshot_records(self, fixture: LiveSession) -> list[AuthoredKnowledgeRecord]:
        return compile_authored_records_from_snapshot(fixture.setup_snapshot or {})

    def retrieve_authored(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> tuple[list[AuthoredKnowledgeRecord], list[AuthoredKnowledgeRecord]]:
        file_id = fixture.character_file_ids.get(character_id)
        template_id = str(
            (fixture.setup_snapshot or {}).get("scene_template_id") or ""
        ).strip() or None
        records = self.compile_snapshot_records(fixture)
        return select_authored_records(
            records,
            character_file_id=file_id,
            session_template_id=template_id,
        )

    def promote_after_commit(
        self,
        fixture: LiveSession,
        *,
        source_domain_commit_id: str,
    ) -> int:
        """Best-effort learned-world promotion after authoritative session persist."""
        if self._scope_repo is None:
            return 0
        records = build_learned_world_records(
            fixture,
            source_domain_commit_id=source_domain_commit_id,
        )
        if not records:
            return 0
        try:
            return self._scope_repo.append_records(records)
        except OSError as exc:
            _logger.warning(
                "scope knowledge promotion failed for session %s: %s",
                fixture.hg_session_id,
                exc,
            )
            return 0

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

    def _visible_to_character(
        self,
        record: ScopeKnowledgeRecord,
        *,
        character_id: str,
        character_file_ids: dict[str, str],
    ) -> bool:
        if record.visibility == "scope_global":
            return True
        if record.visibility == "character_scoped":
            file_id = character_file_ids.get(character_id)
            return bool(file_id and file_id == record.subject_character_file_id)
        return False

    def retrieve_scope_knowledge(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> tuple[list[ScopeKnowledgeRecord], list[ScopeKnowledgeRecord]]:
        if self._scope_repo is None or not fixture.memory_scope_id:
            return [], []
        world_records = self._scope_repo.list_records(
            fixture.memory_scope_id,
            knowledge_kinds={LEARNED_WORLD_KNOWLEDGE},
            limit=DEFAULT_LEARNED_WORLD_LIMIT,
        )
        profile_records = self._scope_repo.list_records(
            fixture.memory_scope_id,
            knowledge_kinds={USER_PROFILE},
            limit=DEFAULT_USER_PROFILE_LIMIT,
        )
        character_file_ids = dict(fixture.character_file_ids or {})
        active_world = filter_active_learned_world_records(fixture, world_records)
        visible_world = [
            record
            for record in active_world
            if self._visible_to_character(
                record,
                character_id=character_id,
                character_file_ids=character_file_ids,
            )
        ]
        visible_profile = [
            record
            for record in profile_records
            if self._visible_to_character(
                record,
                character_id=character_id,
                character_file_ids=character_file_ids,
            )
        ]
        return visible_world, visible_profile

    def project_context(
        self,
        fixture: LiveSession,
        *,
        character_id: str,
    ) -> list[tuple[str, str, dict[str, Any]]]:
        """Return (source_kind, content, provenance) tuples for ContextAssembly."""
        character_records, scene_records = self.retrieve_authored(
            fixture, character_id=character_id
        )
        world_records, profile_records = self.retrieve_scope_knowledge(
            fixture, character_id=character_id
        )
        projections: list[tuple[str, str, dict[str, Any]]] = []
        file_id = fixture.character_file_ids.get(character_id)
        snap_hash = setup_snapshot_hash(fixture.setup_snapshot or {})

        character_content = format_knowledge_content(
            character_records,
            title="Authored character knowledge (reference; current scene state is authoritative)",
        )
        if character_content:
            projections.append(
                (
                    "authored_character_knowledge",
                    character_content,
                    {
                        "knowledge_lane": "authored_character_knowledge",
                        "visibility": "character_scoped",
                        "subject_character_file_id": file_id,
                        "character_id": character_id,
                        "knowledge_ids": [r.knowledge_id for r in character_records],
                        "setup_snapshot_hash": snap_hash,
                        "authority_class": "suggestive",
                        "authority_note": "suggestive_reference_not_current_canon",
                    },
                )
            )

        scene_content = format_knowledge_content(
            scene_records,
            title="Scene template reference (setup context; not current authoritative state)",
        )
        if scene_content:
            projections.append(
                (
                    "scene_reference",
                    scene_content,
                    {
                        "knowledge_lane": "scene_reference",
                        "visibility": "template_participants",
                        "character_id": character_id,
                        "knowledge_ids": [r.knowledge_id for r in scene_records],
                        "setup_snapshot_hash": snap_hash,
                        "source_scene_template_id": (fixture.setup_snapshot or {}).get(
                            "scene_template_id"
                        ),
                        "authority_class": "suggestive",
                        "authority_note": "suggestive_reference_not_current_canon",
                    },
                )
            )

        world_lines = [str(record.content).strip() for record in world_records if record.content]
        if world_lines:
            projections.append(
                (
                    "learned_world_knowledge",
                    "Learned world knowledge (reference derived from continuity; "
                    "current scene state is authoritative):\n"
                    + "\n".join(f"- {line}" for line in world_lines),
                    {
                        "knowledge_lane": "learned_world_knowledge",
                        "character_id": character_id,
                        "knowledge_ids": [r.knowledge_id for r in world_records],
                        "scope_id": fixture.memory_scope_id,
                        "authority_class": "suggestive",
                        "authority_note": "reference_derived_from_continuity_not_independent_canon",
                    },
                )
            )

        profile_lines = [
            f"{record.profile_key}: {record.content}"
            for record in profile_records
            if record.profile_key and record.content
        ]
        if profile_lines:
            projections.append(
                (
                    "user_profile",
                    "User profile (player dimension only; not world canon):\n"
                    + "\n".join(f"- {line}" for line in profile_lines),
                    {
                        "knowledge_lane": "user_profile",
                        "character_id": character_id,
                        "knowledge_ids": [r.knowledge_id for r in profile_records],
                        "scope_id": fixture.memory_scope_id,
                        "authority_class": "suggestive",
                        "authority_note": "user_profile_not_world_canon",
                    },
                )
            )

        return projections

    @staticmethod
    def allowed_user_profile_keys() -> frozenset[str]:
        return ALLOWED_USER_PROFILE_KEYS

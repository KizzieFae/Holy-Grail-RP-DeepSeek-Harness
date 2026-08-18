"""Domain Host authored knowledge orchestration (M11.1 read/projection only)."""

from __future__ import annotations

from typing import Any

from .authored_knowledge import (
    AuthoredKnowledgeRecord,
    compile_authored_records_from_snapshot,
    format_knowledge_content,
    select_authored_records,
    setup_snapshot_hash,
)
from .session_state import LiveSession


class KnowledgeService:
    """Backend-independent authored knowledge retrieval for ContextAssembly."""

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
                        "authority_note": "suggestive_reference_not_current_canon",
                    },
                )
            )

        return projections

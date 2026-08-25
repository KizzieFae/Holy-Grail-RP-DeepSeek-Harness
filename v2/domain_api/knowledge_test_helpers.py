"""Shared helpers for #38 knowledge-path integration test assertions."""

from __future__ import annotations

from .knowledge_service import KnowledgeService
from .session_state import LiveSession


def retrieve_authored_text(
    knowledge_service: KnowledgeService,
    fixture: LiveSession,
    *,
    character_id: str,
) -> tuple[list[str], list[str]]:
    character_records, scene_records = knowledge_service.retrieve_authored(
        fixture, character_id=character_id
    )
    return (
        [record.content for record in character_records],
        [record.content for record in scene_records],
    )


def retrieve_scope_world_text(
    knowledge_service: KnowledgeService,
    fixture: LiveSession,
    *,
    character_id: str,
) -> str:
    world_records, _profiles = knowledge_service.retrieve_scope_knowledge(
        fixture, character_id=character_id
    )
    return "\n".join(record.content for record in world_records)

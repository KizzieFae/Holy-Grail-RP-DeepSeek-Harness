"""Shared context-assembly primitives for role manifest preparation (#54 C2)."""

from __future__ import annotations

import json
from typing import Any

from .continuity_context_projector import AuthoritativeContextContribution
from .contract import PromptContribution
from .memory_retrieval import build_session_memory_projection
from .memory_service import MemoryService
from .session_state import LiveSession


def auth_projections_to_contributions(
    manifest_id: str,
    projections: list[AuthoritativeContextContribution],
) -> list[PromptContribution]:
    return [
        PromptContribution(
            contribution_id=f"{manifest_id}-{proj.source_kind}",
            source_kind=proj.source_kind,  # type: ignore[arg-type]
            authority_class=proj.authority_class,  # type: ignore[arg-type]
            knowledge_ids=proj.knowledge_ids,
            priority=proj.priority,
            content=proj.content,
            provenance=dict(proj.provenance),
        )
        for proj in projections
    ]


def semantic_correction_contribution(
    manifest_id: str,
    correction: dict[str, Any],
    *,
    inference_id: str,
    attempt_index: int | None = None,
    evaluation_pass_id: str | None = None,
) -> PromptContribution:
    provenance: dict[str, Any] = {
        "inference_id": inference_id,
        "visibility": "orchestration_only",
    }
    if attempt_index is not None:
        provenance["attempt_index"] = attempt_index
    return PromptContribution(
        contribution_id=f"{manifest_id}-semantic-correction",
        source_kind="semantic_correction",
        authority_class="suggestive",
        knowledge_ids=(
            str(correction.get("evaluation_pass_id") or evaluation_pass_id or inference_id),
        ),
        priority=29,
        content=json.dumps(correction, ensure_ascii=False, indent=2),
        provenance=provenance,
    )


def memory_projections_for_character(
    fixture: LiveSession,
    character_id: str,
    memory_service: MemoryService | None,
) -> list[tuple[str, dict[str, Any]]]:
    if memory_service is not None:
        return memory_service.retrieve_memory_contributions(fixture, character_id=character_id)
    single = build_session_memory_projection(fixture.character_states.get(character_id))
    return [single] if single is not None else []

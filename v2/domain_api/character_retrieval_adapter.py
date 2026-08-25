"""Character Packaging adapter for generalized Retrieval (#31 S1 compatibility)."""

from __future__ import annotations

import uuid

from .authored_knowledge import AuthoredKnowledgeRecord, setup_snapshot_hash
from .retrieval_contract import (
    ALL_INFORMATION_CLASSES,
    GenerationHints,
    HardAccessConstraints,
    RetrievalAccessRequest,
    RetrievalCandidate,
    ResponseBudget,
)
from .retrieval_selection import character_index_keys
from .scope_knowledge_repository import ScopeKnowledgeRecord
from .session_state import LiveSession


def _authored_classes() -> frozenset[str]:
    return frozenset({"authored_static", "compiled_index"})


def _scope_classes() -> frozenset[str]:
    return frozenset({"promoted_learned_world", "user_profile"})


def build_character_packaging_request(
    fixture: LiveSession,
    *,
    character_id: str,
    request_id: str | None = None,
    information_classes: frozenset[str] = ALL_INFORMATION_CLASSES,
) -> RetrievalAccessRequest:
    """Build a broad-pool retrieval request for the Character Packaging path."""
    file_id = fixture.character_file_ids.get(character_id)
    template_id = str((fixture.setup_snapshot or {}).get("scene_template_id") or "").strip() or None
    anchors = character_index_keys(
        character_file_id=file_id,
        character_display_name=character_id,
    )
    last_round = fixture.rounds[-1] if fixture.rounds else None
    return RetrievalAccessRequest(
        request_id=request_id or f"hg-retrieval-{uuid.uuid4()}",
        consumer_role="host_packaging_legacy",
        hg_scene_id=fixture.hg_session_id,
        hg_round_id=str(last_round.hg_round_id if last_round else "unbound"),
        turn_index=int(last_round.turn_index if last_round else 0),
        memory_scope_id=fixture.memory_scope_id,
        hard_access=HardAccessConstraints(
            viewer_character_id=character_id,
            subject_character_file_id=file_id,
            session_template_id=template_id,
            allowed_information_classes=information_classes,
            exclude_authoritative_live=True,
        ),
        generation_hints=GenerationHints(
            entity_anchors=anchors,
            recall_mode="broad",
            class_recall_budgets={
                "promoted_learned_world": 8,
                "user_profile": 6,
            },
        ),
        response_budget=ResponseBudget(),
        audit_reason="character_packaging_legacy_adapter",
    )


def candidate_to_authored_record(candidate: RetrievalCandidate) -> AuthoredKnowledgeRecord | None:
    if candidate.information_class not in _authored_classes():
        return None
    legacy = candidate.host_internal_metadata.get("legacy_authored_record")
    if isinstance(legacy, dict):
        return AuthoredKnowledgeRecord(
            knowledge_id=str(legacy["knowledge_id"]),
            knowledge_kind=str(legacy["knowledge_kind"]),
            content=str(legacy["content"]),
            authority_class=str(legacy["authority_class"]),
            visibility=str(legacy["visibility"]),
            subject_character_file_id=legacy.get("subject_character_file_id"),
            source_kind=str(legacy["source_kind"]),
            source_asset_id=str(legacy["source_asset_id"]),
            provenance=dict(legacy.get("provenance") or {}),
        )
    provenance = dict(candidate.provenance)
    return AuthoredKnowledgeRecord(
        knowledge_id=candidate.candidate_id,
        knowledge_kind=str(provenance.get("knowledge_lane", "authored")),
        content=candidate.payload.content,
        authority_class=candidate.authority_class,
        visibility=candidate.visibility,
        subject_character_file_id=candidate.subject_character_file_id,
        source_kind=str(provenance.get("source_kind", "")),
        source_asset_id=str(provenance.get("source_asset_id", "")),
        provenance=provenance,
    )


def candidate_to_scope_record(candidate: RetrievalCandidate) -> ScopeKnowledgeRecord | None:
    if candidate.information_class not in _scope_classes():
        return None
    legacy = candidate.host_internal_metadata.get("legacy_scope_record")
    if isinstance(legacy, dict):
        return ScopeKnowledgeRecord.from_dict(legacy)
    provenance = dict(candidate.provenance)
    return ScopeKnowledgeRecord(
        knowledge_id=candidate.candidate_id,
        scope_id=str(provenance.get("scope_id", "")),
        knowledge_kind=str(provenance.get("knowledge_lane", candidate.information_class)),
        content=candidate.payload.content,
        authority_class=candidate.authority_class,
        visibility=candidate.visibility,
        subject_character_file_id=candidate.subject_character_file_id,
        source_kind=str(provenance.get("source_kind", "")),
        provenance=provenance,
        created_at=str(candidate.temporal_metadata.get("created_at", "")),
        profile_key=candidate.host_internal_metadata.get("profile_key"),
        user_persona_id=candidate.host_internal_metadata.get("user_persona_id"),
    )


def packaging_setup_snapshot_hash(fixture: LiveSession) -> str:
    return setup_snapshot_hash(fixture.setup_snapshot or {})

"""Authoritative live-state input for Librarian (#34 S2a.3).

Live Continuity projection bypasses #31. Durable/indexed candidates remain on the
Retrieval façade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .continuity_context_projector import (
    AuthoritativeContextContribution,
    ContextRole,
    project_authoritative_context,
)
from .librarian_contract import (
    KnowledgeAccessRequest,
    LibrarianAnnotation,
    LibrarianBundleEntry,
    PipelineStage,
    StableReference,
    VisibilityScope,
)
from .session_state import LiveSession


@dataclass(frozen=True)
class AuthoritativeWorkingItem:
    contribution: AuthoritativeContextContribution
    source_tier: str
    temporal_relationship: str


_SOURCE_TIER_BY_KIND = {
    "scene_state": "authoritative_live_continuity",
    "scene_setup": "authoritative_live_continuity",
    "scene_progression": "authoritative_live_continuity",
    "recent_environment": "recent_developments",
    "continuity_canon": "canon_anchors",
    "scene_grounding": "scene_grounding",
    "active_constraints": "authoritative_live_continuity",
}


def _context_role(request: KnowledgeAccessRequest) -> ContextRole:
    stage = request.pipeline_stage
    if stage == "character":
        return "character"
    if stage == "narrator":
        return "narrator"
    return "director"


def _character_id(request: KnowledgeAccessRequest) -> str | None:
    envelope = request.visibility_envelope
    if envelope.subject_character_id:
        return envelope.subject_character_id
    if request.consumer_role == "character":
        return request.consumer_instance_id or envelope.viewer_character_id
    return None


def collect_authoritative_working_items(
    request: KnowledgeAccessRequest,
    fixture: LiveSession,
) -> list[AuthoritativeWorkingItem]:
    role = _context_role(request)
    character_id = _character_id(request)
    contributions = project_authoritative_context(
        fixture,
        role=role,
        hg_scene_id=request.hg_scene_id,
        hg_round_id=request.hg_round_id,
        character_id=character_id,
        turn_index=request.turn_index,
    )
    excluded = set(request.exclude_source_tiers or ())
    items: list[AuthoritativeWorkingItem] = []
    for contribution in contributions:
        source_tier = _SOURCE_TIER_BY_KIND.get(contribution.source_kind, "authoritative_live_continuity")
        if source_tier in excluded:
            continue
        temporal = "current"
        if contribution.source_kind in {"scene_setup"}:
            temporal = "historical"
        elif contribution.source_kind in {"scene_progression", "recent_environment"}:
            temporal = "recent"
        items.append(
            AuthoritativeWorkingItem(
                contribution=contribution,
                source_tier=source_tier,
                temporal_relationship=temporal,
            )
        )
    return items


def authoritative_item_to_bundle_entry(
    item: AuthoritativeWorkingItem,
    *,
    entry_id: str,
    relevance_rank: int,
    answers_focus_questions: tuple[str, ...] = (),
) -> LibrarianBundleEntry:
    contribution = item.contribution
    primary_ref = contribution.knowledge_ids[0] if contribution.knowledge_ids else contribution.source_kind
    visibility: VisibilityScope | str = "scene_orchestration"
    provenance = dict(contribution.provenance)
    if provenance.get("visibility"):
        visibility = str(provenance["visibility"])
    elif provenance.get("character_id"):
        visibility = "character_scoped"

    return LibrarianBundleEntry(
        entry_id=entry_id,
        ref=StableReference(
            ref_kind="authoritative_projection",
            stable_ref=str(primary_ref),
            display_hint=contribution.source_kind,
        ),
        content=contribution.content,
        information_class=(
            "authored_static"
            if contribution.source_kind == "scene_setup"
            else "authoritative_live"
        ),
        source_tier=item.source_tier,
        authority_class="authoritative",
        visibility_scope=visibility,
        provenance={
            **provenance,
            "source_kind": contribution.source_kind,
            "authority_note": "live_continuity_projection_not_knowledge_store",
        },
        temporal_relationship=item.temporal_relationship,
        temporal_anchor_turn=provenance.get("continuity_turn_index"),
        librarian_annotation=LibrarianAnnotation(
            relevance_rank=relevance_rank,
            relevance_band="high" if relevance_rank <= 3 else "medium",
            interpretive_status="confirmed",
            answers_focus_questions=answers_focus_questions,
            salience_note="authoritative live continuity projection",
        ),
    )


def authoritative_snapshot_id(fixture: LiveSession, request: KnowledgeAccessRequest) -> str:
    return f"cv:{fixture.continuity_version}:scene:{request.hg_scene_id}:round:{request.hg_round_id}"

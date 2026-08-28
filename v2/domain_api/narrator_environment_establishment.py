"""B2 environmental descriptor establishment via #50 substrate (#49)."""

from __future__ import annotations

import uuid
from typing import Any

from .narrator_environment_location_binding import bind_location_stable_ref
from domain_api.narrator_environment_contract import (
    ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE,
    ENVIRONMENTAL_DESCRIPTOR_MARKER,
    environmental_descriptor_payload,
)
from domain_api.session_state import LiveSession
from domain_api.story_knowledge_contract import (
    DerivedStoryRecordSubmission,
    EpistemicAuthorityRef,
    StableRef,
    StoryEvidence,
    StoryRelation,
)
from domain_api.story_knowledge_service import StoryKnowledgeService


def validate_b2_proposal(
    *,
    property_key: str,
    value: str,
    stable_refs: tuple[str, ...],
) -> tuple[bool, str]:
    key = str(property_key or "").strip()
    val = str(value or "").strip()
    if not key:
        return False, "property_key required"
    if not val:
        return False, "value required"
    if not stable_refs:
        return False, "stable_refs required for continuity-bearing environmental detail"
    return True, ""


def accept_b2_environmental_descriptor(
    fixture: LiveSession,
    service: StoryKnowledgeService,
    *,
    property_key: str,
    value: str,
    stable_refs: tuple[str, ...],
    source_domain_commit_id: str,
    turn_index: int | None,
    supersedes: str | None = None,
    cognition_id: str | None = None,
) -> dict[str, Any]:
    ok, reason = validate_b2_proposal(
        property_key=property_key,
        value=value,
        stable_refs=stable_refs,
    )
    if not ok:
        return {"accepted": False, "reason": reason, "story_record_id": None}

    scope_id = str(fixture.memory_scope_id or "").strip()
    if not scope_id:
        return {"accepted": False, "reason": "memory_scope_id missing", "story_record_id": None}

    story_record_id = f"env-b2-{uuid.uuid4().hex[:16]}"
    location_label = ""
    if fixture.manager.scene_state is not None:
        location_label = str(fixture.manager.scene_state.location or "")
    location_ref = bind_location_stable_ref(location_label)

    refs = [location_ref]
    for ref in stable_refs:
        if ref.startswith("location:"):
            refs.append(StableRef(ref_kind="location", stable_ref=ref))
        elif ref.startswith("object:"):
            refs.append(StableRef(ref_kind="object", stable_ref=ref))
        else:
            refs.append(StableRef(ref_kind="entity", stable_ref=ref))

    related: list[StoryRelation] = []
    if supersedes:
        related.append(StoryRelation(rel="supersedes", target_id=supersedes))

    authority = EpistemicAuthorityRef(
        ref_kind="establishment_decision",
        ref_payload={
            "establishment_kind": "narrator_environmental_b2",
            "domain_commit_id": source_domain_commit_id,
            "cognition_id": cognition_id,
            "property_key": property_key,
        },
    )
    submission = DerivedStoryRecordSubmission(
        story_record_id=story_record_id,
        memory_scope_id=scope_id,
        source_domain_commit_id=source_domain_commit_id,
        source_session_id=fixture.hg_session_id,
        hg_scene_id=fixture.hg_scene_id,
        source_event_ids=(),
        stable_refs=tuple(refs),
        evidence=StoryEvidence(
            summary=f"Environmental descriptor: {property_key}={value}",
            committed_text=environmental_descriptor_payload(
                property_key=property_key,
                value=value,
                stable_refs=stable_refs,
                supersedes=supersedes,
            ),
        ),
        epistemic_authority_ref=authority,
        submission_authority_ref=f"narrator_environment:{cognition_id or source_domain_commit_id}",
        related_refs=tuple(related),
        turn_index=turn_index,
        location=location_label or None,
        participants=tuple(fixture.cast),
        event_type=ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE,
        grounding_markers=(ENVIRONMENTAL_DESCRIPTOR_MARKER,),
    )
    appended = service.submit_derived_record(submission)
    if not appended:
        return {
            "accepted": False,
            "reason": "duplicate or persistence failure",
            "story_record_id": story_record_id,
        }
    return {
        "accepted": True,
        "reason": "b2_established",
        "story_record_id": story_record_id,
        "property_key": property_key,
        "value": value,
        "supersedes": supersedes,
    }


def reject_c_establishment_via_narrator() -> dict[str, Any]:
    """C facts require stronger governed establishment — Narrator cannot establish alone."""
    return {
        "accepted": False,
        "reason": "material_story_fact_requires_governed_establishment_path",
    }

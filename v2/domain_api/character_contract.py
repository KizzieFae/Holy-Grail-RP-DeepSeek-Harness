"""Character knowledge-orientation contracts (#38)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from .librarian_contract import (
    ALL_INFORMATION_CLASSES,
    BudgetExpectations,
    DegradationPreferences,
    InformationNeed,
    KnowledgeAccessRequest,
    RelationshipFocus,
    VisibilityEnvelope,
    new_request_id,
)
from .retrieval_contract import EntityRef

CHARACTER_ORIENTATION_SCHEMA = "hg_character_orientation_v1"

TemporalOrientation = Literal["current", "recent", "historical", "session", "arc"]
RecallBreadthPreference = Literal["broad", "focused"]

PROHIBITED_CHARACTER_ORIENTATION_FIELDS = frozenset(
    {
        "structured_move",
        "beats",
        "dialogue",
        "narration",
        "character_state",
        "continuity_mutation",
        "next_actor",
        "must_act",
        "must_say",
        "must_do",
    }
)


@dataclass(frozen=True)
class CharacterOrientationAssessment:
    orientation_id: str
    hg_round_id: str
    turn_index: int
    character_id: str
    information_gaps: tuple[str, ...]
    entity_attention: tuple[EntityRef, ...] = ()
    relationship_focus: tuple[tuple[str, str | None, str | None], ...] = ()
    temporal_focus: TemporalOrientation = "current"
    breadth_preference: RecallBreadthPreference = "focused"
    requested_classes: tuple[str, ...] = ()
    situational_hypothesis: str | None = None


def new_character_orientation_id() -> str:
    return f"char-orient-{uuid.uuid4()}"


def find_prohibited_character_fields(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if not isinstance(value, dict):
        return hits
    for key, nested in value.items():
        current = f"{path}.{key}" if path else key
        if key in PROHIBITED_CHARACTER_ORIENTATION_FIELDS:
            hits.append(current)
        hits.extend(find_prohibited_character_fields(nested, current))
    return hits


def _entity_ref_from_dict(item: dict[str, Any]) -> EntityRef:
    return EntityRef(
        stable_ref=str(item.get("stable_ref") or ""),
        display_hint=str(item.get("display_hint") or "").strip() or None,
        entity_kind=str(item.get("entity_kind") or "").strip() or None,
    )


def parse_character_orientation(
    raw: dict[str, Any] | str,
) -> tuple[CharacterOrientationAssessment | None, str | None]:
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc:
        return None, f"parse_error:{exc}"
    if not isinstance(parsed, dict):
        return None, "not_object"
    if str(parsed.get("schema", "")) != CHARACTER_ORIENTATION_SCHEMA:
        return None, "schema_mismatch"

    violations = find_prohibited_character_fields(parsed)
    if violations:
        return None, f"prohibited_fields:{','.join(violations[:5])}"

    gaps = tuple(
        str(item).strip()
        for item in (parsed.get("information_gaps") or [])
        if str(item).strip()
    )
    if not gaps:
        return None, "information_gaps_required"

    character_id = str(parsed.get("character_id") or "").strip()
    if not character_id:
        return None, "character_id_required"

    entity_attention = tuple(
        _entity_ref_from_dict(item)
        for item in (parsed.get("entity_attention") or [])
        if isinstance(item, dict) and item.get("stable_ref")
    )
    relationship_focus = tuple(
        (
            str(item.get("subject_ref", "")),
            item.get("object_ref"),
            item.get("relationship_kind"),
        )
        for item in (parsed.get("relationship_focus") or [])
        if isinstance(item, dict) and item.get("subject_ref")
    )
    requested_classes = tuple(
        str(item).strip()
        for item in (parsed.get("requested_classes") or [])
        if str(item).strip()
    )
    temporal = str(parsed.get("temporal_focus") or "current")
    if temporal not in {"current", "recent", "historical", "session", "arc"}:
        temporal = "current"
    breadth = str(parsed.get("breadth_preference") or "focused")
    if breadth not in {"broad", "focused"}:
        breadth = "focused"

    return (
        CharacterOrientationAssessment(
            orientation_id=str(parsed.get("orientation_id") or new_character_orientation_id()),
            hg_round_id=str(parsed.get("hg_round_id") or ""),
            turn_index=int(parsed.get("turn_index") or 0),
            character_id=character_id,
            information_gaps=gaps,
            entity_attention=entity_attention,
            relationship_focus=relationship_focus,
            temporal_focus=temporal,  # type: ignore[arg-type]
            breadth_preference=breadth,  # type: ignore[arg-type]
            requested_classes=requested_classes,
            situational_hypothesis=str(parsed.get("situational_hypothesis") or "").strip() or None,
        ),
        None,
    )


def orientation_to_knowledge_access_request(
    orientation: CharacterOrientationAssessment,
    *,
    hg_scene_id: str,
    request_id: str,
    visibility_envelope: dict[str, Any],
    host_allowed_information_classes: frozenset[str] = ALL_INFORMATION_CLASSES,
    correlation_inference_id: str | None = None,
) -> KnowledgeAccessRequest:
    relationship_focus = tuple(
        RelationshipFocus(
            subject_ref=subject,
            object_ref=obj,
            relationship_kind=kind,
        )
        for subject, obj, kind in orientation.relationship_focus
    )
    requested = frozenset(orientation.requested_classes) if orientation.requested_classes else None
    envelope = VisibilityEnvelope(
        viewer_role="character",
        authority_ceiling_enforced=visibility_envelope.get("authority_ceiling_enforced", "derived"),  # type: ignore[arg-type]
        viewer_character_id=visibility_envelope.get("viewer_character_id") or orientation.character_id,
        subject_character_id=visibility_envelope.get("subject_character_id") or orientation.character_id,
        session_template_id=visibility_envelope.get("session_template_id"),
        perception_gates_ref=visibility_envelope.get("perception_gates_ref"),
        known_by_snapshot_id=visibility_envelope.get("known_by_snapshot_id"),
    )
    return KnowledgeAccessRequest(
        request_id=request_id,
        consumer_role="character",
        consumer_instance_id=orientation.character_id,
        audit_reason="character_orientation",
        hg_scene_id=hg_scene_id,
        hg_round_id=orientation.hg_round_id,
        turn_index=orientation.turn_index,
        pipeline_stage="character",
        visibility_envelope=envelope,
        information_need=InformationNeed(
            focus_questions=orientation.information_gaps,
            entity_refs=orientation.entity_attention,
            relationship_focus=relationship_focus,
            temporal_orientation=orientation.temporal_focus,
            recall_breadth_preference=orientation.breadth_preference,
        ),
        correlation_inference_id=correlation_inference_id,
        requested_information_classes=requested,
        host_allowed_information_classes=host_allowed_information_classes,
        budget_expectations=BudgetExpectations(max_bundle_entries=8, max_bundle_chars=4000),
        degradation_preferences=DegradationPreferences(),
    )


def build_default_character_kar(
    *,
    character_id: str,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    visibility_envelope: dict[str, Any],
    correlation_inference_id: str | None = None,
) -> KnowledgeAccessRequest:
    """Minimal KAR when orientation inference fails but pipeline continues degraded."""
    orientation = CharacterOrientationAssessment(
        orientation_id=new_character_orientation_id(),
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        character_id=character_id,
        information_gaps=("What knowledge is relevant to my current situation?",),
    )
    return orientation_to_knowledge_access_request(
        orientation,
        hg_scene_id=hg_scene_id,
        request_id=new_request_id("hg-character-kar"),
        visibility_envelope=visibility_envelope,
        correlation_inference_id=correlation_inference_id,
    )

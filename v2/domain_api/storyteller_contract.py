"""Storyteller advisory cognition contracts (#32 S3a).

Orientation → KnowledgeAccessRequest → LibrarianKnowledgeBundle →
StorytellerAdvisoryPackage. Consumer wiring remains out of scope for S3a.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from .contract import AuthorityClass
from .librarian_contract import (
    BundleValidity,
    InvalidationKey,
    KnowledgeAccessRequest,
    StableReference,
)
from .retrieval_contract import EntityRef

STORYTELLER_ORIENTATION_SCHEMA = "hg_storyteller_orientation_v1"
STORYTELLER_ASSESSMENT_SCHEMA = "hg_storyteller_assessment_v1"
STORYTELLER_ADVISORY_PACKAGE_SCHEMA = "hg_storyteller_advisory_package_v1"

StorytellerTrigger = Literal["round_start", "material_commit_refresh", "follow_up_gap"]
StorytellerComputedStage = Literal["round_start", "post_commit_refresh"]
StorytellerConfidence = Literal["confirmed", "likely", "speculative"]
StorytellerDegradationLevel = Literal["none", "partial", "degraded", "skipped"]
StorytellerDegradationMode = Literal[
    "none",
    "orientation_failed",
    "librarian_unavailable",
    "librarian_degraded",
    "assessment_failed",
    "malformed_output",
    "insufficient_context",
    "host_default_fallback",
]
TemporalOrientation = Literal["current", "recent", "historical", "session", "arc"]
RecallBreadthPreference = Literal["broad", "focused"]

PROHIBITED_STORYTELLER_FIELDS = frozenset(
    {
        "next_actor",
        "next_actor_hint",
        "required_action",
        "mandated_beat",
        "required_beat",
        "dialogue",
        "narration",
        "structured_move",
        "character_state",
        "continuity_mutation",
        "plot_beat",
        "must_act",
        "must_say",
        "must_do",
        "mandatory_beat",
        "mandated_action",
    }
)


@dataclass(frozen=True)
class StorytellerOrientationAssessment:
    orientation_id: str
    hg_round_id: str
    turn_index: int
    trigger: StorytellerTrigger
    information_gaps: tuple[str, ...]
    entity_attention: tuple[EntityRef, ...] = ()
    relationship_focus: tuple[tuple[str, str | None, str | None], ...] = ()
    temporal_focus: TemporalOrientation = "current"
    breadth_preference: RecallBreadthPreference = "broad"
    requested_classes: tuple[str, ...] = ()
    narrative_hypothesis: str | None = None
    degradation: str | None = None


@dataclass(frozen=True)
class NarrativeObservation:
    text: str
    evidence_refs: tuple[StableReference, ...]
    confidence: StorytellerConfidence = "likely"
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class NarrativeTension:
    label: str
    interpretive_note: str
    evidence_refs: tuple[StableReference, ...]
    issue_refs: tuple[str, ...] = ()
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class NarrativePriority:
    focus: str
    why_it_matters: str
    evidence_refs: tuple[StableReference, ...]
    confidence: StorytellerConfidence = "likely"
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class ProgressionOpportunity:
    opportunity_label: str
    narrative_hook: str
    evidence_refs: tuple[StableReference, ...]
    confidence: StorytellerConfidence = "likely"
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class UnresolvedThread:
    thread_label: str
    neglect_risk: str
    evidence_refs: tuple[StableReference, ...]
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class UncertaintyRecord:
    topic: str
    reason: str
    confidence: StorytellerConfidence = "speculative"
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class InformationGap:
    question: str
    blocking_judgment: bool = False
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class PreservationSignal:
    """Attention hint to Librarian — not evidence, not a proposal."""

    signal_id: str
    subject_label: str
    narrative_significance_note: str
    attention_refs: tuple[StableReference, ...]
    confidence: StorytellerConfidence = "likely"
    binding_level: Literal["advisory"] = "advisory"
    authority_class: AuthorityClass = "suggestive"


@dataclass(frozen=True)
class StorytellerDegradation:
    level: StorytellerDegradationLevel
    mode: StorytellerDegradationMode
    detail: str = ""


@dataclass(frozen=True)
class AssessmentValidity:
    validity_scope: Literal["round_stable"] = "round_stable"
    bound_hg_round_id: str = ""
    bound_turn_index: int = 0
    valid_from_authoritative_snapshot_id: str = ""
    invalidation_keys: tuple[InvalidationKey, ...] = ()
    is_valid: bool = True
    invalidation_reason: str | None = None


@dataclass(frozen=True)
class StorytellerBundleRefs:
    primary_request_id: str
    primary_bundle_id: str
    follow_up_request_ids: tuple[str, ...] = ()
    bundle_validity: BundleValidity | None = None


@dataclass(frozen=True)
class StorytellerAuditRecord:
    orientation_inference_id: str | None = None
    assessment_inference_id: str | None = None
    inference_ids: tuple[str, ...] = ()
    librarian_request_ids: tuple[str, ...] = ()
    librarian_bundle_ids: tuple[str, ...] = ()
    host_validation: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StorytellerAdvisoryPackage:
    schema: str
    package_id: str
    assessment_id: str
    orientation_id: str
    hg_scene_id: str
    hg_round_id: str
    turn_index: int
    computed_at_stage: StorytellerComputedStage
    validity: AssessmentValidity
    bundle_refs: StorytellerBundleRefs
    evidence_refs: tuple[StableReference, ...]
    observations: tuple[NarrativeObservation, ...]
    active_tensions: tuple[NarrativeTension, ...]
    narrative_priorities: tuple[NarrativePriority, ...]
    progression_opportunities: tuple[ProgressionOpportunity, ...]
    unresolved_threads: tuple[UnresolvedThread, ...]
    uncertainty: tuple[UncertaintyRecord, ...]
    information_gaps: tuple[InformationGap, ...]
    degradation: StorytellerDegradation
    audit: StorytellerAuditRecord
    preservation_signals: tuple[PreservationSignal, ...] = ()


def new_orientation_id(prefix: str = "hg-storyteller-orient") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_assessment_id(prefix: str = "hg-storyteller-assess") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_package_id(prefix: str = "hg-storyteller-pkg") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _stable_ref_from_dict(data: dict[str, Any]) -> StableReference:
    return StableReference(
        ref_kind=str(data.get("ref_kind", "")),
        stable_ref=str(data.get("stable_ref", "")),
        display_hint=data.get("display_hint"),
    )


def _entity_ref_from_dict(data: dict[str, Any]) -> EntityRef:
    return EntityRef(
        ref_kind=str(data.get("ref_kind", "")),
        stable_ref=str(data.get("stable_ref", "")),
        display_hint=data.get("display_hint"),
    )


def find_prohibited_storyteller_fields(payload: Any, *, path: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            current = f"{path}.{key_text}" if path else key_text
            if key_text in PROHIBITED_STORYTELLER_FIELDS:
                violations.append(current)
            violations.extend(find_prohibited_storyteller_fields(value, path=current))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            violations.extend(find_prohibited_storyteller_fields(item, path=f"{path}[{index}]"))
    return violations


def validate_storyteller_payload(payload: Any) -> tuple[bool, tuple[str, ...]]:
    violations = find_prohibited_storyteller_fields(payload)
    return (len(violations) == 0, tuple(violations))


def _parse_evidence_refs(raw: Any) -> tuple[StableReference, ...]:
    if not isinstance(raw, list):
        return ()
    refs: list[StableReference] = []
    for item in raw:
        if isinstance(item, dict) and item.get("stable_ref"):
            refs.append(_stable_ref_from_dict(item))
    return tuple(refs)


def parse_storyteller_orientation(raw: dict[str, Any] | str) -> tuple[StorytellerOrientationAssessment | None, str | None]:
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc:
        return None, f"parse_error:{exc}"
    if not isinstance(parsed, dict):
        return None, "not_object"
    if str(parsed.get("schema", "")) != STORYTELLER_ORIENTATION_SCHEMA:
        return None, "schema_mismatch"

    violations = find_prohibited_storyteller_fields(parsed)
    if violations:
        return None, f"prohibited_fields:{','.join(violations[:5])}"

    gaps = tuple(
        str(item).strip()
        for item in (parsed.get("information_gaps") or [])
        if str(item).strip()
    )
    if not gaps:
        return None, "information_gaps_required"

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
    breadth = str(parsed.get("breadth_preference") or "broad")
    if breadth not in {"broad", "focused"}:
        breadth = "broad"
    trigger = str(parsed.get("trigger") or "round_start")
    if trigger not in {"round_start", "material_commit_refresh", "follow_up_gap"}:
        trigger = "round_start"

    return (
        StorytellerOrientationAssessment(
            orientation_id=str(parsed.get("orientation_id") or new_orientation_id()),
            hg_round_id=str(parsed.get("hg_round_id") or ""),
            turn_index=int(parsed.get("turn_index") or 0),
            trigger=trigger,  # type: ignore[arg-type]
            information_gaps=gaps,
            entity_attention=entity_attention,
            relationship_focus=relationship_focus,
            temporal_focus=temporal,  # type: ignore[arg-type]
            breadth_preference=breadth,  # type: ignore[arg-type]
            requested_classes=requested_classes,
            narrative_hypothesis=str(parsed.get("narrative_hypothesis") or "").strip() or None,
            degradation=str(parsed.get("degradation") or "").strip() or None,
        ),
        None,
    )


def orientation_to_knowledge_access_request(
    orientation: StorytellerOrientationAssessment,
    *,
    hg_scene_id: str,
    request_id: str,
    visibility_envelope: dict[str, Any],
    host_allowed_information_classes: frozenset[str],
    correlation_inference_id: str | None = None,
    parent_request_id: str | None = None,
) -> KnowledgeAccessRequest:
    from .librarian_contract import (
        BudgetExpectations,
        DegradationPreferences,
        InformationNeed,
        RelationshipFocus,
        VisibilityEnvelope,
    )

    focus_questions = tuple(orientation.information_gaps)
    entity_refs = orientation.entity_attention
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
        viewer_role=visibility_envelope.get("viewer_role", "orchestration"),  # type: ignore[arg-type]
        authority_ceiling_enforced=visibility_envelope.get("authority_ceiling_enforced", "derived"),  # type: ignore[arg-type]
        viewer_character_id=visibility_envelope.get("viewer_character_id"),
        subject_character_id=visibility_envelope.get("subject_character_id"),
        session_template_id=visibility_envelope.get("session_template_id"),
        perception_gates_ref=visibility_envelope.get("perception_gates_ref"),
        known_by_snapshot_id=visibility_envelope.get("known_by_snapshot_id"),
    )
    return KnowledgeAccessRequest(
        request_id=request_id,
        consumer_role="storyteller",
        audit_reason="storyteller_orientation",
        hg_scene_id=hg_scene_id,
        hg_round_id=orientation.hg_round_id,
        turn_index=orientation.turn_index,
        pipeline_stage="host_default",
        visibility_envelope=envelope,
        information_need=InformationNeed(
            focus_questions=focus_questions,
            entity_refs=entity_refs,
            relationship_focus=relationship_focus,
            temporal_orientation=orientation.temporal_focus,
            recall_breadth_preference=orientation.breadth_preference,
        ),
        parent_request_id=parent_request_id,
        correlation_inference_id=correlation_inference_id,
        requested_information_classes=requested,
        host_allowed_information_classes=host_allowed_information_classes,
        budget_expectations=BudgetExpectations(max_bundle_entries=32, max_bundle_chars=24000),
        degradation_preferences=DegradationPreferences(),
    )


def _parse_observations(raw: Any) -> tuple[NarrativeObservation, ...]:
    items: list[NarrativeObservation] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        items.append(
            NarrativeObservation(
                text=text,
                evidence_refs=_parse_evidence_refs(entry.get("evidence_refs")),
                confidence=str(entry.get("confidence") or "likely"),  # type: ignore[arg-type]
            )
        )
    return tuple(items)


def _parse_tensions(raw: Any) -> tuple[NarrativeTension, ...]:
    items: list[NarrativeTension] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label", "")).strip()
        note = str(entry.get("interpretive_note", "")).strip()
        if not label or not note:
            continue
        issue_refs = tuple(
            str(item).strip()
            for item in (entry.get("issue_refs") or [])
            if str(item).strip()
        )
        items.append(
            NarrativeTension(
                label=label,
                interpretive_note=note,
                issue_refs=issue_refs,
                evidence_refs=_parse_evidence_refs(entry.get("evidence_refs")),
            )
        )
    return tuple(items)


def _parse_priorities(raw: Any) -> tuple[NarrativePriority, ...]:
    items: list[NarrativePriority] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        focus = str(entry.get("focus", "")).strip()
        why = str(entry.get("why_it_matters", "")).strip()
        if not focus or not why:
            continue
        items.append(
            NarrativePriority(
                focus=focus,
                why_it_matters=why,
                evidence_refs=_parse_evidence_refs(entry.get("evidence_refs")),
                confidence=str(entry.get("confidence") or "likely"),  # type: ignore[arg-type]
            )
        )
    return tuple(items)


def _parse_opportunities(raw: Any) -> tuple[ProgressionOpportunity, ...]:
    items: list[ProgressionOpportunity] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("opportunity_label", "")).strip()
        hook = str(entry.get("narrative_hook", "")).strip()
        if not label or not hook:
            continue
        items.append(
            ProgressionOpportunity(
                opportunity_label=label,
                narrative_hook=hook,
                evidence_refs=_parse_evidence_refs(entry.get("evidence_refs")),
                confidence=str(entry.get("confidence") or "likely"),  # type: ignore[arg-type]
            )
        )
    return tuple(items)


def _parse_threads(raw: Any) -> tuple[UnresolvedThread, ...]:
    items: list[UnresolvedThread] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("thread_label", "")).strip()
        risk = str(entry.get("neglect_risk", "")).strip()
        if not label or not risk:
            continue
        items.append(
            UnresolvedThread(
                thread_label=label,
                neglect_risk=risk,
                evidence_refs=_parse_evidence_refs(entry.get("evidence_refs")),
            )
        )
    return tuple(items)


def _parse_uncertainty(raw: Any) -> tuple[UncertaintyRecord, ...]:
    items: list[UncertaintyRecord] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        topic = str(entry.get("topic", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        if not topic or not reason:
            continue
        items.append(
            UncertaintyRecord(
                topic=topic,
                reason=reason,
                confidence=str(entry.get("confidence") or "speculative"),  # type: ignore[arg-type]
            )
        )
    return tuple(items)


def _parse_information_gaps(raw: Any) -> tuple[InformationGap, ...]:
    items: list[InformationGap] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        question = str(entry.get("question", "")).strip()
        if not question:
            continue
        items.append(
            InformationGap(
                question=question,
                blocking_judgment=bool(entry.get("blocking_judgment", False)),
            )
        )
    return tuple(items)


def _parse_preservation_signals(raw: Any) -> tuple[PreservationSignal, ...]:
    items: list[PreservationSignal] = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        subject = str(entry.get("subject_label", "")).strip()
        note = str(entry.get("narrative_significance_note", "")).strip()
        attention_refs = _parse_evidence_refs(entry.get("attention_refs"))
        if not subject or not note or not attention_refs:
            continue
        if entry.get("evidence_refs") is not None:
            continue
        items.append(
            PreservationSignal(
                signal_id=str(entry.get("signal_id") or f"pres-{uuid.uuid4()}"),
                subject_label=subject,
                narrative_significance_note=note,
                attention_refs=attention_refs,
                confidence=str(entry.get("confidence") or "likely"),  # type: ignore[arg-type]
            )
        )
    return tuple(items)


def parse_storyteller_assessment(raw: dict[str, Any] | str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc:
        return None, f"parse_error:{exc}"
    if not isinstance(parsed, dict):
        return None, "not_object"
    if str(parsed.get("schema", "")) != STORYTELLER_ASSESSMENT_SCHEMA:
        return None, "schema_mismatch"

    ok, violations = validate_storyteller_payload(parsed)
    if not ok:
        return None, f"prohibited_fields:{','.join(violations[:5])}"

    return parsed, None


def build_storyteller_advisory_package(
    *,
    assessment: dict[str, Any],
    orientation: StorytellerOrientationAssessment,
    hg_scene_id: str,
    bundle_refs: StorytellerBundleRefs,
    authoritative_snapshot_id: str,
    audit: StorytellerAuditRecord,
    degradation: StorytellerDegradation | None = None,
) -> StorytellerAdvisoryPackage:
    all_evidence = _parse_evidence_refs(assessment.get("evidence_refs"))
    degradation = degradation or StorytellerDegradation(level="none", mode="none")
    validity = AssessmentValidity(
        bound_hg_round_id=orientation.hg_round_id,
        bound_turn_index=orientation.turn_index,
        valid_from_authoritative_snapshot_id=authoritative_snapshot_id,
        invalidation_keys=(
            InvalidationKey(key_kind="hg_round_id", key_value=orientation.hg_round_id),
            InvalidationKey(
                key_kind="authoritative_snapshot_id",
                key_value=authoritative_snapshot_id,
            ),
        ),
        is_valid=True,
    )
    return StorytellerAdvisoryPackage(
        schema=STORYTELLER_ADVISORY_PACKAGE_SCHEMA,
        package_id=new_package_id(),
        assessment_id=str(assessment.get("assessment_id") or new_assessment_id()),
        orientation_id=orientation.orientation_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=orientation.hg_round_id,
        turn_index=orientation.turn_index,
        computed_at_stage="round_start",
        validity=validity,
        bundle_refs=bundle_refs,
        evidence_refs=all_evidence,
        observations=_parse_observations(assessment.get("observations")),
        active_tensions=_parse_tensions(assessment.get("active_tensions")),
        narrative_priorities=_parse_priorities(assessment.get("narrative_priorities")),
        progression_opportunities=_parse_opportunities(assessment.get("progression_opportunities")),
        unresolved_threads=_parse_threads(assessment.get("unresolved_threads")),
        uncertainty=_parse_uncertainty(assessment.get("uncertainty")),
        information_gaps=_parse_information_gaps(assessment.get("information_gaps")),
        preservation_signals=_parse_preservation_signals(assessment.get("preservation_signals")),
        degradation=degradation,
        audit=audit,
    )


def invalidate_storyteller_package(
    package: StorytellerAdvisoryPackage,
    *,
    reason: str,
) -> StorytellerAdvisoryPackage:
    validity = AssessmentValidity(
        validity_scope=package.validity.validity_scope,
        bound_hg_round_id=package.validity.bound_hg_round_id,
        bound_turn_index=package.validity.bound_turn_index,
        valid_from_authoritative_snapshot_id=package.validity.valid_from_authoritative_snapshot_id,
        invalidation_keys=package.validity.invalidation_keys,
        is_valid=False,
        invalidation_reason=reason,
    )
    return StorytellerAdvisoryPackage(
        schema=package.schema,
        package_id=package.package_id,
        assessment_id=package.assessment_id,
        orientation_id=package.orientation_id,
        hg_scene_id=package.hg_scene_id,
        hg_round_id=package.hg_round_id,
        turn_index=package.turn_index,
        computed_at_stage=package.computed_at_stage,
        validity=validity,
        bundle_refs=package.bundle_refs,
        evidence_refs=package.evidence_refs,
        observations=package.observations,
        active_tensions=package.active_tensions,
        narrative_priorities=package.narrative_priorities,
        progression_opportunities=package.progression_opportunities,
        unresolved_threads=package.unresolved_threads,
        uncertainty=package.uncertainty,
        information_gaps=package.information_gaps,
        preservation_signals=package.preservation_signals,
        degradation=package.degradation,
        audit=package.audit,
    )


def advisory_package_to_dict(package: StorytellerAdvisoryPackage) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(package)


def advisory_package_from_dict(data: dict[str, Any]) -> StorytellerAdvisoryPackage:
    validity_data = data.get("validity") or {}
    validity = AssessmentValidity(
        validity_scope=validity_data.get("validity_scope", "round_stable"),  # type: ignore[arg-type]
        bound_hg_round_id=str(validity_data.get("bound_hg_round_id", "")),
        bound_turn_index=int(validity_data.get("bound_turn_index", 0)),
        valid_from_authoritative_snapshot_id=str(
            validity_data.get("valid_from_authoritative_snapshot_id", "")
        ),
        invalidation_keys=tuple(
            InvalidationKey(
                key_kind=str(item.get("key_kind", "")),
                key_value=str(item.get("key_value", "")),
            )
            for item in validity_data.get("invalidation_keys") or ()
            if isinstance(item, dict)
        ),
        is_valid=bool(validity_data.get("is_valid", True)),
        invalidation_reason=validity_data.get("invalidation_reason"),
    )
    bundle_data = data.get("bundle_refs") or {}
    bundle_refs = StorytellerBundleRefs(
        primary_request_id=str(bundle_data.get("primary_request_id", "")),
        primary_bundle_id=str(bundle_data.get("primary_bundle_id", "")),
        follow_up_request_ids=tuple(
            str(item) for item in bundle_data.get("follow_up_request_ids") or ()
        ),
        bundle_validity=None,
    )
    degradation_data = data.get("degradation") or {}
    degradation = StorytellerDegradation(
        level=str(degradation_data.get("level", "none")),  # type: ignore[arg-type]
        mode=str(degradation_data.get("mode", "none")),  # type: ignore[arg-type]
        detail=str(degradation_data.get("detail", "")),
    )
    audit_data = data.get("audit") or {}
    audit = StorytellerAuditRecord(
        orientation_inference_id=audit_data.get("orientation_inference_id"),
        assessment_inference_id=audit_data.get("assessment_inference_id"),
        inference_ids=tuple(str(item) for item in audit_data.get("inference_ids") or ()),
        librarian_request_ids=tuple(
            str(item) for item in audit_data.get("librarian_request_ids") or ()
        ),
        librarian_bundle_ids=tuple(
            str(item) for item in audit_data.get("librarian_bundle_ids") or ()
        ),
        host_validation=dict(audit_data.get("host_validation") or {}),
    )
    return StorytellerAdvisoryPackage(
        schema=str(data.get("schema", "")),
        package_id=str(data.get("package_id", "")),
        assessment_id=str(data.get("assessment_id", "")),
        orientation_id=str(data.get("orientation_id", "")),
        hg_scene_id=str(data.get("hg_scene_id", "")),
        hg_round_id=str(data.get("hg_round_id", "")),
        turn_index=int(data.get("turn_index", 0)),
        computed_at_stage=str(data.get("computed_at_stage", "round_start")),  # type: ignore[arg-type]
        validity=validity,
        bundle_refs=bundle_refs,
        evidence_refs=_parse_evidence_refs(data.get("evidence_refs")),
        observations=_parse_observations(data.get("observations")),
        active_tensions=_parse_tensions(data.get("active_tensions")),
        narrative_priorities=_parse_priorities(data.get("narrative_priorities")),
        progression_opportunities=_parse_opportunities(data.get("progression_opportunities")),
        unresolved_threads=_parse_threads(data.get("unresolved_threads")),
        uncertainty=_parse_uncertainty(data.get("uncertainty")),
        information_gaps=_parse_information_gaps(data.get("information_gaps")),
        preservation_signals=_parse_preservation_signals(data.get("preservation_signals")),
        degradation=degradation,
        audit=audit,
    )

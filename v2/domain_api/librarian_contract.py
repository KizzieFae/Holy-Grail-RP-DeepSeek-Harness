"""Librarian read-side contracts (#34 S2a).

Public request/response types for KnowledgeAccessRequest mediation through
Retrieval (#31) and authoritative projection.

Write-side grounded proposals: see ``librarian_proposal_contract.py`` (#34 S4a).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from .contract import AuthorityClass
from .retrieval_contract import ALL_INFORMATION_CLASSES, EntityRef, InformationClass

LibrarianConsumerRole = Literal[
    "storyteller",
    "character",
    "director",
    "narrator",
    "continuity_proposal",
    "host_default",
    "packaging_adapter",
]
PipelineStage = Literal["director", "character", "narrator", "post_commit", "host_default"]
ViewerRole = Literal["orchestration", "character", "narrator", "host_internal"]
RecallBreadthPreference = Literal["broad", "focused"]
TemporalOrientation = Literal["current", "recent", "historical", "session", "arc"]
SourceTier = Literal[
    "authoritative_live_continuity",
    "scene_grounding",
    "canon_anchors",
    "recent_developments",
    "committed_turn",
    "director_decision",
    "episodic_projection",
    "retrieval_candidate",
]
BundleValidityScope = Literal["stage_current", "round_stable"]
BundleDegradationLevel = Literal["none", "partial", "degraded", "unavailable"]
BundleDegradationMode = Literal[
    "none",
    "partial_sources",
    "retrieval_unavailable",
    "semantic_inference_failed",
    "deterministic_fallback",
    "provenance_incomplete",
    "budget_truncated",
    "request_malformed",
    "authoritative_only",
]
MediationMode = Literal["contextual_semantic", "deterministic_fallback", "authoritative_only"]
LIBRARIAN_MEDIATION_RESULT_SCHEMA = "hg_librarian_mediation_result_v1"
RelevanceBand = Literal["high", "medium", "low"]
InterpretiveStatus = Literal["confirmed", "likely", "speculative"]
QuestionOutcomeStatus = Literal["answered", "partial", "unanswered", "not_applicable"]
VisibilityScope = Literal[
    "character_scoped",
    "scene_orchestration",
    "orchestration_only",
    "public",
    "template_participants",
]

_AUTHORITY_ORDER = {"suggestive": 0, "derived": 1, "authoritative": 2}


@dataclass(frozen=True)
class VisibilityEnvelope:
    """Host-authoritative visibility and authority ceiling — consumer cannot widen."""

    viewer_role: ViewerRole
    authority_ceiling_enforced: AuthorityClass
    viewer_character_id: str | None = None
    subject_character_id: str | None = None
    session_template_id: str | None = None
    perception_gates_ref: str | None = None
    known_by_snapshot_id: str | None = None


@dataclass(frozen=True)
class RelationshipFocus:
    subject_ref: str
    object_ref: str | None = None
    relationship_kind: str | None = None


@dataclass(frozen=True)
class InformationNeed:
    """Consumer semantic intent — maps to #31 Layer B, not hard access."""

    focus_questions: tuple[str, ...]
    topics: tuple[str, ...] = ()
    entity_refs: tuple[EntityRef, ...] = ()
    relationship_focus: tuple[RelationshipFocus, ...] = ()
    temporal_orientation: TemporalOrientation | None = None
    recall_breadth_preference: RecallBreadthPreference = "broad"


@dataclass(frozen=True)
class BudgetExpectations:
    max_bundle_entries: int = 32
    max_bundle_chars: int = 24000
    max_synthesis_entries: int = 4


@dataclass(frozen=True)
class DegradationPreferences:
    allow_partial_sources: bool = True
    allow_heuristic_fallback: bool = True
    require_provenance_complete: bool = False


@dataclass(frozen=True)
class KnowledgeAccessRequest:
    """Public Librarian read request — Host assembles authoritative envelope."""

    request_id: str
    consumer_role: LibrarianConsumerRole
    audit_reason: str
    hg_scene_id: str
    hg_round_id: str
    turn_index: int
    pipeline_stage: PipelineStage
    visibility_envelope: VisibilityEnvelope
    information_need: InformationNeed
    parent_request_id: str | None = None
    correlation_inference_id: str | None = None
    consumer_instance_id: str | None = None
    domain_commit_id: str | None = None
    requested_information_classes: frozenset[str] | None = None
    authority_ceiling: AuthorityClass | None = None
    exclude_source_tiers: frozenset[str] = frozenset()
    budget_expectations: BudgetExpectations = BudgetExpectations()
    degradation_preferences: DegradationPreferences = DegradationPreferences()
    host_allowed_information_classes: frozenset[str] = ALL_INFORMATION_CLASSES


@dataclass(frozen=True)
class StableReference:
    ref_kind: str
    stable_ref: str
    display_hint: str | None = None


@dataclass(frozen=True)
class LibrarianAnnotation:
    relevance_rank: int
    relevance_band: RelevanceBand | None = None
    salience_note: str | None = None
    interpretive_status: InterpretiveStatus | None = None
    answers_focus_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SynthesisMeta:
    synthesis_kind: Literal["summary", "connection_bridge", "consolidated_fact_view"]
    source_entry_refs: tuple[StableReference, ...]
    synthesis_authority: Literal["suggestive"] = "suggestive"
    interpretive_status: InterpretiveStatus = "likely"


@dataclass(frozen=True)
class BundleEntryUncertainty:
    reason: str
    conflict_with_authoritative: StableReference | None = None


@dataclass(frozen=True)
class LibrarianBundleEntry:
    entry_id: str
    ref: StableReference
    content: str
    information_class: InformationClass | str
    source_tier: SourceTier | str
    authority_class: AuthorityClass
    visibility_scope: VisibilityScope | str
    provenance: dict[str, Any]
    temporal_relationship: TemporalOrientation | str
    librarian_annotation: LibrarianAnnotation
    temporal_anchor_turn: int | None = None
    temporal_anchor_commit_id: str | None = None
    uncertainty: BundleEntryUncertainty | None = None
    synthesis_meta: SynthesisMeta | None = None
    structured_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class BundleConnection:
    connection_id: str
    edge_kind: Literal["supports", "contradicts", "same_entity", "causal_candidate"]
    from_entry_id: str
    to_entry_id: str
    note: str | None = None


@dataclass(frozen=True)
class QuestionOutcome:
    question: str
    status: QuestionOutcomeStatus
    supporting_entry_ids: tuple[str, ...] = ()
    note: str | None = None


@dataclass(frozen=True)
class RequestSatisfactionSummary:
    focus_questions: tuple[QuestionOutcome, ...]
    omitted_classes: tuple[tuple[str, str], ...] = ()
    truncated: bool = False
    truncation_reason: Literal["budget", "policy", "source_failure"] | None = None


@dataclass(frozen=True)
class InvalidationKey:
    key_kind: str
    key_value: str


@dataclass(frozen=True)
class BundleValidity:
    validity_scope: BundleValidityScope
    bound_hg_round_id: str
    bound_turn_index: int
    bound_pipeline_stage: PipelineStage | None
    valid_from_authoritative_snapshot_id: str
    invalidation_keys: tuple[InvalidationKey, ...] = ()
    bound_domain_commit_id: str | None = None


@dataclass(frozen=True)
class SourceStatus:
    source_tier: str
    status: Literal["ok", "degraded", "unavailable", "skipped"]
    detail: str = ""


@dataclass(frozen=True)
class SourceDiagnostics:
    consulted_tiers: tuple[str, ...]
    omitted_tiers: tuple[str, ...]
    per_source: tuple[SourceStatus, ...] = ()


@dataclass(frozen=True)
class BudgetAccounting:
    entries_returned: int
    entries_considered: int
    chars_returned: int
    chars_budget: int
    entries_truncated: int = 0


@dataclass(frozen=True)
class BundleDegradation:
    level: BundleDegradationLevel
    mode: BundleDegradationMode
    per_source: tuple[SourceStatus, ...] = ()
    deterministic_fallback_used: bool = False


@dataclass(frozen=True)
class MediationCatalogItem:
    """Bounded item supplied to DSH Librarian inference."""

    source_id: str
    source_kind: str
    stable_ref: str
    content: str
    information_class: str
    authority_class: AuthorityClass
    visibility_scope: str
    source_tier: str
    provenance: dict[str, Any]
    temporal_relationship: str = "recent"


@dataclass(frozen=True)
class MediationSelectionItem:
    source_id: str
    relevance_rank: int
    relevance_band: RelevanceBand | None = None
    salience_note: str | None = None
    interpretive_status: InterpretiveStatus | None = None
    answers_focus_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class MediationSynthesisItem:
    synthesis_id: str
    synthesis_kind: Literal["summary", "connection_bridge", "consolidated_fact_view"]
    content: str
    source_ids: tuple[str, ...]
    interpretive_status: InterpretiveStatus = "likely"


@dataclass(frozen=True)
class MediationConnectionItem:
    connection_id: str
    edge_kind: Literal["supports", "contradicts", "same_entity", "causal_candidate"]
    from_source_id: str
    to_source_id: str
    note: str | None = None


@dataclass(frozen=True)
class LibrarianMediationResult:
    schema: str
    selected_items: tuple[MediationSelectionItem, ...]
    connections: tuple[MediationConnectionItem, ...] = ()
    synthesis_entries: tuple[MediationSynthesisItem, ...] = ()
    focus_question_outcomes: tuple[QuestionOutcome, ...] = ()


@dataclass(frozen=True)
class HostMediationValidation:
    accepted: bool
    reason: str
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalDispositionSnapshot:
    """Observational Retrieval boundary at prepare time (#45)."""

    request_id: str | None
    candidate_ids_returned: tuple[str, ...]
    diagnostics: dict[str, Any]
    retrieval_omitted: bool = False


@dataclass(frozen=True)
class LibrarianMediationPrepareResponse:
    manifest_id: str
    inference_id: str
    request_id: str
    hg_scene_id: str
    hg_round_id: str
    contributions: tuple[Any, ...]
    mediation_catalog: tuple[MediationCatalogItem, ...]
    retrieval_request_ids: tuple[str, ...]
    candidate_ids_supplied: tuple[str, ...]
    authoritative_snapshot_id: str
    retrieval_disposition: tuple[RetrievalDispositionSnapshot, ...] = ()


@dataclass(frozen=True)
class BundleAudit:
    bundle_hash: str
    retrieval_request_ids: tuple[str, ...]
    candidate_ids_considered: tuple[str, ...]
    original_request_id: str
    mediation_mode: MediationMode
    mediation_strategy: str
    inference_id: str | None = None
    host_validation: HostMediationValidation | None = None
    fallback_reason: str | None = None
    structured_mediation_evidence: dict[str, Any] | None = None


@dataclass(frozen=True)
class LibrarianKnowledgeBundle:
    bundle_id: str
    request_id: str
    consumer_role: LibrarianConsumerRole
    pipeline_stage: PipelineStage
    hg_round_id: str
    turn_index: int
    mediation_mode: MediationMode
    validity: BundleValidity
    degradation: BundleDegradation
    satisfaction: RequestSatisfactionSummary
    entries: tuple[LibrarianBundleEntry, ...]
    budget_accounting: BudgetAccounting
    source_diagnostics: SourceDiagnostics
    audit: BundleAudit
    connections: tuple[BundleConnection, ...] = ()


def new_request_id(prefix: str = "hg-librarian-req") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_bundle_id(prefix: str = "hg-librarian-bundle") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _authority_rank(value: AuthorityClass) -> int:
    return _AUTHORITY_ORDER.get(value, -1)


def validate_knowledge_access_request(request: KnowledgeAccessRequest) -> None:
    if not str(request.request_id or "").strip():
        raise ValueError("request_id is required")
    if not str(request.hg_scene_id or "").strip():
        raise ValueError("hg_scene_id is required")
    if not str(request.hg_round_id or "").strip():
        raise ValueError("hg_round_id is required")
    if request.turn_index < 0:
        raise ValueError("turn_index must be non-negative")
    if not request.information_need.focus_questions:
        raise ValueError("information_need.focus_questions must be non-empty")
    if request.pipeline_stage == "post_commit" and not str(request.domain_commit_id or "").strip():
        raise ValueError("domain_commit_id is required when pipeline_stage=post_commit")

    envelope_ceiling = request.visibility_envelope.authority_ceiling_enforced
    if request.authority_ceiling is not None:
        if _authority_rank(request.authority_ceiling) > _authority_rank(envelope_ceiling):
            raise ValueError(
                "authority_ceiling cannot exceed visibility_envelope.authority_ceiling_enforced"
            )

    if request.requested_information_classes is not None:
        unknown = set(request.requested_information_classes) - ALL_INFORMATION_CLASSES
        if unknown:
            raise ValueError(f"unknown information_class in request filter: {sorted(unknown)}")
        disallowed = set(request.requested_information_classes) - set(
            request.host_allowed_information_classes
        )
        if disallowed:
            raise ValueError(
                "requested_information_classes cannot widen host_allowed_information_classes"
            )

    budget = request.budget_expectations
    if budget.max_bundle_entries <= 0:
        raise ValueError("budget_expectations.max_bundle_entries must be positive")
    if budget.max_bundle_chars <= 0:
        raise ValueError("budget_expectations.max_bundle_chars must be positive")


def compute_bundle_hash(bundle_payload: dict[str, Any]) -> str:
    encoded = json.dumps(bundle_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def knowledge_access_request_from_dict(data: dict[str, Any]) -> KnowledgeAccessRequest:
    envelope_raw = dict(data.get("visibility_envelope") or {})
    need_raw = dict(data.get("information_need") or {})
    budget_raw = dict(data.get("budget_expectations") or {})
    degrade_raw = dict(data.get("degradation_preferences") or {})
    entity_refs = tuple(
        EntityRef(
            ref_kind=str(item.get("ref_kind", "")),
            stable_ref=str(item.get("stable_ref", "")),
            display_hint=item.get("display_hint"),
        )
        for item in (need_raw.get("entity_refs") or [])
        if isinstance(item, dict)
    )
    relationship_focus = tuple(
        RelationshipFocus(
            subject_ref=str(item.get("subject_ref", "")),
            object_ref=item.get("object_ref"),
            relationship_kind=item.get("relationship_kind"),
        )
        for item in (need_raw.get("relationship_focus") or [])
        if isinstance(item, dict)
    )
    allowed_raw = data.get("host_allowed_information_classes")
    allowed = (
        frozenset(str(item) for item in allowed_raw)
        if isinstance(allowed_raw, list)
        else ALL_INFORMATION_CLASSES
    )
    requested_raw = data.get("requested_information_classes")
    requested = (
        frozenset(str(item) for item in requested_raw)
        if isinstance(requested_raw, list)
        else None
    )
    exclude_raw = data.get("exclude_source_tiers")
    exclude = frozenset(str(item) for item in exclude_raw) if isinstance(exclude_raw, list) else frozenset()
    return KnowledgeAccessRequest(
        request_id=str(data["request_id"]),
        consumer_role=data["consumer_role"],  # type: ignore[arg-type]
        audit_reason=str(data.get("audit_reason", "")),
        hg_scene_id=str(data["hg_scene_id"]),
        hg_round_id=str(data["hg_round_id"]),
        turn_index=int(data.get("turn_index", 0)),
        pipeline_stage=data.get("pipeline_stage", "director"),  # type: ignore[arg-type]
        visibility_envelope=VisibilityEnvelope(
            viewer_role=envelope_raw.get("viewer_role", "orchestration"),  # type: ignore[arg-type]
            authority_ceiling_enforced=envelope_raw.get("authority_ceiling_enforced", "derived"),  # type: ignore[arg-type]
            viewer_character_id=envelope_raw.get("viewer_character_id"),
            subject_character_id=envelope_raw.get("subject_character_id"),
            session_template_id=envelope_raw.get("session_template_id"),
            perception_gates_ref=envelope_raw.get("perception_gates_ref"),
            known_by_snapshot_id=envelope_raw.get("known_by_snapshot_id"),
        ),
        information_need=InformationNeed(
            focus_questions=tuple(str(item) for item in (need_raw.get("focus_questions") or []) if str(item).strip()),
            topics=tuple(str(item) for item in (need_raw.get("topics") or []) if str(item).strip()),
            entity_refs=entity_refs,
            relationship_focus=relationship_focus,
            temporal_orientation=need_raw.get("temporal_orientation"),
            recall_breadth_preference=need_raw.get("recall_breadth_preference", "broad"),  # type: ignore[arg-type]
        ),
        parent_request_id=data.get("parent_request_id"),
        correlation_inference_id=data.get("correlation_inference_id"),
        consumer_instance_id=data.get("consumer_instance_id"),
        domain_commit_id=data.get("domain_commit_id"),
        requested_information_classes=requested,
        authority_ceiling=data.get("authority_ceiling"),
        exclude_source_tiers=exclude,
        budget_expectations=BudgetExpectations(
            max_bundle_entries=int(budget_raw.get("max_bundle_entries", 32)),
            max_bundle_chars=int(budget_raw.get("max_bundle_chars", 24000)),
            max_synthesis_entries=int(budget_raw.get("max_synthesis_entries", 4)),
        ),
        degradation_preferences=DegradationPreferences(
            allow_partial_sources=bool(degrade_raw.get("allow_partial_sources", True)),
            allow_heuristic_fallback=bool(degrade_raw.get("allow_heuristic_fallback", True)),
            require_provenance_complete=bool(degrade_raw.get("require_provenance_complete", False)),
        ),
        host_allowed_information_classes=allowed,
    )

"""Librarian write-side proposal contracts (#34 S4a).

Grounded LibrarianSemanticProposal batches for post-commit contextual interpretation.
Continuity remains exclusive durable-state authority; proposals never commit truth directly.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from .contract import AuthorityClass
from .librarian_contract import VisibilityEnvelope

LIBRARIAN_PROPOSAL_RESULT_SCHEMA = "hg_librarian_proposal_result_v1"
LIBRARIAN_PROPOSAL_ORIGIN = "librarian"

ProposalKind = Literal[
    "consequence_meaning",
    "information_salience",
    "relationship_development_hypothesis",
    "issue_tension_pressure",
    "knowledge_revelation_significance",
    "persistence_promotion_candidate",
    "knowledge_propagation_augmentation",
]
EvidenceKind = Literal[
    "committed_move",
    "continuity_state",
    "public_event",
    "scene_state",
    "memory_record",
    "knowledge_record",
    "bundle_entry",
]
ProposalConfidence = Literal["confirmed", "likely", "speculative"]
ProposalValidationOutcome = Literal["accept", "reject"]
ProposalBatchDegradationMode = Literal[
    "none",
    "inference_failed",
    "host_validation_failed",
    "continuity_rejected_all",
    "malformed_result",
    "unavailable",
]

S4A_ACTIVE_PROPOSAL_KINDS: frozenset[str] = frozenset(
    {
        "consequence_meaning",
        "information_salience",
    }
)

_CONSEQUENCE_TAGS = frozenset(
    {
        "advancement",
        "complication",
        "revelation",
        "resolution_candidate",
        "relationship_shift",
        "tension_escalation",
        "tension_release",
    }
)
_SALIENCE_LEVELS = frozenset({"minor", "major", "pivotal"})


@dataclass(frozen=True)
class EvidenceAnchor:
    anchor_id: str
    evidence_kind: EvidenceKind | str
    anchor_path: str | None = None
    anchor_commit_id: str | None = None


@dataclass(frozen=True)
class ProposalCommitBinding:
    domain_commit_id: str
    hg_round_id: str
    turn_index: int
    pipeline_stage: Literal["post_commit"] = "post_commit"


@dataclass(frozen=True)
class ProposalProvenance:
    librarian_inference_id: str
    source_bundle_id: str | None = None


@dataclass(frozen=True)
class LibrarianSemanticProposal:
    proposal_id: str
    proposal_batch_id: str
    proposal_origin: Literal["librarian"]
    proposal_kind: ProposalKind | str
    evidence_anchors: tuple[EvidenceAnchor, ...]
    derivation_summary: str
    confidence: ProposalConfidence
    proposed_payload: dict[str, Any]
    commit_binding: ProposalCommitBinding
    provenance: ProposalProvenance
    affected_entities: tuple[str, ...] = ()
    affected_state_classes: tuple[str, ...] = ()
    validation_outcome: ProposalValidationOutcome | None = None
    rejection_reason_code: str | None = None


@dataclass(frozen=True)
class ProposalEvidenceCatalogItem:
    """Bounded evidence supplied to DSH Librarian proposal inference."""

    anchor_id: str
    evidence_kind: EvidenceKind | str
    stable_ref: str
    authority_class: AuthorityClass
    visibility_scope: str
    content: str
    anchor_commit_id: str | None = None
    anchor_path: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LibrarianProposalContextRequest:
    request_id: str
    hg_scene_id: str
    hg_round_id: str
    turn_index: int
    domain_commit_id: str
    visibility_envelope: VisibilityEnvelope
    librarian_inference_id: str
    audit_reason: str = "post_commit_semantic_interpretation"


@dataclass(frozen=True)
class LibrarianProposalPrepareResponse:
    manifest_id: str
    inference_id: str
    request_id: str
    hg_scene_id: str
    hg_round_id: str
    domain_commit_id: str
    contributions: tuple[Any, ...]
    evidence_catalog: tuple[ProposalEvidenceCatalogItem, ...]
    authoritative_snapshot_id: str


@dataclass(frozen=True)
class HostProposalItemValidation:
    proposal_id: str
    accepted: bool
    reason: str
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class HostProposalBatchValidation:
    accepted: bool
    reason: str
    item_results: tuple[HostProposalItemValidation, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContinuityProposalItemDecision:
    proposal_id: str
    outcome: ProposalValidationOutcome
    reason_code: str = ""
    reason_detail: str = ""
    durable_mutation_applied: bool = False


@dataclass(frozen=True)
class ContinuityProposalBatchDecision:
    batch_id: str
    domain_commit_id: str
    item_decisions: tuple[ContinuityProposalItemDecision, ...]
    accepted_count: int
    rejected_count: int


@dataclass(frozen=True)
class ProposalBatchAudit:
    batch_id: str
    batch_hash: str
    request_id: str
    domain_commit_id: str
    librarian_inference_id: str
    host_validation: HostProposalBatchValidation
    continuity_decision: ContinuityProposalBatchDecision | None
    degradation_mode: ProposalBatchDegradationMode
    proposals_considered: tuple[str, ...] = ()


@dataclass(frozen=True)
class LibrarianProposalBatchResult:
    batch_id: str
    request_id: str
    domain_commit_id: str
    proposals: tuple[LibrarianSemanticProposal, ...]
    host_validation: HostProposalBatchValidation
    continuity_decision: ContinuityProposalBatchDecision | None
    audit: ProposalBatchAudit
    degradation_mode: ProposalBatchDegradationMode


def new_proposal_request_id(prefix: str = "hg-librarian-prop-req") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_proposal_batch_id(prefix: str = "hg-librarian-prop-batch") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_proposal_id(prefix: str = "hg-librarian-prop") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def compute_proposal_batch_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def validate_proposal_payload_schema(
    proposal_kind: str,
    payload: dict[str, Any],
) -> tuple[bool, str, tuple[str, ...]]:
    if proposal_kind not in S4A_ACTIVE_PROPOSAL_KINDS:
        return False, f"unsupported_proposal_kind:{proposal_kind}", ("invalid_proposal_kind",)
    if payload.get("manufactured_fact"):
        return False, "manufactured_fact_ungrounded", ("manufactured_fact_ungrounded",)
    if proposal_kind == "consequence_meaning":
        tags = payload.get("tags")
        if not isinstance(tags, list) or not tags:
            return False, "consequence_meaning requires non-empty tags", ("invalid_payload_schema",)
        unknown = [str(t) for t in tags if str(t) not in _CONSEQUENCE_TAGS]
        if unknown:
            return False, f"unknown_consequence_tags:{unknown}", ("invalid_payload_schema",)
        if payload.get("authority_class") == "authoritative":
            return False, "authority_elevation_attempt", ("authority_elevation_attempt",)
        return True, "", ()
    if proposal_kind == "information_salience":
        subject = str(payload.get("subject_ref", "") or "").strip()
        level = str(payload.get("salience_level", "") or "").strip()
        if not subject or level not in _SALIENCE_LEVELS:
            return False, "information_salience requires subject_ref and legal salience_level", (
                "invalid_payload_schema",
            )
        if payload.get("authority_class") == "authoritative":
            return False, "authority_elevation_attempt", ("authority_elevation_attempt",)
        return True, "", ()
    return False, f"unsupported_proposal_kind:{proposal_kind}", ("invalid_proposal_kind",)


def proposal_context_request_from_dict(data: dict[str, Any]) -> LibrarianProposalContextRequest:
    envelope_raw = dict(data.get("visibility_envelope") or {})
    return LibrarianProposalContextRequest(
        request_id=str(data.get("request_id") or new_proposal_request_id()),
        hg_scene_id=str(data["hg_scene_id"]),
        hg_round_id=str(data["hg_round_id"]),
        turn_index=int(data.get("turn_index", 0)),
        domain_commit_id=str(data["domain_commit_id"]),
        visibility_envelope=VisibilityEnvelope(
            viewer_role=envelope_raw.get("viewer_role", "host_internal"),  # type: ignore[arg-type]
            authority_ceiling_enforced=envelope_raw.get("authority_ceiling_enforced", "derived"),  # type: ignore[arg-type]
            viewer_character_id=envelope_raw.get("viewer_character_id"),
            subject_character_id=envelope_raw.get("subject_character_id"),
            session_template_id=envelope_raw.get("session_template_id"),
            perception_gates_ref=envelope_raw.get("perception_gates_ref"),
            known_by_snapshot_id=envelope_raw.get("known_by_snapshot_id"),
        ),
        librarian_inference_id=str(data.get("librarian_inference_id") or data.get("inference_id") or ""),
        audit_reason=str(data.get("audit_reason") or "post_commit_semantic_interpretation"),
    )

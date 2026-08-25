"""Continuity validation boundary for Librarian semantic proposals (#34 S4a).

Non-fatal accept/reject decisions. S4a proves the proposal seam without migrating
existing heuristic-driven Continuity behavior or applying durable mutations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain_api.librarian_proposal_contract import (
    ContinuityProposalBatchDecision,
    ContinuityProposalItemDecision,
    LibrarianSemanticProposal,
    validate_proposal_payload_schema,
)

REASON_ACCEPTED = "accepted"
REASON_HOST_REJECTED = "host_rejected"
REASON_MISSING_ANCHORS = "missing_evidence_anchors"
REASON_UNKNOWN_ANCHOR = "unknown_evidence_anchor"
REASON_COMMIT_MISMATCH = "commit_binding_mismatch"
REASON_VISIBILITY_VIOLATION = "visibility_authority_violation"
REASON_AUTHORITY_ELEVATION = "authority_elevation_attempt"
REASON_MANUFACTURED_FACT = "manufactured_fact_ungrounded"
REASON_INVALID_KIND = "invalid_proposal_kind"
REASON_INVALID_PAYLOAD = "invalid_payload_schema"
REASON_PRESERVATION_SIGNAL = "preservation_signal_not_evidence"


@dataclass(frozen=True)
class ContinuityEvidenceClosure:
    domain_commit_id: str
    anchor_ids: frozenset[str]
    authoritative_anchor_ids: frozenset[str]
    visibility_scopes: dict[str, str]


def build_evidence_closure(
    *,
    domain_commit_id: str,
    catalog_anchor_ids: tuple[str, ...],
    catalog_visibility: dict[str, str],
    catalog_authority: dict[str, str],
) -> ContinuityEvidenceClosure:
    authoritative = frozenset(
        anchor_id
        for anchor_id in catalog_anchor_ids
        if catalog_authority.get(anchor_id) == "authoritative"
    )
    return ContinuityEvidenceClosure(
        domain_commit_id=domain_commit_id,
        anchor_ids=frozenset(catalog_anchor_ids),
        authoritative_anchor_ids=authoritative,
        visibility_scopes=dict(catalog_visibility),
    )


def _requires_authoritative_anchor(proposal_kind: str) -> bool:
    return proposal_kind not in {
        "persistence_promotion_candidate",
        "knowledge_propagation_augmentation",
    }


def evaluate_librarian_proposal_continuity(
    proposal: LibrarianSemanticProposal,
    *,
    closure: ContinuityEvidenceClosure,
    host_accepted: bool,
) -> ContinuityProposalItemDecision:
    if not host_accepted:
        return ContinuityProposalItemDecision(
            proposal_id=proposal.proposal_id,
            outcome="reject",
            reason_code=REASON_HOST_REJECTED,
            reason_detail="host_validation_failed",
            durable_mutation_applied=False,
        )

    binding = proposal.commit_binding
    if binding.domain_commit_id != closure.domain_commit_id:
        return ContinuityProposalItemDecision(
            proposal_id=proposal.proposal_id,
            outcome="reject",
            reason_code=REASON_COMMIT_MISMATCH,
            reason_detail="proposal commit_binding does not match closure",
            durable_mutation_applied=False,
        )

    if not proposal.evidence_anchors:
        return ContinuityProposalItemDecision(
            proposal_id=proposal.proposal_id,
            outcome="reject",
            reason_code=REASON_MISSING_ANCHORS,
            durable_mutation_applied=False,
        )

    anchor_kinds = [str(a.evidence_kind) for a in proposal.evidence_anchors]
    if any(kind == "preservation_signal" for kind in anchor_kinds):
        return ContinuityProposalItemDecision(
            proposal_id=proposal.proposal_id,
            outcome="reject",
            reason_code=REASON_PRESERVATION_SIGNAL,
            durable_mutation_applied=False,
        )

    for anchor in proposal.evidence_anchors:
        if anchor.anchor_id not in closure.anchor_ids:
            return ContinuityProposalItemDecision(
                proposal_id=proposal.proposal_id,
                outcome="reject",
                reason_code=REASON_UNKNOWN_ANCHOR,
                reason_detail=anchor.anchor_id,
                durable_mutation_applied=False,
            )
        scope = closure.visibility_scopes.get(anchor.anchor_id, "")
        if scope == "orchestration_only" and proposal.proposal_kind in {
            "knowledge_revelation_significance",
            "knowledge_propagation_augmentation",
        }:
            return ContinuityProposalItemDecision(
                proposal_id=proposal.proposal_id,
                outcome="reject",
                reason_code=REASON_VISIBILITY_VIOLATION,
                durable_mutation_applied=False,
            )

    if _requires_authoritative_anchor(str(proposal.proposal_kind)):
        if not any(
            anchor.anchor_id in closure.authoritative_anchor_ids
            for anchor in proposal.evidence_anchors
        ):
            return ContinuityProposalItemDecision(
                proposal_id=proposal.proposal_id,
                outcome="reject",
                reason_code=REASON_VISIBILITY_VIOLATION,
                reason_detail="requires authoritative anchor in commit closure",
                durable_mutation_applied=False,
            )

    ok, detail, _codes = validate_proposal_payload_schema(
        str(proposal.proposal_kind),
        proposal.proposed_payload,
    )
    if not ok:
        code = REASON_AUTHORITY_ELEVATION if "authority_elevation" in detail else REASON_INVALID_PAYLOAD
        if "unsupported_proposal_kind" in detail:
            code = REASON_INVALID_KIND
        if "manufactured" in detail:
            code = REASON_MANUFACTURED_FACT
        return ContinuityProposalItemDecision(
            proposal_id=proposal.proposal_id,
            outcome="reject",
            reason_code=code,
            reason_detail=detail,
            durable_mutation_applied=False,
        )

    if proposal.proposed_payload.get("manufactured_fact"):
        return ContinuityProposalItemDecision(
            proposal_id=proposal.proposal_id,
            outcome="reject",
            reason_code=REASON_MANUFACTURED_FACT,
            durable_mutation_applied=False,
        )

    return ContinuityProposalItemDecision(
        proposal_id=proposal.proposal_id,
        outcome="accept",
        reason_code=REASON_ACCEPTED,
        reason_detail="proposal passed S4a continuity validation boundary",
        durable_mutation_applied=False,
    )


def evaluate_librarian_proposal_batch(
    proposals: tuple[LibrarianSemanticProposal, ...],
    *,
    closure: ContinuityEvidenceClosure,
    host_accepted_by_id: dict[str, bool],
    batch_id: str,
) -> ContinuityProposalBatchDecision:
    decisions: list[ContinuityProposalItemDecision] = []
    accepted = 0
    rejected = 0
    for proposal in proposals:
        decision = evaluate_librarian_proposal_continuity(
            proposal,
            closure=closure,
            host_accepted=host_accepted_by_id.get(proposal.proposal_id, False),
        )
        decisions.append(decision)
        if decision.outcome == "accept":
            accepted += 1
        else:
            rejected += 1
    return ContinuityProposalBatchDecision(
        batch_id=batch_id,
        domain_commit_id=closure.domain_commit_id,
        item_decisions=tuple(decisions),
        accepted_count=accepted,
        rejected_count=rejected,
    )


def librarian_proposal_audit_metadata(
    *,
    batch_id: str,
    domain_commit_id: str,
    librarian_inference_id: str,
    host_validation: Any,
    continuity_decision: ContinuityProposalBatchDecision | None,
) -> dict[str, Any]:
    return {
        "librarian_proposal_batch_id": batch_id,
        "librarian_proposal_domain_commit_id": domain_commit_id,
        "librarian_inference_id": librarian_inference_id,
        "librarian_proposal_host_accepted": bool(getattr(host_validation, "accepted", False)),
        "librarian_proposal_host_rejection_codes": list(
            getattr(host_validation, "rejection_codes", ()) or ()
        ),
        "librarian_proposal_continuity_accepted_count": (
            continuity_decision.accepted_count if continuity_decision else 0
        ),
        "librarian_proposal_continuity_rejected_count": (
            continuity_decision.rejected_count if continuity_decision else 0
        ),
        "librarian_proposal_durable_mutation_applied": False,
    }

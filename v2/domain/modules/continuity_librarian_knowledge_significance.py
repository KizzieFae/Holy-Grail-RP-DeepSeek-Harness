"""S4b apply path for knowledge_revelation_significance (#34).

Writes per-character semantic significance annotations onto already-grounded
PublicEvent records. Does not mutate known_by or factual knowledge authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domain_api.librarian_proposal_contract import (
    ContinuityProposalBatchDecision,
    ContinuityProposalItemDecision,
    LibrarianSemanticProposal,
)

REASON_UNKNOWN_EVENT = "unknown_event_reference"
REASON_MISSING_SUBJECT = "missing_subject_character"
REASON_SUBJECT_NOT_KNOWER = "subject_not_in_known_by"
REASON_SIGNIFICANCE_CONFLICT = "significance_conflict"
REASON_ALREADY_APPLIED = "already_applied"
REASON_EQUAL_RANK_UNCHANGED = "equal_rank_unchanged"

_SIGNIFICANCE_RANK = {"minor": 0, "major": 1, "pivotal": 2}


@dataclass(frozen=True)
class KnowledgeSignificanceApplyResult:
    proposal_id: str
    event_id: str
    subject_character: str
    applied: bool
    idempotent: bool
    prior_annotation: dict[str, Any] | None
    final_annotation: dict[str, Any] | None
    reason_code: str = ""


def _find_event(manager: Any, event_ref: str, *, turn_index: int | None) -> Any | None:
    ref = str(event_ref or "").strip()
    if not ref:
        return None
    for event in getattr(manager, "public_events", []) or []:
        if str(getattr(event, "event_id", "")) == ref:
            if turn_index is not None and getattr(event, "turn_index", None) not in (
                None,
                turn_index,
            ):
                continue
            return event
        stable = f"event:{getattr(event, 'event_id', '')}"
        if ref == stable:
            if turn_index is not None and getattr(event, "turn_index", None) not in (
                None,
                turn_index,
            ):
                continue
            return event
    return None


def _annotations_map(event: Any) -> dict[str, dict[str, Any]]:
    raw = getattr(event, "revelation_significance_by_character", None)
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): dict(value)
        for key, value in raw.items()
        if str(key).strip() and isinstance(value, dict)
    }


def _annotation_rank(annotation: dict[str, Any] | None) -> int:
    if not annotation:
        return -1
    level = str(annotation.get("revelation_significance_level", "") or "").strip()
    return _SIGNIFICANCE_RANK.get(level, -1)


def _build_annotation(
    proposal: LibrarianSemanticProposal,
    *,
    subject: str,
    level: str,
    note: str | None,
) -> dict[str, Any]:
    return {
        "revelation_significance_level": level,
        "annotation_note": note,
        "subject_character": subject,
        "proposal_id": proposal.proposal_id,
        "proposal_batch_id": proposal.proposal_batch_id,
        "domain_commit_id": proposal.commit_binding.domain_commit_id,
        "librarian_inference_id": proposal.provenance.librarian_inference_id,
        "derivation_summary": proposal.derivation_summary,
        "confidence": proposal.confidence,
    }


def apply_knowledge_revelation_significance(
    manager: Any,
    proposal: LibrarianSemanticProposal,
) -> KnowledgeSignificanceApplyResult:
    payload = dict(proposal.proposed_payload or {})
    event_ref = str(payload.get("event_ref", "") or "").strip()
    subject = str(payload.get("subject_character", "") or "").strip()
    level = str(payload.get("revelation_significance_level", "") or "").strip()
    note = str(payload.get("annotation_note", "") or "").strip() or None

    if not subject:
        return KnowledgeSignificanceApplyResult(
            proposal_id=proposal.proposal_id,
            event_id=event_ref,
            subject_character="",
            applied=False,
            idempotent=False,
            prior_annotation=None,
            final_annotation=None,
            reason_code=REASON_MISSING_SUBJECT,
        )

    event = _find_event(
        manager,
        event_ref,
        turn_index=proposal.commit_binding.turn_index,
    )
    if event is None:
        return KnowledgeSignificanceApplyResult(
            proposal_id=proposal.proposal_id,
            event_id=event_ref,
            subject_character=subject,
            applied=False,
            idempotent=False,
            prior_annotation=None,
            final_annotation=None,
            reason_code=REASON_UNKNOWN_EVENT,
        )

    if subject not in list(getattr(event, "known_by", []) or []):
        return KnowledgeSignificanceApplyResult(
            proposal_id=proposal.proposal_id,
            event_id=str(event.event_id),
            subject_character=subject,
            applied=False,
            idempotent=False,
            prior_annotation=_annotations_map(event).get(subject),
            final_annotation=None,
            reason_code=REASON_SUBJECT_NOT_KNOWER,
        )

    annotations = _annotations_map(event)
    prior = dict(annotations.get(subject, {}) or {}) or None

    if prior and str(prior.get("proposal_id", "")) == proposal.proposal_id:
        return KnowledgeSignificanceApplyResult(
            proposal_id=proposal.proposal_id,
            event_id=str(event.event_id),
            subject_character=subject,
            applied=True,
            idempotent=True,
            prior_annotation=prior,
            final_annotation=prior,
            reason_code=REASON_ALREADY_APPLIED,
        )

    new_rank = _SIGNIFICANCE_RANK.get(level, -1)
    prior_rank = _annotation_rank(prior)
    if prior is not None and new_rank < prior_rank:
        return KnowledgeSignificanceApplyResult(
            proposal_id=proposal.proposal_id,
            event_id=str(event.event_id),
            subject_character=subject,
            applied=False,
            idempotent=False,
            prior_annotation=prior,
            final_annotation=prior,
            reason_code=REASON_SIGNIFICANCE_CONFLICT,
        )

    if prior is not None and new_rank == prior_rank:
        return KnowledgeSignificanceApplyResult(
            proposal_id=proposal.proposal_id,
            event_id=str(event.event_id),
            subject_character=subject,
            applied=True,
            idempotent=True,
            prior_annotation=prior,
            final_annotation=prior,
            reason_code=REASON_EQUAL_RANK_UNCHANGED,
        )

    annotation = _build_annotation(
        proposal,
        subject=subject,
        level=level,
        note=note,
    )
    annotations[subject] = annotation
    event.revelation_significance_by_character = annotations
    return KnowledgeSignificanceApplyResult(
        proposal_id=proposal.proposal_id,
        event_id=str(event.event_id),
        subject_character=subject,
        applied=True,
        idempotent=False,
        prior_annotation=prior,
        final_annotation=annotation,
        reason_code="applied",
    )


def apply_accepted_librarian_proposals(
    manager: Any,
    proposals: tuple[LibrarianSemanticProposal, ...],
    continuity_decision: ContinuityProposalBatchDecision,
) -> tuple[ContinuityProposalBatchDecision, list[KnowledgeSignificanceApplyResult]]:
    apply_results: list[KnowledgeSignificanceApplyResult] = []
    updated: list[ContinuityProposalItemDecision] = []

    proposal_by_id = {item.proposal_id: item for item in proposals}

    for item in continuity_decision.item_decisions:
        proposal = proposal_by_id.get(item.proposal_id)
        if (
            item.outcome != "accept"
            or proposal is None
            or str(proposal.proposal_kind) != "knowledge_revelation_significance"
        ):
            updated.append(item)
            continue

        result = apply_knowledge_revelation_significance(manager, proposal)
        apply_results.append(result)
        if result.applied:
            updated.append(
                ContinuityProposalItemDecision(
                    proposal_id=item.proposal_id,
                    outcome="accept",
                    reason_code=item.reason_code,
                    reason_detail=item.reason_detail,
                    durable_mutation_applied=result.reason_code == "applied",
                )
            )
        else:
            updated.append(
                ContinuityProposalItemDecision(
                    proposal_id=item.proposal_id,
                    outcome="reject",
                    reason_code=result.reason_code or "apply_failed",
                    reason_detail="S4b apply rejected after continuity accept",
                    durable_mutation_applied=False,
                )
            )

    accepted = sum(1 for item in updated if item.outcome == "accept")
    rejected = len(updated) - accepted
    new_decision = ContinuityProposalBatchDecision(
        batch_id=continuity_decision.batch_id,
        domain_commit_id=continuity_decision.domain_commit_id,
        item_decisions=tuple(updated),
        accepted_count=accepted,
        rejected_count=rejected,
    )
    return new_decision, apply_results

"""S4b apply path for issue_tension_pressure B2 semantic overlay (#40).

Persists Librarian-derived issue-pressure semantics separately from IssueState.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from continuity_scene_pressure_projection import compute_issue_material_fingerprint

REASON_UNKNOWN_ISSUE = "unknown_issue_reference"
REASON_ISSUE_NOT_PROJECTABLE = "issue_not_projectable"
REASON_MISSING_SEMANTIC = "missing_semantic_unmet_condition"
REASON_FORBIDDEN_FIELD = "forbidden_authority_field"
REASON_ALREADY_APPLIED = "already_applied"
REASON_UNCHANGED = "unchanged_overlay"

_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "pressure_kind",
        "required_next_step",
        "issue_status",
        "participants",
        "grant_knowledge",
        "add_to_known_by",
        "manufactured_fact",
    }
)


@dataclass(frozen=True)
class IssuePressureOverlayApplyResult:
    proposal_id: str
    issue_id: str
    applied: bool
    idempotent: bool
    prior_overlay: dict[str, Any] | None
    final_overlay: dict[str, Any] | None
    reason_code: str = ""
    accepted_payload: dict[str, Any] | None = None


def _overlay_store(manager: Any) -> dict[str, dict[str, Any]]:
    if not hasattr(manager, "issue_pressure_semantic_overlays"):
        manager.issue_pressure_semantic_overlays = {}
    store = getattr(manager, "issue_pressure_semantic_overlays")
    if not isinstance(store, dict):
        store = {}
        manager.issue_pressure_semantic_overlays = store
    return store


def _find_issue(manager: Any, issue_ref: str) -> Any | None:
    ref = str(issue_ref or "").strip()
    if not ref:
        return None
    issues = getattr(manager, "issues", None) or {}
    issue = issues.get(ref)
    if issue is not None:
        return issue
    for candidate in issues.values():
        issue_id = str(getattr(candidate, "issue_id", ""))
        if issue_id == ref:
            return candidate
        stable = f"issue:{issue_id}"
        if ref == stable:
            return candidate
    return None


def _build_overlay(
    proposal: Any,
    *,
    issue: Any,
    semantic_unmet_condition: str,
    stakes_summary: str | None,
) -> dict[str, Any]:
    payload = dict(proposal.proposed_payload or {})
    return {
        "issue_id": str(issue.issue_id),
        "semantic_unmet_condition": semantic_unmet_condition,
        "stakes_summary": stakes_summary,
        "lifecycle": "active",
        "proposal_id": proposal.proposal_id,
        "proposal_batch_id": proposal.proposal_batch_id,
        "domain_commit_id": proposal.commit_binding.domain_commit_id,
        "librarian_inference_id": proposal.provenance.librarian_inference_id,
        "derivation_summary": proposal.derivation_summary,
        "confidence": proposal.confidence,
        "applied_at_turn_index": proposal.commit_binding.turn_index,
        "issue_material_fingerprint": compute_issue_material_fingerprint(issue),
        "accepted_payload": {
            "issue_ref": str(payload.get("issue_ref", "") or issue.issue_id),
            "semantic_unmet_condition": semantic_unmet_condition,
            **({"stakes_summary": stakes_summary} if stakes_summary else {}),
        },
    }


def apply_issue_tension_pressure(
    manager: Any,
    proposal: Any,
) -> IssuePressureOverlayApplyResult:
    from continuity_state import IssueStatus

    payload = dict(proposal.proposed_payload or {})
    issue_ref = str(payload.get("issue_ref", "") or "").strip()
    semantic = str(payload.get("semantic_unmet_condition", "") or "").strip()
    stakes_raw = str(payload.get("stakes_summary", "") or "").strip()
    stakes_summary = stakes_raw or None

    if any(key in payload for key in _FORBIDDEN_PAYLOAD_KEYS):
        return IssuePressureOverlayApplyResult(
            proposal_id=proposal.proposal_id,
            issue_id=issue_ref,
            applied=False,
            idempotent=False,
            prior_overlay=None,
            final_overlay=None,
            reason_code=REASON_FORBIDDEN_FIELD,
        )

    if not semantic:
        return IssuePressureOverlayApplyResult(
            proposal_id=proposal.proposal_id,
            issue_id=issue_ref,
            applied=False,
            idempotent=False,
            prior_overlay=None,
            final_overlay=None,
            reason_code=REASON_MISSING_SEMANTIC,
        )

    issue = _find_issue(manager, issue_ref)
    if issue is None:
        return IssuePressureOverlayApplyResult(
            proposal_id=proposal.proposal_id,
            issue_id=issue_ref,
            applied=False,
            idempotent=False,
            prior_overlay=None,
            final_overlay=None,
            reason_code=REASON_UNKNOWN_ISSUE,
        )

    if issue.status not in {IssueStatus.ACTIVE, IssueStatus.ESCALATING}:
        return IssuePressureOverlayApplyResult(
            proposal_id=proposal.proposal_id,
            issue_id=str(issue.issue_id),
            applied=False,
            idempotent=False,
            prior_overlay=_overlay_store(manager).get(str(issue.issue_id)),
            final_overlay=None,
            reason_code=REASON_ISSUE_NOT_PROJECTABLE,
        )

    store = _overlay_store(manager)
    issue_id = str(issue.issue_id)
    prior = dict(store.get(issue_id, {}) or {}) or None

    if prior and str(prior.get("proposal_id", "")) == proposal.proposal_id:
        return IssuePressureOverlayApplyResult(
            proposal_id=proposal.proposal_id,
            issue_id=issue_id,
            applied=True,
            idempotent=True,
            prior_overlay=prior,
            final_overlay=prior,
            reason_code=REASON_ALREADY_APPLIED,
            accepted_payload=dict(prior.get("accepted_payload") or {}),
        )

    new_overlay = _build_overlay(
        proposal,
        issue=issue,
        semantic_unmet_condition=semantic,
        stakes_summary=stakes_summary,
    )

    if (
        prior
        and prior.get("semantic_unmet_condition") == semantic
        and prior.get("stakes_summary") == stakes_summary
        and prior.get("issue_material_fingerprint") == new_overlay["issue_material_fingerprint"]
        and str(prior.get("proposal_id", "")) != proposal.proposal_id
    ):
        store[issue_id] = {**prior, **new_overlay}
        return IssuePressureOverlayApplyResult(
            proposal_id=proposal.proposal_id,
            issue_id=issue_id,
            applied=True,
            idempotent=True,
            prior_overlay=prior,
            final_overlay=store[issue_id],
            reason_code=REASON_UNCHANGED,
            accepted_payload=dict(new_overlay.get("accepted_payload") or {}),
        )

    store[issue_id] = new_overlay
    return IssuePressureOverlayApplyResult(
        proposal_id=proposal.proposal_id,
        issue_id=issue_id,
        applied=True,
        idempotent=False,
        prior_overlay=prior,
        final_overlay=new_overlay,
        reason_code="applied",
        accepted_payload=dict(new_overlay.get("accepted_payload") or {}),
    )


def apply_accepted_librarian_proposals(
    manager: Any,
    proposals: tuple[Any, ...],
    continuity_decision: Any,
) -> tuple[Any, list[Any], list[IssuePressureOverlayApplyResult]]:
    from domain_api.librarian_proposal_contract import (  # noqa: WPS433
        ContinuityProposalBatchDecision,
        ContinuityProposalItemDecision,
    )
    from continuity_librarian_knowledge_significance import (  # noqa: WPS433
        KnowledgeSignificanceApplyResult,
        apply_knowledge_revelation_significance,
    )

    s4b_results: list[KnowledgeSignificanceApplyResult] = []
    b2_results: list[IssuePressureOverlayApplyResult] = []
    updated: list[ContinuityProposalItemDecision] = []

    proposal_by_id = {item.proposal_id: item for item in proposals}

    for item in continuity_decision.item_decisions:
        proposal = proposal_by_id.get(item.proposal_id)
        if item.outcome != "accept" or proposal is None:
            updated.append(item)
            continue

        kind = str(proposal.proposal_kind)
        if kind == "knowledge_revelation_significance":
            result = apply_knowledge_revelation_significance(manager, proposal)
            s4b_results.append(result)
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
            continue

        if kind == "issue_tension_pressure":
            result = apply_issue_tension_pressure(manager, proposal)
            b2_results.append(result)
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
                        reason_detail="B2 issue-pressure apply rejected after continuity accept",
                        durable_mutation_applied=False,
                    )
                )
            continue

        updated.append(item)

    accepted = sum(1 for decision in updated if decision.outcome == "accept")
    rejected = len(updated) - accepted
    new_decision = ContinuityProposalBatchDecision(
        batch_id=continuity_decision.batch_id,
        domain_commit_id=continuity_decision.domain_commit_id,
        item_decisions=tuple(updated),
        accepted_count=accepted,
        rejected_count=rejected,
    )
    combined_results: list[Any] = [*s4b_results, *b2_results]
    return new_decision, combined_results, b2_results

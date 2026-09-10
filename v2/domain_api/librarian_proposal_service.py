"""Librarian write-side proposal service (#34 S4a).

Prepare/finalize post-commit grounded proposal batches. No direct Continuity writes.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_librarian_proposals import (  # noqa: E402
    build_evidence_closure,
    evaluate_librarian_proposal_batch,
    librarian_proposal_audit_metadata,
)

from .librarian_contract import VisibilityEnvelope
from .librarian_proposal_context import (
    build_post_commit_evidence_catalog,
    build_proposal_manifest_contributions,
)
from .librarian_proposal_contract import (
    HostProposalBatchValidation,
    LibrarianProposalBatchResult,
    LibrarianProposalContextRequest,
    LibrarianProposalPrepareResponse,
    ProposalBatchAudit,
    ProposalBatchDegradationMode,
    ProposalCommitBinding,
    ProposalEvidenceCatalogItem,
    compute_proposal_batch_hash,
    new_proposal_batch_id,
    new_proposal_request_id,
)
from .post_commit_semantic_eligibility import evaluate_post_commit_semantic_eligibility
from .librarian_proposal_validate import (
    parse_librarian_proposal_result,
    validate_host_proposal_batch,
)
from .session_state import LiveSession

_logger = logging.getLogger(__name__)


def find_terminal_audit_for_commit(
    fixture: LiveSession,
    domain_commit_id: str,
) -> dict[str, Any] | None:
    """Return the latest persisted audit entry for a commit, if any (#39 at-most-once)."""
    commit_id = str(domain_commit_id or "").strip()
    if not commit_id:
        return None
    for entry in reversed(getattr(fixture, "librarian_proposal_audit_log", []) or []):
        if str(entry.get("librarian_proposal_domain_commit_id") or "") != commit_id:
            continue
        return dict(entry)
    return None


def build_post_commit_proposal_request(
    *,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    domain_commit_id: str,
    librarian_inference_id: str,
    visibility_envelope: VisibilityEnvelope | None = None,
) -> LibrarianProposalContextRequest:
    envelope = visibility_envelope or VisibilityEnvelope(
        viewer_role="host_internal",
        authority_ceiling_enforced="derived",
    )
    return LibrarianProposalContextRequest(
        request_id=new_proposal_request_id(),
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        domain_commit_id=domain_commit_id,
        visibility_envelope=envelope,
        librarian_inference_id=librarian_inference_id,
    )


class LibrarianProposalService:
    """Write-side grounded proposal seam — proposals only, Continuity decides separately."""

    def prepare_proposal_context(
        self,
        request: LibrarianProposalContextRequest,
        fixture: LiveSession,
    ) -> LibrarianProposalPrepareResponse:
        catalog, commit_record = build_post_commit_evidence_catalog(request, fixture)
        if commit_record is None or not catalog:
            raise ValueError(f"unknown domain_commit_id for proposal context: {request.domain_commit_id}")

        snapshot_id = (
            f"cv:{fixture.continuity_version}:scene:{request.hg_scene_id}:"
            f"round:{request.hg_round_id}:commit:{request.domain_commit_id}"
        )
        manifest_id = f"manifest-{request.request_id}"
        contributions = build_proposal_manifest_contributions(
            request,
            manifest_id=manifest_id,
            catalog=catalog,
            authoritative_snapshot_id_value=snapshot_id,
        )
        return LibrarianProposalPrepareResponse(
            manifest_id=manifest_id,
            inference_id=request.librarian_inference_id,
            request_id=request.request_id,
            hg_scene_id=request.hg_scene_id,
            hg_round_id=request.hg_round_id,
            domain_commit_id=request.domain_commit_id,
            contributions=tuple(contributions),
            evidence_catalog=catalog,
            authoritative_snapshot_id=snapshot_id,
        )

    def finalize_proposals(
        self,
        request: LibrarianProposalContextRequest,
        fixture: LiveSession,
        *,
        proposal_result: dict[str, Any] | None,
        evidence_catalog: tuple[ProposalEvidenceCatalogItem, ...] | None = None,
        proposal_generation_failure: str | None = None,
        proposal_generation_skip_reason: str | None = None,
        allow_legacy_kinds: bool = False,
    ) -> LibrarianProposalBatchResult:
        batch_id = new_proposal_batch_id()
        commit_binding = ProposalCommitBinding(
            domain_commit_id=request.domain_commit_id,
            hg_round_id=request.hg_round_id,
            turn_index=request.turn_index,
        )
        if evidence_catalog is None:
            evidence_catalog, _commit = build_post_commit_evidence_catalog(request, fixture)
        if evidence_catalog is None:
            evidence_catalog = ()

        if proposal_generation_skip_reason:
            host_validation = HostProposalBatchValidation(
                accepted=True,
                reason=proposal_generation_skip_reason,
                item_results=(),
                rejection_codes=(),
            )
            degradation_mode: ProposalBatchDegradationMode = "eligibility_skipped"
            audit = ProposalBatchAudit(
                batch_id=batch_id,
                batch_hash=compute_proposal_batch_hash(
                    {
                        "batch_id": batch_id,
                        "skip_reason": proposal_generation_skip_reason,
                        "proposals": [],
                    }
                ),
                request_id=request.request_id,
                domain_commit_id=request.domain_commit_id,
                librarian_inference_id=request.librarian_inference_id,
                host_validation=host_validation,
                continuity_decision=None,
                degradation_mode=degradation_mode,
                proposals_considered=(),
            )
            self._record_audit(
                fixture,
                request,
                audit,
                None,
                skip_reason=proposal_generation_skip_reason,
            )
            return LibrarianProposalBatchResult(
                batch_id=batch_id,
                request_id=request.request_id,
                domain_commit_id=request.domain_commit_id,
                proposals=(),
                host_validation=host_validation,
                continuity_decision=None,
                audit=audit,
                degradation_mode=degradation_mode,
            )

        if proposal_result is None:
            if proposal_generation_failure == "structural_parse_failed":
                host_validation = HostProposalBatchValidation(
                    accepted=False,
                    reason="structural_parse_failed",
                    rejection_codes=("malformed_result",),
                )
                degradation_mode: ProposalBatchDegradationMode = "malformed_result"
            else:
                host_validation = HostProposalBatchValidation(
                    accepted=False,
                    reason="inference_unavailable",
                    rejection_codes=("inference_failed",),
                )
                degradation_mode = "inference_failed"
            audit = ProposalBatchAudit(
                batch_id=batch_id,
                batch_hash=compute_proposal_batch_hash({"batch_id": batch_id, "proposals": []}),
                request_id=request.request_id,
                domain_commit_id=request.domain_commit_id,
                librarian_inference_id=request.librarian_inference_id,
                host_validation=host_validation,
                continuity_decision=None,
                degradation_mode=degradation_mode,
            )
            self._record_audit(fixture, request, audit, None)
            return LibrarianProposalBatchResult(
                batch_id=batch_id,
                request_id=request.request_id,
                domain_commit_id=request.domain_commit_id,
                proposals=(),
                host_validation=host_validation,
                continuity_decision=None,
                audit=audit,
                degradation_mode=degradation_mode,
            )

        parsed, parse_error = parse_librarian_proposal_result(
            proposal_result,
            batch_id=batch_id,
            commit_binding=commit_binding,
            librarian_inference_id=request.librarian_inference_id,
            semantic_producer_role=request.semantic_producer_role,
        )
        if parsed is None:
            host_validation = HostProposalBatchValidation(
                accepted=False,
                reason=parse_error,
                rejection_codes=("malformed_result",),
            )
            audit = ProposalBatchAudit(
                batch_id=batch_id,
                batch_hash=compute_proposal_batch_hash({"batch_id": batch_id, "error": parse_error}),
                request_id=request.request_id,
                domain_commit_id=request.domain_commit_id,
                librarian_inference_id=request.librarian_inference_id,
                host_validation=host_validation,
                continuity_decision=None,
                degradation_mode="malformed_result",
            )
            self._record_audit(fixture, request, audit, None)
            return LibrarianProposalBatchResult(
                batch_id=batch_id,
                request_id=request.request_id,
                domain_commit_id=request.domain_commit_id,
                proposals=(),
                host_validation=host_validation,
                continuity_decision=None,
                audit=audit,
                degradation_mode="malformed_result",
            )

        host_validation = validate_host_proposal_batch(
            parsed,
            catalog=evidence_catalog,
            domain_commit_id=request.domain_commit_id,
            allow_legacy_kinds=allow_legacy_kinds,
        )
        host_accepted_by_id = {
            item.proposal_id: item.accepted for item in host_validation.item_results
        }
        closure = build_evidence_closure(
            domain_commit_id=request.domain_commit_id,
            catalog_anchor_ids=tuple(item.anchor_id for item in evidence_catalog),
            catalog_visibility={item.anchor_id: item.visibility_scope for item in evidence_catalog},
            catalog_authority={item.anchor_id: item.authority_class for item in evidence_catalog},
        )
        continuity_decision = evaluate_librarian_proposal_batch(
            parsed,
            closure=closure,
            host_accepted_by_id=host_accepted_by_id,
            batch_id=batch_id,
            catalog=evidence_catalog,
            allow_legacy_kinds=allow_legacy_kinds,
        )
        from continuity_librarian_issue_pressure import (  # noqa: WPS433
            apply_accepted_librarian_proposals,
        )

        continuity_decision, apply_results, b2_apply_results = apply_accepted_librarian_proposals(
            fixture.manager,
            parsed,
            continuity_decision,
        )

        audit_payload = {
            "batch_id": batch_id,
            "request_id": request.request_id,
            "domain_commit_id": request.domain_commit_id,
            "proposals": [asdict(proposal) for proposal in parsed],
            "host_validation": asdict(host_validation),
            "continuity_decision": asdict(continuity_decision),
            "s4b_apply_results": [
                asdict(item)
                for item in apply_results
                if item.__class__.__name__ != "IssuePressureOverlayApplyResult"
            ],
            "issue_pressure_apply_results": [asdict(item) for item in b2_apply_results],
        }
        audit = ProposalBatchAudit(
            batch_id=batch_id,
            batch_hash=compute_proposal_batch_hash(audit_payload),
            request_id=request.request_id,
            domain_commit_id=request.domain_commit_id,
            librarian_inference_id=request.librarian_inference_id,
            host_validation=host_validation,
            continuity_decision=continuity_decision,
            degradation_mode="none" if host_validation.accepted else "host_validation_failed",
            proposals_considered=tuple(item.proposal_id for item in parsed),
        )

        self._record_audit(
            fixture,
            request,
            audit,
            continuity_decision,
            apply_results=apply_results,
            b2_apply_results=b2_apply_results,
        )

        return LibrarianProposalBatchResult(
            batch_id=batch_id,
            request_id=request.request_id,
            domain_commit_id=request.domain_commit_id,
            proposals=parsed,
            host_validation=host_validation,
            continuity_decision=continuity_decision,
            audit=audit,
            degradation_mode=audit.degradation_mode,
        )

    def evaluate_eligibility(self, fixture: LiveSession) -> tuple[bool, str]:
        return evaluate_post_commit_semantic_eligibility(fixture)

    def _record_audit(
        self,
        fixture: LiveSession,
        request: LibrarianProposalContextRequest,
        audit: ProposalBatchAudit,
        continuity_decision: Any,
        *,
        apply_results: list[Any] | None = None,
        b2_apply_results: list[Any] | None = None,
        skip_reason: str | None = None,
    ) -> None:
        metadata = librarian_proposal_audit_metadata(
            batch_id=audit.batch_id,
            domain_commit_id=request.domain_commit_id,
            librarian_inference_id=request.librarian_inference_id,
            host_validation=audit.host_validation,
            continuity_decision=continuity_decision,
            semantic_producer_role=request.semantic_producer_role,
            eligibility_skip_reason=skip_reason,
        )
        metadata["batch_hash"] = audit.batch_hash
        metadata["host_validation"] = asdict(audit.host_validation)
        if continuity_decision is not None:
            metadata["continuity_decision"] = asdict(continuity_decision)
        if apply_results:
            metadata["s4b_apply_results"] = [
                asdict(item)
                for item in apply_results
                if item.__class__.__name__ != "IssuePressureOverlayApplyResult"
            ]
        if b2_apply_results:
            metadata["issue_pressure_apply_results"] = [
                asdict(item) for item in b2_apply_results
            ]
        if not hasattr(fixture, "librarian_proposal_audit_log"):
            fixture.librarian_proposal_audit_log = []  # type: ignore[attr-defined]
        fixture.librarian_proposal_audit_log.append(metadata)  # type: ignore[attr-defined]

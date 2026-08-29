"""Plot Cognition initialization domain service (#60)."""

from __future__ import annotations

from .plot_cognition_initialization_contract import (
    InitializationCommitResult,
    InitializationForensicHandoff,
    InitializationSourceSnapshot,
    ObjectiveValidationResult,
    PlotCognitionInitializationProposal,
    materialize_initial_overlay,
    validate_initialization_proposal_objective,
)
from .plot_cognition_initialization_sources import (
    gather_initialization_sources,
    initialization_sources_complete,
)
from .plot_cognition_overlay_service import PlotCognitionOverlayService
from .plot_cognition_overlay_store import (
    BoundednessPolicy,
    LoadStatus,
    PlotCognitionOverlayStore,
)
from .session_state import LiveSession


class PlotCognitionInitializationService:
    """Domain capabilities for Plot Cognition overlay initialization."""

    def __init__(self, overlay_service: PlotCognitionOverlayService) -> None:
        self._overlay = overlay_service

    def gather_sources(self, fixture: LiveSession) -> InitializationSourceSnapshot:
        return gather_initialization_sources(fixture)

    def sources_ready_for_initialization(
        self,
        source_snapshot: InitializationSourceSnapshot,
    ) -> bool:
        return initialization_sources_complete(source_snapshot.opening_completeness)

    def validate_proposal(
        self,
        proposal: PlotCognitionInitializationProposal,
        *,
        policy: BoundednessPolicy,
    ) -> ObjectiveValidationResult:
        return validate_initialization_proposal_objective(
            proposal,
            policy_max_active_goals=policy.max_active_goals,
            policy_max_active_pressures=policy.max_active_pressures,
        )

    def materialize(
        self,
        proposal: PlotCognitionInitializationProposal,
        *,
        plot_cognition_scope_id: str,
    ) -> tuple[PlotCognitionOverlayStore | None, ObjectiveValidationResult]:
        store, validation = materialize_initial_overlay(
            proposal,
            plot_cognition_scope_id=plot_cognition_scope_id,
        )
        return store, validation

    def commit_initial_overlay_if_absent(
        self,
        fixture: LiveSession,
        proposal: PlotCognitionInitializationProposal,
        *,
        policy: BoundednessPolicy,
        forensic_handoff: InitializationForensicHandoff | None = None,
    ) -> InitializationCommitResult:
        scope_id = str(fixture.plot_cognition_scope_id or "")
        if proposal.plot_cognition_scope_id != scope_id:
            return InitializationCommitResult(
                success=False,
                code="integrity_invalid",
                message="proposal scope id does not match fixture scope id",
            )

        current_sources = self.gather_sources(fixture)
        if current_sources.fingerprint != proposal.source_snapshot_fingerprint:
            return InitializationCommitResult(
                success=False,
                code="stale_source",
                message="proposal source fingerprint does not match current initialization sources",
            )

        if not self.sources_ready_for_initialization(current_sources):
            return InitializationCommitResult(
                success=False,
                code="opening_incomplete",
                message="opening presentation required for initialization is not yet durable",
            )

        validation = self.validate_proposal(proposal, policy=policy)
        if not validation.ok:
            code = "budget_exceeded" if validation.over_budget else "integrity_invalid"
            return InitializationCommitResult(
                success=False,
                code=code,
                message="proposal failed objective validation",
            )

        store, materialize_validation = self.materialize(
            proposal,
            plot_cognition_scope_id=scope_id,
        )
        if store is None or not materialize_validation.ok:
            return InitializationCommitResult(
                success=False,
                code="integrity_invalid",
                message="proposal could not be materialized",
            )

        loaded = self._overlay.load(scope_id, policy=policy)
        if loaded.status == LoadStatus.READY:
            return InitializationCommitResult(
                success=False,
                code="already_initialized",
                message="plot cognition overlay already initialized",
                store_revision=loaded.store.store_revision if loaded.store else None,
                load_status=loaded.status.value,
            )
        if loaded.status in {
            LoadStatus.CORRUPT,
            LoadStatus.UNSUPPORTED_VERSION,
            LoadStatus.DEGRADED,
        }:
            return InitializationCommitResult(
                success=False,
                code="blocked_status",
                message=f"overlay store status {loaded.status.value} blocks initialization",
                load_status=loaded.status.value,
            )

        expected_revision = loaded.store.store_revision if loaded.store is not None else 0
        replace_result = self._overlay.replace_snapshot(
            scope_id,
            store,
            expected_revision=expected_revision,
            policy=policy,
        )
        if forensic_handoff is not None:
            forensic_handoff.accepted_proposal_id = proposal.proposal_id
            forensic_handoff.materialized_store = store.to_dict()
            forensic_handoff.commit_result = {
                "success": replace_result.success,
                "error_code": replace_result.error_code,
                "prior_revision": replace_result.prior_revision,
                "new_revision": replace_result.new_revision,
            }

        if not replace_result.success:
            code = replace_result.error_code or "persistence_failed"
            if code == "revision_conflict":
                reloaded = self._overlay.load(scope_id, policy=policy)
                if reloaded.status == LoadStatus.READY:
                    return InitializationCommitResult(
                        success=False,
                        code="already_initialized",
                        message="plot cognition overlay initialized by concurrent writer",
                        store_revision=reloaded.store.store_revision if reloaded.store else None,
                        load_status=reloaded.status.value,
                    )
                mapped = "revision_conflict"
            elif code == "budget_exceeded":
                mapped = "budget_exceeded"
            else:
                mapped = "persistence_failed"
            return InitializationCommitResult(
                success=False,
                code=mapped,  # type: ignore[arg-type]
                message=replace_result.error_message or "overlay persistence failed",
                prior_revision=replace_result.prior_revision,
            )

        return InitializationCommitResult(
            success=True,
            code="committed",
            message="initial plot cognition overlay established",
            store_revision=replace_result.new_revision,
            prior_revision=replace_result.prior_revision,
            load_status=LoadStatus.READY.value,
        )

    def is_initialization_eligible(
        self,
        fixture: LiveSession,
        *,
        policy: BoundednessPolicy,
    ) -> tuple[bool, str]:
        scope_id = str(fixture.plot_cognition_scope_id or "")
        loaded = self._overlay.load(scope_id, policy=policy)
        if loaded.status == LoadStatus.READY:
            return False, "already_initialized"
        if loaded.status in {
            LoadStatus.CORRUPT,
            LoadStatus.UNSUPPORTED_VERSION,
            LoadStatus.DEGRADED,
        }:
            return False, loaded.status.value
        sources = self.gather_sources(fixture)
        if not self.sources_ready_for_initialization(sources):
            return False, "opening_incomplete"
        return True, "absent"

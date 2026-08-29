"""Plot Cognition update and semantic replan domain service (#61)."""

from __future__ import annotations

from .plot_cognition_overlay_service import PlotCognitionOverlayService
from .plot_cognition_overlay_store import (
    ASSIMILATED_AUTHORITY_SCHEMA,
    AssimilatedAuthority,
    AssimilatedSessionAuthority,
    BoundednessPolicy,
    LoadStatus,
    PlotCognitionOverlayStore,
    authority_freshness_status,
    sync_legacy_commit_lineage,
)
from .plot_cognition_update_contract import (
    CognitionUpdateSourceSnapshot,
    FreshnessAssessment,
    PlotCognitionReplanEvaluation,
    PlotCognitionReplanProposal,
    PlotCognitionUpdateEvaluation,
    PlotCognitionUpdateProposal,
    UpdateCommitResult,
    UpdateForensicHandoff,
    materialize_replan_overlay,
    materialize_update_overlay,
    validate_authority_vector_consistency,
    validate_replan_proposal_objective,
    validate_update_proposal_objective,
)
from .plot_cognition_update_sources import (
    build_assimilated_authority_from_snapshot,
    gather_update_source_snapshot,
)
from .session_state import LiveSession
from .story_knowledge_contract import StoryKnowledgeRecord


class PlotCognitionUpdateService:
    """Domain capabilities for Plot Cognition overlay update and semantic replan."""

    def __init__(self, overlay_service: PlotCognitionOverlayService) -> None:
        self._overlay = overlay_service

    def gather_sources(
        self,
        fixture: LiveSession,
        store: PlotCognitionOverlayStore,
        story_records: list[StoryKnowledgeRecord] | None,
        contributors: tuple[str, ...],
        *,
        catch_up_mode: str = "sequential",
        evidence_gap: bool = False,
        evidence_gap_detail: str | None = None,
    ) -> CognitionUpdateSourceSnapshot:
        return gather_update_source_snapshot(
            fixture,
            store,
            story_records,
            contributors,
            catch_up_mode=catch_up_mode,  # type: ignore[arg-type]
            evidence_gap=evidence_gap,
            evidence_gap_detail=evidence_gap_detail,
        )

    def assess_freshness(
        self,
        fixture: LiveSession,
        store: PlotCognitionOverlayStore,
        policy: BoundednessPolicy,
        *,
        story_records: list[StoryKnowledgeRecord] | None = None,
        contributors: tuple[str, ...] = (),
    ) -> FreshnessAssessment:
        loaded = self._overlay.load(store.plot_cognition_scope_id, policy=policy)
        if loaded.status != LoadStatus.READY or loaded.store is None:
            return FreshnessAssessment(
                status="overlay_unavailable",
                message=f"overlay status {loaded.status.value} blocks freshness assessment",
            )

        snapshot = self.gather_sources(
            fixture,
            loaded.store,
            story_records,
            contributors or (fixture.hg_scene_id,),
        )
        current_commit = snapshot.through_domain_commit_id
        status = authority_freshness_status(
            loaded.store,
            current_domain_commit_id=current_commit,
            current_continuity_version=snapshot.continuity_version,
            current_authority_source_fingerprint=snapshot.authority_source_fingerprint,
            contributor_hg_scene_ids=contributors or (fixture.hg_scene_id,),
        )
        if status == "freshness_unprovable" and loaded.store.assimilated_authority is None:
            return FreshnessAssessment(
                status="freshness_unprovable",
                message="authority metadata absent; reconciliation required",
                source_snapshot=snapshot,
            )
        return FreshnessAssessment(
            status=status,
            message=f"authority freshness status: {status}",
            source_snapshot=snapshot,
        )

    def first_reconciliation(
        self,
        fixture: LiveSession,
        store: PlotCognitionOverlayStore,
        policy: BoundednessPolicy,
        *,
        story_records: list[StoryKnowledgeRecord] | None = None,
        contributors: tuple[str, ...] = (),
        forensic_handoff: UpdateForensicHandoff | None = None,
    ) -> UpdateCommitResult:
        scope_id = str(fixture.plot_cognition_scope_id or "")
        loaded = self._overlay.load(scope_id, policy=policy)
        if loaded.status != LoadStatus.READY or loaded.store is None:
            return UpdateCommitResult(
                success=False,
                code="overlay_unavailable",
                message=f"overlay status {loaded.status.value} blocks reconciliation",
                load_status=loaded.status.value,
            )
        current_store = loaded.store
        if current_store.assimilated_authority is not None:
            return UpdateCommitResult(
                success=False,
                code="integrity_invalid",
                message="authority metadata already present",
                store_revision=current_store.store_revision,
            )

        snapshot = self.gather_sources(
            fixture,
            current_store,
            story_records,
            contributors or (fixture.hg_scene_id,),
        )
        authority = build_assimilated_authority_from_snapshot(snapshot)
        reconciled = PlotCognitionOverlayStore(
            store_schema=current_store.store_schema,
            plot_cognition_scope_id=current_store.plot_cognition_scope_id,
            store_revision=current_store.store_revision + 1,
            assimilated_through_domain_commit_id=snapshot.through_domain_commit_id,
            goals=dict(current_store.goals),
            pressures=dict(current_store.pressures),
            active_frame=current_store.active_frame,
            assimilated_authority=authority,
        )
        reconciled = sync_legacy_commit_lineage(
            reconciled,
            sole_contributor_hg_scene_id=fixture.hg_scene_id,
        )
        vector_ok = validate_authority_vector_consistency(
            reconciled,
            sole_contributor_hg_scene_id=fixture.hg_scene_id,
        )
        if not vector_ok.ok:
            return UpdateCommitResult(
                success=False,
                code="integrity_invalid",
                message="reconciled authority vector failed consistency validation",
            )

        replace_result = self._overlay.replace_snapshot(
            scope_id,
            reconciled,
            expected_revision=current_store.store_revision,
            policy=policy,
        )
        if forensic_handoff is not None:
            forensic_handoff.outcome = "endpoint_reconciliation"
            forensic_handoff.source_snapshot = snapshot
            forensic_handoff.prior_authority = []
            forensic_handoff.resulting_authority = [
                session.to_dict() for session in authority.sessions
            ]
            forensic_handoff.materialized_store = reconciled.to_dict()
            forensic_handoff.commit_result = {
                "success": replace_result.success,
                "error_code": replace_result.error_code,
                "prior_revision": replace_result.prior_revision,
                "new_revision": replace_result.new_revision,
            }

        if not replace_result.success:
            code = replace_result.error_code or "persistence_failed"
            mapped = "revision_conflict" if code == "revision_conflict" else "persistence_failed"
            return UpdateCommitResult(
                success=False,
                code=mapped,  # type: ignore[arg-type]
                message=replace_result.error_message or "reconciliation persistence failed",
                prior_revision=replace_result.prior_revision,
            )

        return UpdateCommitResult(
            success=True,
            code="reconciliation_established",
            message="first authority reconciliation established without cognition change",
            store_revision=replace_result.new_revision,
            prior_revision=replace_result.prior_revision,
            load_status=LoadStatus.READY.value,
            forensic_outcome="endpoint_reconciliation",
        )

    def advance_authority_unchanged(
        self,
        fixture: LiveSession,
        store: PlotCognitionOverlayStore,
        policy: BoundednessPolicy,
        *,
        source_snapshot: CognitionUpdateSourceSnapshot,
        story_records: list[StoryKnowledgeRecord] | None = None,
        contributors: tuple[str, ...] = (),
        forensic_handoff: UpdateForensicHandoff | None = None,
    ) -> UpdateCommitResult:
        scope_id = str(fixture.plot_cognition_scope_id or "")
        if source_snapshot.plot_cognition_scope_id != scope_id:
            return UpdateCommitResult(
                success=False,
                code="integrity_invalid",
                message="source snapshot scope id does not match fixture scope id",
            )

        loaded = self._overlay.load(scope_id, policy=policy)
        if loaded.status != LoadStatus.READY or loaded.store is None:
            return UpdateCommitResult(
                success=False,
                code="overlay_unavailable",
                message=f"overlay status {loaded.status.value} blocks advancement",
                load_status=loaded.status.value,
            )
        current_store = loaded.store
        if current_store.store_revision != source_snapshot.prior_store_revision:
            return UpdateCommitResult(
                success=False,
                code="stale_revision",
                message="overlay store revision changed since snapshot",
                store_revision=current_store.store_revision,
            )

        current_sources = self.gather_sources(
            fixture,
            current_store,
            story_records,
            contributors or (fixture.hg_scene_id,),
        )
        if current_sources.continuity_version != source_snapshot.continuity_version:
            return UpdateCommitResult(
                success=False,
                code="stale_continuity_version",
                message="continuity version changed since snapshot",
            )
        if current_sources.authority_source_fingerprint != source_snapshot.authority_source_fingerprint:
            return UpdateCommitResult(
                success=False,
                code="stale_source",
                message="authority fingerprint changed since snapshot",
            )

        authority = build_assimilated_authority_from_snapshot(current_sources)
        advanced = PlotCognitionOverlayStore(
            store_schema=current_store.store_schema,
            plot_cognition_scope_id=current_store.plot_cognition_scope_id,
            store_revision=current_store.store_revision + 1,
            assimilated_through_domain_commit_id=current_sources.through_domain_commit_id,
            goals=dict(current_store.goals),
            pressures=dict(current_store.pressures),
            active_frame=current_store.active_frame,
            assimilated_authority=authority,
        )
        advanced = sync_legacy_commit_lineage(
            advanced,
            sole_contributor_hg_scene_id=fixture.hg_scene_id,
        )

        replace_result = self._overlay.replace_snapshot(
            scope_id,
            advanced,
            expected_revision=current_store.store_revision,
            policy=policy,
        )
        if forensic_handoff is not None:
            forensic_handoff.outcome = "objective_authority_unchanged"
            forensic_handoff.source_snapshot = source_snapshot
            forensic_handoff.prior_authority = [
                item.to_dict() for item in source_snapshot.prior_assimilated_authority
            ]
            forensic_handoff.resulting_authority = [
                session.to_dict() for session in authority.sessions
            ]
            forensic_handoff.materialized_store = advanced.to_dict()
            forensic_handoff.commit_result = {
                "success": replace_result.success,
                "error_code": replace_result.error_code,
                "prior_revision": replace_result.prior_revision,
                "new_revision": replace_result.new_revision,
            }

        if not replace_result.success:
            code = replace_result.error_code or "persistence_failed"
            mapped = "revision_conflict" if code == "revision_conflict" else "persistence_failed"
            return UpdateCommitResult(
                success=False,
                code=mapped,  # type: ignore[arg-type]
                message=replace_result.error_message or "authority advancement failed",
                prior_revision=replace_result.prior_revision,
            )

        return UpdateCommitResult(
            success=True,
            code="authority_unchanged",
            message="authority metadata advanced without cognition change",
            store_revision=replace_result.new_revision,
            prior_revision=replace_result.prior_revision,
            load_status=LoadStatus.READY.value,
            forensic_outcome="objective_authority_unchanged",
        )

    def commit_update(
        self,
        fixture: LiveSession,
        proposal: PlotCognitionUpdateProposal,
        evaluation: PlotCognitionUpdateEvaluation,
        *,
        policy: BoundednessPolicy,
        replan_proposal: PlotCognitionReplanProposal | None = None,
        replan_eval: PlotCognitionReplanEvaluation | None = None,
        story_records: list[StoryKnowledgeRecord] | None = None,
        contributors: tuple[str, ...] = (),
        forensic_handoff: UpdateForensicHandoff | None = None,
    ) -> UpdateCommitResult:
        scope_id = str(fixture.plot_cognition_scope_id or "")
        if proposal.plot_cognition_scope_id != scope_id:
            return UpdateCommitResult(
                success=False,
                code="integrity_invalid",
                message="proposal scope id does not match fixture scope id",
            )

        loaded = self._overlay.load(scope_id, policy=policy)
        if loaded.status != LoadStatus.READY or loaded.store is None:
            return UpdateCommitResult(
                success=False,
                code="overlay_unavailable",
                message=f"overlay status {loaded.status.value} blocks update commit",
                load_status=loaded.status.value,
            )
        current_store = loaded.store

        current_sources = self.gather_sources(
            fixture,
            current_store,
            story_records,
            contributors or (fixture.hg_scene_id,),
        )
        if current_sources.authority_source_fingerprint != proposal.source_snapshot_fingerprint:
            return UpdateCommitResult(
                success=False,
                code="stale_source",
                message="proposal source fingerprint does not match current authority",
            )
        if current_store.store_revision != proposal.prior_store_revision:
            return UpdateCommitResult(
                success=False,
                code="stale_revision",
                message="overlay store revision changed since proposal",
                store_revision=current_store.store_revision,
            )

        validation = validate_update_proposal_objective(
            proposal,
            policy_max_active_goals=policy.max_active_goals,
            policy_max_active_pressures=policy.max_active_pressures,
        )
        if not validation.ok:
            code = "budget_exceeded" if validation.over_budget else "integrity_invalid"
            return UpdateCommitResult(
                success=False,
                code=code,
                message="update proposal failed objective validation",
            )

        authority = build_assimilated_authority_from_snapshot(current_sources)
        materialized, materialize_validation = materialize_update_overlay(
            current_store,
            proposal,
            evaluation,
            assimilated_authority=authority,
            through_domain_commit_id=current_sources.through_domain_commit_id,
        )
        if materialized is None or not materialize_validation.ok:
            return UpdateCommitResult(
                success=False,
                code="integrity_invalid",
                message="update proposal could not be materialized",
            )

        if proposal.replan_required:
            if replan_proposal is None or replan_eval is None:
                return UpdateCommitResult(
                    success=False,
                    code="integrity_invalid",
                    message="replan proposal and evaluation required when replan_required",
                )
            replan_validation = validate_replan_proposal_objective(
                replan_proposal,
                policy_max_active_goals=policy.max_active_goals,
                policy_max_active_pressures=policy.max_active_pressures,
            )
            if not replan_validation.ok:
                code = "budget_exceeded" if replan_validation.over_budget else "integrity_invalid"
                return UpdateCommitResult(
                    success=False,
                    code=code,
                    message="replan proposal failed objective validation",
                )
            materialized, materialize_validation = materialize_replan_overlay(
                materialized,
                replan_proposal,
                replan_eval,
                assimilated_authority=authority,
                through_domain_commit_id=current_sources.through_domain_commit_id,
            )
            if materialized is None or not materialize_validation.ok:
                return UpdateCommitResult(
                    success=False,
                    code="integrity_invalid",
                    message="replan proposal could not be materialized",
                )

        integrity = self._overlay.validate_integrity(materialized, policy=policy)
        if not integrity.ok:
            code = "budget_exceeded" if integrity.over_budget else "integrity_invalid"
            return UpdateCommitResult(
                success=False,
                code=code,
                message="materialized overlay failed integrity validation",
            )

        replace_result = self._overlay.replace_snapshot(
            scope_id,
            materialized,
            expected_revision=current_store.store_revision,
            policy=policy,
        )

        outcome = (
            "semantic_no_change"
            if evaluation.overall_result == "no_change"
            else "semantic_replan"
            if proposal.replan_required
            else "semantic_update"
        )
        if forensic_handoff is not None:
            forensic_handoff.outcome = outcome
            forensic_handoff.source_snapshot = current_sources
            forensic_handoff.update_proposals.append(proposal.to_dict())
            forensic_handoff.update_evaluations.append(evaluation.to_dict())
            forensic_handoff.accepted_update_proposal_id = proposal.proposal_id
            if replan_proposal is not None:
                forensic_handoff.replan_proposals.append(replan_proposal.to_dict())
            if replan_eval is not None:
                forensic_handoff.replan_evaluations.append(replan_eval.to_dict())
                forensic_handoff.accepted_replan_proposal_id = replan_proposal.proposal_id
            forensic_handoff.materialized_store = materialized.to_dict()
            forensic_handoff.commit_result = {
                "success": replace_result.success,
                "error_code": replace_result.error_code,
                "prior_revision": replace_result.prior_revision,
                "new_revision": replace_result.new_revision,
            }

        if not replace_result.success:
            code = replace_result.error_code or "persistence_failed"
            mapped = "revision_conflict" if code == "revision_conflict" else "persistence_failed"
            return UpdateCommitResult(
                success=False,
                code=mapped,  # type: ignore[arg-type]
                message=replace_result.error_message or "update persistence failed",
                prior_revision=replace_result.prior_revision,
            )

        commit_code = (
            "semantic_no_change" if evaluation.overall_result == "no_change" else "committed"
        )
        return UpdateCommitResult(
            success=True,
            code=commit_code,  # type: ignore[arg-type]
            message="plot cognition overlay updated",
            store_revision=replace_result.new_revision,
            prior_revision=replace_result.prior_revision,
            load_status=LoadStatus.READY.value,
            forensic_outcome=outcome,
        )

"""Plot Cognition runtime orchestration service (#63)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .plot_cognition_orchestration_contract import (
    PLOT_COGNITION_PENDING_WORK_SCHEMA,
    PlotCognitionPendingWork,
)
from .plot_cognition_overlay_service import PlotCognitionOverlayService
from .plot_cognition_overlay_store import BoundednessPolicy, LoadStatus
from .plot_cognition_projection_batch import (
    CharacterProjectionSemanticResult,
    FinalizedProjectionBatch,
    PrepareProjectionBatchResult,
    finalize_batch_to_service_result,
    finalize_character_projection_batch,
    prepare_character_projection_batch,
)
from .plot_cognition_projection_contract import (
    CharacterAdvisoryCandidate,
    ProjectionBudget,
)
from .plot_cognition_projection_service import (
    collect_overlay_character_candidates,
    project_director_overlay,
)
from .session_state import LiveSession, RoundFixture
from .storyteller_packaging_mapper import map_storyteller_package_to_contributions
from .storyteller_packaging_policy import StorytellerPackagingConsumer


@dataclass(frozen=True)
class OverlayFreshnessStatus:
    fresh: bool
    reason: str
    pending_work: PlotCognitionPendingWork | None = None


@dataclass(frozen=True)
class PendingWorkApplyResult:
    success: bool
    code: str
    message: str
    store_revision: int | None = None
    prior_revision: int | None = None
    overlay_mutated: bool = False


class PlotCognitionOrchestrationService:
    """Coordinates overlay freshness, candidate collection, and split-phase projection."""

    def __init__(
        self,
        overlay_service: PlotCognitionOverlayService | None,
    ) -> None:
        self._overlay = overlay_service

    _DEFAULT_POLICY = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)

    def build_post_commit_pending_work(
        self,
        fixture: LiveSession,
        *,
        domain_commit_id: str,
        work_kind: str = "update",
        authority_source_fingerprint: str = "",
    ) -> PlotCognitionPendingWork | None:
        scope_id = str(fixture.plot_cognition_scope_id or "").strip()
        if not scope_id or self._overlay is None:
            return None
        return PlotCognitionPendingWork(
            schema=PLOT_COGNITION_PENDING_WORK_SCHEMA,
            plot_cognition_scope_id=scope_id,
            trigger_domain_commit_id=domain_commit_id,
            work_kind=work_kind,  # type: ignore[arg-type]
            recorded_at_continuity_version=int(fixture.continuity_version),
            authority_source_fingerprint=authority_source_fingerprint or domain_commit_id,
        )

    def apply_post_commit_pending_work(
        self,
        fixture: LiveSession,
        pending: PlotCognitionPendingWork,
        *,
        expected_revision: int,
    ) -> PendingWorkApplyResult:
        scope_id = str(fixture.plot_cognition_scope_id or "").strip()
        if not scope_id or self._overlay is None:
            return PendingWorkApplyResult(
                success=False,
                code="overlay_unavailable",
                message="plot cognition overlay unavailable",
            )
        loaded = self._overlay.load(scope_id, policy=self._DEFAULT_POLICY)
        if loaded.status != LoadStatus.READY or loaded.store is None:
            return PendingWorkApplyResult(
                success=True,
                code="queued_without_overlay",
                message="pending work recorded; overlay store not ready for mutation",
                prior_revision=expected_revision,
                store_revision=expected_revision,
                overlay_mutated=False,
            )
        store = loaded.store
        if int(store.store_revision) != int(expected_revision):
            return PendingWorkApplyResult(
                success=False,
                code="stale_revision",
                message="overlay revision changed before pending-work apply",
                prior_revision=expected_revision,
                store_revision=int(store.store_revision),
            )
        store.pending_work = pending.to_dict()
        replace_result = self._overlay.replace_snapshot(
            scope_id,
            store,
            expected_revision=expected_revision,
            policy=self._DEFAULT_POLICY,
        )
        if not replace_result.success:
            return PendingWorkApplyResult(
                success=False,
                code=str(replace_result.error_code or "persistence_failed"),
                message=str(replace_result.error_message or "pending-work overlay mutation failed"),
                prior_revision=replace_result.prior_revision,
                store_revision=replace_result.new_revision,
            )
        return PendingWorkApplyResult(
            success=True,
            code="committed",
            message="pending work applied to overlay",
            prior_revision=replace_result.prior_revision,
            store_revision=replace_result.new_revision,
            overlay_mutated=True,
        )

    def record_post_commit_pending_work(
        self,
        fixture: LiveSession,
        *,
        domain_commit_id: str,
        work_kind: str = "update",
        authority_source_fingerprint: str = "",
    ) -> PlotCognitionPendingWork | None:
        """Direct apply without WAFI — test/offline helpers only; production uses WAFI integration."""
        pending = self.build_post_commit_pending_work(
            fixture,
            domain_commit_id=domain_commit_id,
            work_kind=work_kind,
            authority_source_fingerprint=authority_source_fingerprint,
        )
        if pending is None:
            return None
        scope_id = str(fixture.plot_cognition_scope_id or "").strip()
        if not scope_id or self._overlay is None:
            return pending
        loaded = self._overlay.load(scope_id, policy=self._DEFAULT_POLICY)
        prior_revision = loaded.store.store_revision if loaded.store is not None else 0
        result = self.apply_post_commit_pending_work(
            fixture,
            pending,
            expected_revision=prior_revision,
        )
        if not result.success and result.code not in {"queued_without_overlay"}:
            return None
        return pending

    def clear_pending_work(self, fixture: LiveSession) -> None:
        scope_id = str(fixture.plot_cognition_scope_id or "").strip()
        if not scope_id or self._overlay is None:
            return
        loaded = self._overlay.load(scope_id, policy=BoundednessPolicy(max_active_goals=8, max_active_pressures=8))
        if loaded.status != LoadStatus.READY or loaded.store is None:
            return
        store = loaded.store
        store.pending_work = None
        self._overlay.replace_snapshot(
            scope_id,
            store,
            expected_revision=store.store_revision,
            policy=BoundednessPolicy(max_active_goals=8, max_active_pressures=8),
        )

    def assess_overlay_freshness(self, fixture: LiveSession) -> OverlayFreshnessStatus:
        scope_id = str(fixture.plot_cognition_scope_id or "").strip()
        if not scope_id or self._overlay is None:
            return OverlayFreshnessStatus(fresh=True, reason="overlay_unconfigured")
        loaded = self._overlay.load(scope_id, policy=BoundednessPolicy(max_active_goals=8, max_active_pressures=8))
        if loaded.status != LoadStatus.READY or loaded.store is None:
            return OverlayFreshnessStatus(fresh=True, reason=f"overlay_{loaded.status.value}")
        raw_pending = getattr(loaded.store, "pending_work", None)
        if not raw_pending:
            return OverlayFreshnessStatus(fresh=True, reason="no_pending_work")
        pending = PlotCognitionPendingWork.from_dict(raw_pending)
        if pending.required_before_projection:
            return OverlayFreshnessStatus(
                fresh=False,
                reason="pending_plot_cognition_work",
                pending_work=pending,
            )
        return OverlayFreshnessStatus(fresh=True, reason="pending_not_blocking")

    def collect_character_candidates(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        character_id: str,
        overlay_view: Any | None = None,
        include_model_a: bool = True,
        supplemental_global_candidates: tuple[CharacterAdvisoryCandidate, ...] = (),
    ) -> tuple[CharacterAdvisoryCandidate, ...]:
        """Merge provenance-separated candidate paths."""
        candidates: list[CharacterAdvisoryCandidate] = []
        view = overlay_view
        if view is not None:
            candidates.extend(
                collect_overlay_character_candidates(
                    view,
                    character_id=character_id,
                    supplemental_candidates=supplemental_global_candidates,
                )
            )
        if include_model_a:
            from .storyteller_round_packaging import active_storyteller_package

            package = active_storyteller_package(rnd)
            if package is not None:
                from .storyteller_packaging_mapper import collect_model_a_character_candidates

                candidates.extend(
                    collect_model_a_character_candidates(
                        package,
                        character_id=character_id,
                    )
                )
        candidates.extend(supplemental_global_candidates)
        return tuple(candidates)

    def prepare_projection(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        manifest_id: str,
        character_id: str,
        candidates: tuple[CharacterAdvisoryCandidate, ...],
        budget: ProjectionBudget,
        overlay_revision: int | None = None,
        authority_fingerprint: str | None = None,
    ) -> PrepareProjectionBatchResult:
        return prepare_character_projection_batch(
            fixture,
            manifest_id=manifest_id,
            character_id=character_id,
            candidates=candidates,
            budget=budget,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint=authority_fingerprint,
            overlay_revision=overlay_revision,
        )

    def finalize_projection(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        batch_id: str,
        semantic_results: tuple[CharacterProjectionSemanticResult, ...],
        **kwargs: Any,
    ) -> FinalizedProjectionBatch:
        return finalize_character_projection_batch(
            fixture,
            batch_id=batch_id,
            semantic_results=semantic_results,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            **kwargs,
        )

    def director_overlay_contributions(
        self,
        view: Any,
        *,
        manifest_id: str,
        freshness: OverlayFreshnessStatus,
    ) -> tuple[Any, ...]:
        if not freshness.fresh:
            return ()
        return project_director_overlay(view, manifest_id=manifest_id)

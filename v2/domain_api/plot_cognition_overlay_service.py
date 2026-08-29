"""Plot Cognition Overlay persistence integrity and boundedness service (#59)."""

from __future__ import annotations

from .plot_cognition_overlay_repository import (
    PersistenceError,
    PlotCognitionOverlayRepository,
    RevisionConflictError,
)
from .plot_cognition_overlay_store import (
    BoundednessPolicy,
    IntegrityReport,
    LoadResult,
    LoadStatus,
    OperativePlotCognitionView,
    PlotCognitionOverlayStore,
    ReplaceResult,
    build_operative_view,
    classify_load_status,
    empty_store,
    is_assimilation_current,
    is_assimilation_stale,
    validate_boundedness,
)
from .plot_cognition_scope_lock import PlotCognitionScopeLockRegistry


class PlotCognitionOverlayService:
    """Integrity, boundedness, and snapshot replacement for Plot Cognition Overlay."""

    def __init__(
        self,
        repository: PlotCognitionOverlayRepository,
        *,
        scope_locks: PlotCognitionScopeLockRegistry | None = None,
    ) -> None:
        self._repository = repository
        self._scope_locks = scope_locks or PlotCognitionScopeLockRegistry()

    def load(
        self,
        plot_cognition_scope_id: str,
        *,
        policy: BoundednessPolicy,
    ) -> LoadResult:
        raw = self._repository.load_raw(plot_cognition_scope_id)
        if raw.status == "absent":
            store = empty_store(plot_cognition_scope_id)
            integrity = validate_boundedness(store, policy=policy)
            return LoadResult(
                status=LoadStatus.ABSENT,
                store=store,
                integrity=integrity,
            )
        if raw.status == "unsupported_version":
            return LoadResult(
                status=LoadStatus.UNSUPPORTED_VERSION,
                store=None,
                integrity=IntegrityReport(ok=False, violations=raw.diagnostics),
                diagnostics=raw.diagnostics,
            )
        if raw.status == "corrupt":
            return LoadResult(
                status=LoadStatus.CORRUPT,
                store=None,
                integrity=IntegrityReport(ok=False, violations=raw.diagnostics),
                diagnostics=raw.diagnostics,
                quarantine_path=raw.quarantine_path,
            )
        assert raw.payload is not None
        store = self._repository.parse_store(raw.payload)
        integrity = validate_boundedness(store, policy=policy)
        status = classify_load_status(
            raw_present=True,
            envelope_ok=True,
            unsupported_version=False,
            integrity=integrity,
        )
        return LoadResult(
            status=status,
            store=store,
            integrity=integrity,
            diagnostics=integrity.violations,
        )

    def replace_snapshot(
        self,
        plot_cognition_scope_id: str,
        store: PlotCognitionOverlayStore,
        *,
        expected_revision: int,
        policy: BoundednessPolicy,
    ) -> ReplaceResult:
        if store.plot_cognition_scope_id != plot_cognition_scope_id:
            integrity = IntegrityReport(
                ok=False,
                violations=("plot_cognition_scope_id_mismatch",),
            )
            return ReplaceResult(
                success=False,
                prior_revision=expected_revision,
                new_revision=None,
                integrity=integrity,
                error_code="scope_mismatch",
                error_message="store scope id does not match request scope id",
            )

        integrity = validate_boundedness(store, policy=policy)
        if not integrity.ok:
            error_code = "budget_exceeded" if integrity.over_budget else "integrity_invalid"
            return ReplaceResult(
                success=False,
                prior_revision=expected_revision,
                new_revision=None,
                integrity=integrity,
                error_code=error_code,
                error_message="replacement snapshot failed integrity validation",
            )

        current = self.load(plot_cognition_scope_id, policy=policy)
        if current.status in {LoadStatus.CORRUPT, LoadStatus.UNSUPPORTED_VERSION}:
            return ReplaceResult(
                success=False,
                prior_revision=expected_revision,
                new_revision=None,
                integrity=current.integrity,
                error_code=current.status.value,
                error_message=f"existing store status {current.status.value} blocks replacement",
            )
        if current.status == LoadStatus.DEGRADED and current.store is not None:
            # Allow repair only when replacement snapshot is fully valid (checked above).
            pass

        with self._scope_locks.scope_lock(plot_cognition_scope_id):
            try:
                new_revision = self._repository.save_raw(
                    plot_cognition_scope_id,
                    store.to_dict(),
                    expected_revision=expected_revision,
                )
            except RevisionConflictError as exc:
                return ReplaceResult(
                    success=False,
                    prior_revision=expected_revision,
                    new_revision=None,
                    integrity=integrity,
                    error_code="revision_conflict",
                    error_message=str(exc),
                )
            except PersistenceError as exc:
                return ReplaceResult(
                    success=False,
                    prior_revision=expected_revision,
                    new_revision=None,
                    integrity=integrity,
                    error_code="persistence_error",
                    error_message=str(exc),
                )

        return ReplaceResult(
            success=True,
            prior_revision=expected_revision,
            new_revision=new_revision,
            integrity=integrity,
        )

    def validate_integrity(
        self,
        store: PlotCognitionOverlayStore,
        *,
        policy: BoundednessPolicy,
    ) -> IntegrityReport:
        return validate_boundedness(store, policy=policy)

    def operative_view(
        self,
        store: PlotCognitionOverlayStore,
        *,
        policy: BoundednessPolicy,
        load_status: LoadStatus,
    ) -> OperativePlotCognitionView | None:
        if load_status != LoadStatus.READY:
            return None
        integrity = validate_boundedness(store, policy=policy)
        if not integrity.ok:
            return None
        return build_operative_view(store)

    def is_assimilation_current(
        self,
        store: PlotCognitionOverlayStore,
        *,
        current_domain_commit_id: str | None,
    ) -> bool:
        return is_assimilation_current(
            store,
            current_domain_commit_id=current_domain_commit_id,
        )

    def is_assimilation_stale(
        self,
        store: PlotCognitionOverlayStore,
        *,
        current_domain_commit_id: str | None,
    ) -> bool:
        return is_assimilation_stale(
            store,
            current_domain_commit_id=current_domain_commit_id,
        )

"""Plot Cognition forensic integration at Domain finalize boundaries (#64).

Imported only from lifecycle/orchestration API layers — not from packaging modules.
"""

from __future__ import annotations

from typing import Any

from .plot_cognition_forensics_capture import (
    bounded_overlay_snapshot,
    capture_authority_projection_verbatim,
    capture_epistemic_envelope,
)
from .plot_cognition_forensics_service import PlotCognitionForensicsService
from .session_state import LiveSession, RoundFixture


def get_forensics_service(kernel: Any) -> PlotCognitionForensicsService | None:
    store = getattr(kernel, "store", None)
    if store is not None:
        getter = getattr(store, "plot_cognition_forensics_service", None)
        if isinstance(getter, PlotCognitionForensicsService):
            return getter
        if getter is not None and not callable(getter):
            return getter  # type: ignore[return-value]
        return getattr(store, "_plot_cognition_forensics", None)
    return getattr(kernel, "plot_cognition_forensics", None)


def _completion_payload(
    forensics: PlotCognitionForensicsService,
    scope_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    index = forensics.repository.load_index(scope_id)
    completion_id = (
        (index.get("by_idempotency_key") or {}).get(idempotency_key, {}).get("completion")
    )
    if not completion_id:
        return {}
    record = forensics.repository.load_record(scope_id, str(completion_id))
    if not record:
        return {}
    payload = record.get("payload")
    return dict(payload) if isinstance(payload, dict) else {}


def _mutation_already_applied(result: Any, intent_payload: dict[str, Any]) -> bool:
    code = getattr(result, "code", None) or (
        result.get("code") if isinstance(result, dict) else None
    )
    if code in {"already_initialized", "reconciliation_established"}:
        return True
    if code == "stale_revision":
        prior = intent_payload.get("prior_revision")
        current = getattr(result, "store_revision", None) or (
            result.get("store_revision") if isinstance(result, dict) else None
        )
        if prior is not None and current is not None and int(current) > int(prior):
            return True
    return False


def _base_correlation(fixture: LiveSession, **extra: Any) -> dict[str, Any]:
    correlation = {
        "plot_cognition_scope_id": str(fixture.plot_cognition_scope_id or ""),
        "hg_session_id": fixture.hg_session_id,
        "hg_scene_id": fixture.hg_scene_id,
    }
    correlation.update({key: value for key, value in extra.items() if value is not None})
    return correlation


def ensure_activation(kernel: Any, fixture: LiveSession, overlay_store_dict: dict[str, Any] | None) -> None:
    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return
    forensics.ensure_scope_activation(
        scope_id,
        overlay_store_dict=overlay_store_dict,
        hg_session_id=fixture.hg_session_id,
    )
    forensics.attach_session(scope_id, fixture.hg_session_id)
    forensics.reconcile_incomplete_wafi(scope_id)


def wafi_initialize(
    kernel: Any,
    fixture: LiveSession,
    *,
    proposal: Any,
    sources: Any,
    policy: Any,
    commit_fn: Any,
) -> Any:
    from .plot_cognition_initialization_contract import InitializationCommitResult

    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return commit_fn()

    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    loaded = overlay.load(scope_id, policy=policy) if overlay else None
    prior_revision = loaded.store.store_revision if loaded and loaded.store else 0
    ensure_activation(kernel, fixture, loaded.store.to_dict() if loaded and loaded.store else None)

    idempotency_key = f"{scope_id}:init:{proposal.source_snapshot_fingerprint}"
    authority_artifact = forensics.store_semantic_artifact(
        scope_id,
        capture_authority_projection_verbatim(fixture, None, None),
    )
    intent_payload = {
        "proposal": proposal.to_dict(),
        "source_snapshot": sources.to_dict(),
        "prior_revision": prior_revision,
        "authority_artifact_id": authority_artifact,
    }
    correlation = _base_correlation(fixture, overlay_revision_before=prior_revision)

    mutation_holder: dict[str, Any] = {}

    def mutation():
        mutation_holder["result"] = commit_fn()
        return mutation_holder["result"]

    def completion_builder(result: Any) -> dict[str, Any]:
        overlay_after = overlay.load(scope_id, policy=policy) if overlay else None
        store_dict = overlay_after.store.to_dict() if overlay_after and overlay_after.store else {}
        return {
            "accepted_proposal_id": proposal.proposal_id,
            "store_revision": result.store_revision,
            "prior_revision": result.prior_revision,
            "resulting_snapshot": bounded_overlay_snapshot(store_dict),
            "code": result.code,
        }

    wafi = forensics.execute_wafi_mutation(
        plot_cognition_scope_id=scope_id,
        idempotency_key=idempotency_key,
        operation_kind="initialization",
        intent_payload=intent_payload,
        correlation=correlation,
        mutation_fn=mutation,
        completion_builder=completion_builder,
    )
    if wafi.replayed:
        completion = _completion_payload(forensics, scope_id, idempotency_key)
        return InitializationCommitResult(
            success=True,
            code="already_initialized",
            message="mutation already completed",
            store_revision=completion.get("store_revision"),
            prior_revision=completion.get("prior_revision"),
        )
    if not wafi.ok:
        return InitializationCommitResult(
            success=False,
            code="forensic_persistence_failed",  # type: ignore[arg-type]
            message=wafi.message,
        )
    return mutation_holder["result"]


def wafi_update_like(
    kernel: Any,
    fixture: LiveSession,
    *,
    operation_kind: str,
    idempotency_suffix: str,
    intent_payload: dict[str, Any],
    correlation_extra: dict[str, Any],
    commit_fn: Any,
    completion_extra: dict[str, Any] | None = None,
) -> tuple[Any, bool]:
    """Returns (result, forensic_ok)."""
    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return commit_fn(), True

    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    from .plot_cognition_overlay_store import BoundednessPolicy

    policy = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)
    loaded = overlay.load(scope_id, policy=policy) if overlay else None
    prior_revision = loaded.store.store_revision if loaded and loaded.store else 0
    ensure_activation(kernel, fixture, loaded.store.to_dict() if loaded and loaded.store else None)

    idempotency_key = f"{scope_id}:{operation_kind}:{idempotency_suffix}"
    correlation = _base_correlation(
        fixture,
        overlay_revision_before=prior_revision,
        **correlation_extra,
    )
    intent_payload = {**intent_payload, "prior_revision": prior_revision}

    mutation_holder: dict[str, Any] = {}

    def mutation():
        mutation_holder["result"] = commit_fn()
        return mutation_holder["result"]

    def completion_builder(result: Any) -> dict[str, Any]:
        overlay_after = overlay.load(scope_id, policy=policy) if overlay else None
        store_dict = overlay_after.store.to_dict() if overlay_after and overlay_after.store else {}
        payload = {
            "store_revision": getattr(result, "store_revision", None),
            "prior_revision": getattr(result, "prior_revision", prior_revision),
            "resulting_snapshot": bounded_overlay_snapshot(store_dict),
            "code": getattr(result, "code", None),
            "message": getattr(result, "message", None),
        }
        if completion_extra:
            payload.update(completion_extra)
        return payload

    wafi = forensics.execute_wafi_mutation(
        plot_cognition_scope_id=scope_id,
        idempotency_key=idempotency_key,
        operation_kind=operation_kind,
        intent_payload=intent_payload,
        correlation=correlation,
        mutation_fn=mutation,
        completion_builder=completion_builder,
    )
    if wafi.replayed:
        completion = _completion_payload(forensics, scope_id, idempotency_key)
        from .plot_cognition_update_contract import UpdateCommitResult

        return UpdateCommitResult(
            success=True,
            code="committed",
            message="mutation already completed",
            store_revision=completion.get("store_revision"),
            prior_revision=completion.get("prior_revision"),
        ), True
    if not wafi.ok:
        if "result" in mutation_holder:
            return mutation_holder["result"], False
        return None, False
    return mutation_holder["result"], True


def record_projection_decisions(
    kernel: Any,
    fixture: LiveSession,
    rnd: RoundFixture,
    *,
    batch_id: str,
    forensic_payload: dict[str, Any],
    inference_evidence_by_candidate: dict[str, str] | None = None,
) -> bool:
    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return True

    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    from .plot_cognition_overlay_store import BoundednessPolicy, LoadStatus

    policy = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)
    loaded = overlay.load(scope_id, policy=policy) if overlay else None
    ensure_activation(kernel, fixture, loaded.store.to_dict() if loaded and loaded.store else None)

    character_id = forensic_payload.get("character_id")
    correlation = _base_correlation(
        fixture,
        hg_round_id=rnd.hg_round_id,
        turn_index=int(rnd.turn_index),
        batch_id=batch_id,
        character_id=character_id,
        overlay_revision_before=loaded.store.store_revision if loaded and loaded.store else None,
    )
    idempotency_key = f"{scope_id}:projection:{batch_id}:finalize"
    inference_refs = []
    if inference_evidence_by_candidate:
        for candidate_id, evidence_id in inference_evidence_by_candidate.items():
            inference_refs.append(
                {"evidence_id": evidence_id, "role": f"layer_b:{candidate_id}"}
            )
    result = forensics.record_semantic_decision(
        plot_cognition_scope_id=scope_id,
        idempotency_key=idempotency_key,
        record_class="consumer_decision",
        operation_kind="projection_evaluate",
        correlation=correlation,
        payload=forensic_payload,
        inference_evidence_refs=inference_refs,
    )
    return result.ok


def record_pending_work_mutation(
    kernel: Any,
    fixture: LiveSession,
    *,
    domain_commit_id: str,
    pending_work: dict[str, Any],
    prior_store_dict: dict[str, Any] | None,
) -> bool:
    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return True
    ensure_activation(kernel, fixture, prior_store_dict)
    idempotency_key = f"{scope_id}:pending:{domain_commit_id}"
    correlation = _base_correlation(fixture, domain_commit_id=domain_commit_id)
    result = forensics.record_semantic_decision(
        plot_cognition_scope_id=scope_id,
        idempotency_key=idempotency_key,
        record_class="operational_mutation",
        operation_kind="pending_work",
        correlation=correlation,
        payload={
            "pending_work": pending_work,
            "prior_snapshot": bounded_overlay_snapshot(prior_store_dict),
        },
    )
    return result.ok

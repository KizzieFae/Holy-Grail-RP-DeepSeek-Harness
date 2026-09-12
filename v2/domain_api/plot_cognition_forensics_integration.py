"""Plot Cognition forensic integration at Domain finalize boundaries (#64).

Imported only from lifecycle/orchestration API layers — not from packaging modules.
"""

from __future__ import annotations

from typing import Any, Callable

from .plot_cognition_forensics_capture import (
    bounded_overlay_snapshot,
    capture_authority_projection_verbatim,
    capture_epistemic_envelope,
)
from .plot_cognition_forensics_service import PlotCognitionForensicsService, WafiResult
from .session_state import LiveSession, RoundFixture


def format_plot_cognition_wafi_finalize_response(
    result: Any,
    forensic_ok: bool,
    wafi: WafiResult | None,
    *,
    persistence_message: str,
) -> dict[str, Any]:
    """Map WAFI/update outcomes to public finalize responses (#68)."""
    violations = tuple(getattr(result, "violations", ()) or ())
    base: dict[str, Any] = {
        "accepted": bool(getattr(result, "success", False)),
        "code": getattr(result, "code", None),
        "message": getattr(result, "message", None),
        "store_revision": getattr(result, "store_revision", None),
    }
    if violations:
        base["violations"] = list(violations)
    if forensic_ok:
        return base
    if wafi is not None and wafi.code == "mutation_failed" and result is not None:
        return {
            **base,
            "accepted": False,
            "code": getattr(result, "code", "integrity_invalid"),
            "message": getattr(result, "message", "plot cognition update rejected"),
            "forensic_stage": wafi.code,
            "forensic_message": wafi.message,
        }
    return {
        "accepted": False,
        "code": "forensic_persistence_failed",
        "message": wafi.message if wafi is not None else persistence_message,
        "store_revision": getattr(result, "store_revision", None) if result is not None else None,
        "forensic_stage": wafi.code if wafi is not None else None,
        "forensic_message": wafi.message if wafi is not None else None,
        **({"violations": list(violations)} if violations else {}),
    }


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
    before_completion_snapshot: Callable[[Any], None] | None = None,
) -> tuple[Any, bool, WafiResult | None]:
    """Returns (result, forensic_ok, wafi_result)."""
    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return commit_fn(), True, None

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
        if before_completion_snapshot is not None:
            before_completion_snapshot(result)
        overlay_after = overlay.load(scope_id, policy=policy) if overlay else None
        store_dict = overlay_after.store.to_dict() if overlay_after and overlay_after.store else {}
        payload = {
            "store_revision": getattr(result, "store_revision", None),
            "prior_revision": getattr(result, "prior_revision", prior_revision),
            "resulting_snapshot": bounded_overlay_snapshot(store_dict),
            "code": getattr(result, "code", None),
            "message": getattr(result, "message", None),
        }
        violations = tuple(getattr(result, "violations", ()) or ())
        if violations:
            payload["violations"] = list(violations)
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
        ), True, wafi
    if not wafi.ok:
        if "result" in mutation_holder:
            return mutation_holder["result"], False, wafi
        return None, False, wafi
    return mutation_holder["result"], True, wafi


def record_plot_cognition_orchestration_decision(
    kernel: Any,
    fixture: LiveSession,
    *,
    plan_operation: str,
    reason: str,
    freshness_status: str | None = None,
    inference_id: str | None = None,
    domain_commit_id: str | None = None,
) -> bool:
    """Record non-mutation orchestration gate decisions (#166 Lane 1)."""
    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return True
    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    from .plot_cognition_overlay_store import BoundednessPolicy

    policy = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)
    loaded = overlay.load(scope_id, policy=policy) if overlay else None
    ensure_activation(kernel, fixture, loaded.store.to_dict() if loaded and loaded.store else None)
    correlation = _base_correlation(
        fixture,
        domain_commit_id=domain_commit_id,
        overlay_revision_before=loaded.store.store_revision if loaded and loaded.store else None,
    )
    suffix = inference_id or plan_operation or "orchestration"
    idempotency_key = f"{scope_id}:orchestration:{suffix}:{plan_operation}"
    result = forensics.record_semantic_decision(
        plot_cognition_scope_id=scope_id,
        idempotency_key=idempotency_key,
        record_class="semantic_decision",
        operation_kind="freshness_barrier",
        correlation=correlation,
        payload={
            "decision": "deterministic_skip",
            "plan_operation": plan_operation,
            "reason": reason,
            "freshness_status": freshness_status,
            "mutation_lifecycle_entered": False,
        },
        inference_evidence_refs=[],
    )
    return result.ok


def record_layer_b_reuse_decision(
    kernel: Any,
    fixture: LiveSession,
    rnd: RoundFixture,
    *,
    batch_id: str,
    evaluation_pass_id: str,
    candidate_id: str,
    reuse_key_digest: str,
    decision: str,
    prior_inference_evidence_id: str | None = None,
    inference_evidence_id: str | None = None,
) -> str | None:
    """Record invoke/reuse/invalidation for Layer B epistemic evaluation (#166 Lane 2)."""
    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        return None
    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    from .plot_cognition_overlay_store import BoundednessPolicy

    policy = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)
    loaded = overlay.load(scope_id, policy=policy) if overlay else None
    ensure_activation(kernel, fixture, loaded.store.to_dict() if loaded and loaded.store else None)
    correlation = _base_correlation(
        fixture,
        hg_round_id=rnd.hg_round_id,
        turn_index=int(rnd.turn_index),
        batch_id=batch_id,
        candidate_id=candidate_id,
        overlay_revision_before=loaded.store.store_revision if loaded and loaded.store else None,
    )
    idempotency_key = f"{scope_id}:layer_b:{batch_id}:{evaluation_pass_id}:{decision}"
    inference_refs = []
    if prior_inference_evidence_id:
        inference_refs.append(
            {"evidence_id": prior_inference_evidence_id, "role": "layer_b_reuse_source"}
        )
    if inference_evidence_id:
        inference_refs.append({"evidence_id": inference_evidence_id, "role": "layer_b_eval"})
    result = forensics.record_semantic_decision(
        plot_cognition_scope_id=scope_id,
        idempotency_key=idempotency_key,
        record_class="consumer_decision",
        operation_kind="projection_evaluate",
        correlation=correlation,
        payload={
            "decision": decision,
            "reuse_key_digest": reuse_key_digest,
            "evaluation_pass_id": evaluation_pass_id,
            "candidate_id": candidate_id,
            "prior_inference_evidence_id": prior_inference_evidence_id,
        },
        inference_evidence_refs=inference_refs,
    )
    return result.record_id if result.ok else None


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


def wafi_record_post_commit_pending_work(
    kernel: Any,
    fixture: LiveSession,
    *,
    domain_commit_id: str,
) -> dict[str, Any]:
    """Production post-commit pending-work path with full WAFI ordering."""
    from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService

    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    if overlay is None:
        return {"recorded": False, "reason": "plot_cognition_overlay_unavailable"}
    orch = PlotCognitionOrchestrationService(overlay)
    pending = orch.build_post_commit_pending_work(fixture, domain_commit_id=domain_commit_id)
    if pending is None:
        return {"recorded": False, "reason": "plot_cognition_scope_unconfigured"}

    forensics = get_forensics_service(kernel)
    scope_id = str(fixture.plot_cognition_scope_id or "")
    if forensics is None or not scope_id:
        result = orch.apply_post_commit_pending_work(fixture, pending, expected_revision=0)
        return {
            "recorded": result.success,
            "pending_work": pending.to_dict() if result.success else None,
            "code": result.code,
            "message": result.message,
        }

    from .plot_cognition_overlay_store import BoundednessPolicy

    policy = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)
    loaded = overlay.load(scope_id, policy=policy)
    prior_revision = loaded.store.store_revision if loaded and loaded.store else 0
    prior_store_dict = loaded.store.to_dict() if loaded and loaded.store else None
    ensure_activation(kernel, fixture, prior_store_dict)

    idempotency_key = f"{scope_id}:pending:{domain_commit_id}"
    correlation = _base_correlation(
        fixture,
        domain_commit_id=domain_commit_id,
        overlay_revision_before=prior_revision,
    )
    intent_payload = {
        "pending_work": pending.to_dict(),
        "prior_snapshot": bounded_overlay_snapshot(prior_store_dict),
        "prior_revision": prior_revision,
        "trigger_domain_commit_id": domain_commit_id,
    }

    mutation_holder: dict[str, Any] = {}

    def mutation():
        mutation_holder["result"] = orch.apply_post_commit_pending_work(
            fixture,
            pending,
            expected_revision=prior_revision,
        )
        return mutation_holder["result"]

    def completion_builder(result: Any) -> dict[str, Any]:
        overlay_after = overlay.load(scope_id, policy=policy)
        store_dict = (
            overlay_after.store.to_dict()
            if overlay_after and overlay_after.store is not None
            else {}
        )
        return {
            "pending_work": pending.to_dict(),
            "prior_snapshot": bounded_overlay_snapshot(prior_store_dict),
            "resulting_snapshot": bounded_overlay_snapshot(store_dict),
            "store_revision": getattr(result, "store_revision", None),
            "prior_revision": getattr(result, "prior_revision", prior_revision),
            "overlay_mutated": getattr(result, "overlay_mutated", False),
            "code": getattr(result, "code", None),
        }

    wafi = forensics.execute_wafi_mutation(
        plot_cognition_scope_id=scope_id,
        idempotency_key=idempotency_key,
        operation_kind="pending_work",
        intent_payload=intent_payload,
        correlation=correlation,
        mutation_fn=mutation,
        completion_builder=completion_builder,
    )
    if wafi.replayed:
        completion = _completion_payload(forensics, scope_id, idempotency_key)
        return {
            "recorded": True,
            "replayed": True,
            "pending_work": completion.get("pending_work") or pending.to_dict(),
            "store_revision": completion.get("store_revision"),
        }
    if not wafi.ok:
        mutation_result = mutation_holder.get("result")
        return {
            "recorded": False,
            "code": wafi.code,
            "message": wafi.message,
            "pending_work": None,
            "store_revision": getattr(mutation_result, "store_revision", None),
        }
    mutation_result = mutation_holder["result"]
    if not getattr(mutation_result, "success", False):
        return {
            "recorded": False,
            "code": getattr(mutation_result, "code", "mutation_failed"),
            "message": getattr(mutation_result, "message", "pending-work mutation failed"),
            "pending_work": None,
        }
    return {
        "recorded": True,
        "pending_work": pending.to_dict(),
        "store_revision": mutation_result.store_revision,
    }

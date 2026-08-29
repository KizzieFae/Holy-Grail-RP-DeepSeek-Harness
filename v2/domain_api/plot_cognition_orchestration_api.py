"""Plot Cognition orchestration HTTP/kernel handlers (#63)."""

from __future__ import annotations

from typing import Any

from .plot_cognition_orchestration_contract import RegenerationGuidance
from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService
from .plot_cognition_projection_batch import (
    CharacterProjectionSemanticResult,
    clear_prepared_batches_for_tests,
    finalize_character_projection_batch,
    get_prepared_batch,
    prepare_character_projection_batch,
)
from .plot_cognition_projection_runtime import (
    collect_regeneration_inputs,
    collect_registered_results_for_finalize,
    finalize_projection_regeneration,
    prepare_projection_regeneration,
    register_projection_semantic_result,
)
from .plot_cognition_projection_contract import (
    ProjectionBudget,
    SemanticEvaluationResult,
)
from .session_state import LiveSession, RoundFixture


def _orchestration(kernel: Any) -> PlotCognitionOrchestrationService | None:
    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    if overlay is None:
        return None
    return PlotCognitionOrchestrationService(overlay)


def prepare_plot_cognition_projection(
    kernel: Any,
    fixture: LiveSession,
    rnd: RoundFixture,
    data: dict[str, Any],
) -> dict[str, Any]:
    orch = _orchestration(kernel)
    if orch is None:
        return {"accepted": False, "reason": "plot_cognition_overlay_unavailable"}
    character_id = str(data.get("character_id", ""))
    manifest_id = str(data.get("manifest_id", f"manifest-plot-proj-{rnd.hg_round_id}"))
    budget_raw = data.get("budget") or {}
    budget = ProjectionBudget(
        max_evaluation_candidates=int(budget_raw.get("max_evaluation_candidates", 8)),
        max_projection_candidates=int(budget_raw.get("max_projection_candidates", 5)),
    )
    view = None
    overlay_revision: int | None = None
    loaded = None
    overlay = kernel.cognition.plot_cognition_overlay
    if overlay is not None:
        from .plot_cognition_overlay_store import BoundednessPolicy, LoadStatus

        scope_id = str(fixture.plot_cognition_scope_id or "")
        loaded = overlay.load(scope_id, policy=BoundednessPolicy(max_active_goals=8, max_active_pressures=8))
        if loaded.status == LoadStatus.READY and loaded.store is not None:
            view = overlay.operative_view(
                loaded.store,
                policy=BoundednessPolicy(max_active_goals=8, max_active_pressures=8),
                load_status=loaded.status,
            )
            overlay_revision = loaded.store.store_revision
    candidates = orch.collect_character_candidates(
        fixture,
        rnd,
        character_id=character_id,
        overlay_view=view,
        include_model_a=bool(data.get("include_model_a", True)),
    )
    prepared = orch.prepare_projection(
        fixture,
        rnd,
        manifest_id=manifest_id,
        character_id=character_id,
        candidates=candidates,
        budget=budget,
        overlay_revision=overlay_revision,
        authority_fingerprint=data.get("authority_fingerprint"),
    )
    return {
        "accepted": True,
        "batch_id": prepared.batch.batch_id,
        "batch": {
            "batch_id": prepared.batch.batch_id,
            "character_id": prepared.batch.character_id,
            "manifest_id": prepared.batch.manifest_id,
            "binding_digest": prepared.batch.binding_digest,
            "evaluation_pass_ids": [item.evaluation_pass_id for item in prepared.batch.items],
        },
        "evaluator_manifests": prepared.evaluator_manifests,
        "candidate_count": len(prepared.batch.items),
        "items": [
            {
                "evaluation_pass_id": item.evaluation_pass_id,
                "candidate_id": item.candidate.candidate_id,
            }
            for item in prepared.batch.items
        ],
    }


def register_plot_cognition_projection_semantic_result(
    fixture: LiveSession,
    rnd: RoundFixture,
    data: dict[str, Any],
) -> dict[str, Any]:
    return register_projection_semantic_result(
        fixture,
        batch_id=str(data.get("batch_id", "")),
        evaluation_pass_id=str(data.get("evaluation_pass_id", "")),
        candidate_id=str(data.get("candidate_id", "")),
        semantic_raw=dict(data.get("semantic") or {}),
        inference_evidence_id=data.get("inference_evidence_id"),
        hg_round_id=rnd.hg_round_id,
        turn_index=int(rnd.turn_index),
        evaluation_attempt=int(data.get("evaluation_attempt", 1)),
    )


def prepare_plot_cognition_projection_regeneration(
    kernel: Any,
    fixture: LiveSession,
    rnd: RoundFixture,
    data: dict[str, Any],
) -> dict[str, Any]:
    return prepare_projection_regeneration(
        kernel,
        fixture,
        batch_id=str(data.get("batch_id", "")),
        evaluation_pass_id=str(data.get("evaluation_pass_id", "")),
        hg_round_id=rnd.hg_round_id,
        turn_index=int(rnd.turn_index),
    )


def finalize_plot_cognition_projection_regeneration(
    fixture: LiveSession,
    rnd: RoundFixture,
    data: dict[str, Any],
) -> dict[str, Any]:
    return finalize_projection_regeneration(
        fixture,
        batch_id=str(data.get("batch_id", "")),
        evaluation_pass_id=str(data.get("evaluation_pass_id", "")),
        regeneration_prepare_id=str(data.get("regeneration_prepare_id", "")),
        candidate_id=str(data.get("candidate_id", "")),
        regenerated_text=str(data.get("regenerated_text", "")),
        generator_inference_evidence_id=data.get("generator_inference_evidence_id"),
        hg_round_id=rnd.hg_round_id,
        turn_index=int(rnd.turn_index),
    )


def finalize_plot_cognition_projection(
    kernel: Any,
    fixture: LiveSession,
    rnd: RoundFixture,
    data: dict[str, Any],
) -> dict[str, Any]:
    batch_id = str(data.get("batch_id", ""))
    use_registered = bool(data.get("use_registered_results", True))
    raw_results = data.get("semantic_results") or []
    semantic_results: list[CharacterProjectionSemanticResult] = []
    regeneration_inputs = None
    second_pass_results = None
    if use_registered and not raw_results:
        first_pass, second_pass = collect_registered_results_for_finalize(batch_id)
        semantic_results = list(first_pass)
        regeneration_inputs = collect_regeneration_inputs(batch_id)
        second_pass_results = second_pass if second_pass else None
    else:
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            semantic_raw = item.get("semantic") or {}
            guidance_raw = item.get("regeneration_guidance")
            guidance = (
                RegenerationGuidance.from_dict(guidance_raw)
                if isinstance(guidance_raw, dict)
                else None
            )
            semantic = SemanticEvaluationResult(
                verdict=semantic_raw.get("verdict", "evaluator_unavailable"),  # type: ignore[arg-type]
                rationale=str(semantic_raw.get("rationale", "")),
                leak_indicators=tuple(str(x) for x in (semantic_raw.get("leak_indicators") or [])),
                forensic_rationale=semantic_raw.get("forensic_rationale"),
                regeneration_guidance=guidance,
            )
            semantic_results.append(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=str(item.get("evaluation_pass_id", "")),
                    candidate_id=str(item.get("candidate_id", "")),
                    semantic=semantic,
                    regeneration_guidance=guidance,
                    inference_evidence_id=item.get("inference_evidence_id"),
                )
            )
    if not semantic_results and use_registered:
        empty_batch = get_prepared_batch(batch_id)
        if empty_batch is None or empty_batch.items:
            return {
                "accepted": False,
                "reason": "no_registered_semantic_results",
                "contributions": [],
                "forensic": None,
            }
        semantic_results = []
    prepared_batch = get_prepared_batch(batch_id)
    binding_payload = None
    if prepared_batch is not None:
        binding_payload = {
            "batch_id": prepared_batch.batch_id,
            "binding_digest": prepared_batch.binding_digest,
            "character_id": prepared_batch.character_id,
            "overlay_revision": prepared_batch.overlay_revision,
            "hg_round_id": rnd.hg_round_id,
            "turn_index": int(rnd.turn_index),
        }
    try:
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=batch_id,
            semantic_results=tuple(semantic_results),
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            regeneration_inputs=regeneration_inputs,
            second_pass_results=second_pass_results,
        )
    except ValueError as exc:
        return {"accepted": False, "reason": str(exc), "contributions": [], "forensic": None}
    forensic = finalized.forensic
    inference_map: dict[str, str] = {}
    for item in semantic_results:
        if item.inference_evidence_id:
            inference_map[item.candidate_id] = str(item.inference_evidence_id)
    from .plot_cognition_forensics_integration import record_projection_decisions

    forensic_ok = record_projection_decisions(
        kernel,
        fixture,
        rnd,
        batch_id=batch_id,
        forensic_payload=forensic.to_dict() if hasattr(forensic, "to_dict") else {},
        inference_evidence_by_candidate=inference_map,
    )
    if not forensic_ok:
        return {
            "accepted": False,
            "reason": "forensic_persistence_failed",
            "contributions": [],
            "forensic": forensic.to_dict() if hasattr(forensic, "to_dict") else None,
        }
    return {
        "accepted": True,
        "batch_id": batch_id,
        "binding": binding_payload,
        "contributions": [
            {
                "contribution_id": item.contribution_id,
                "source_kind": item.source_kind,
                "authority_class": item.authority_class,
                "knowledge_ids": list(item.knowledge_ids),
                "priority": item.priority,
                "content": item.content,
                "provenance": dict(item.provenance),
            }
            for item in finalized.contributions
        ],
        "forensic": forensic.to_dict() if hasattr(forensic, "to_dict") else None,
        "pending_regenerations": [
            {
                "candidate_id": item.candidate_id,
                "evaluation_pass_id": item.evaluation_pass_id,
                "forensic_rationale": item.forensic_rationale,
                "regeneration_guidance": item.regeneration_guidance.to_dict(),
            }
            for item in finalized.pending_regenerations
        ],
    }


def record_plot_cognition_post_commit(
    kernel: Any,
    fixture: LiveSession,
    *,
    domain_commit_id: str,
) -> dict[str, Any]:
    from .plot_cognition_forensics_integration import wafi_record_post_commit_pending_work

    return wafi_record_post_commit_pending_work(
        kernel,
        fixture,
        domain_commit_id=domain_commit_id,
    )


def assess_plot_cognition_freshness(kernel: Any, fixture: LiveSession) -> dict[str, Any]:
    orch = _orchestration(kernel)
    if orch is None:
        return {"fresh": True, "reason": "plot_cognition_overlay_unavailable"}
    status = orch.assess_overlay_freshness(fixture)
    return {
        "fresh": status.fresh,
        "reason": status.reason,
        "pending_work": status.pending_work.to_dict() if status.pending_work else None,
    }


def plan_post_commit_plot_cognition_work(kernel: Any, fixture: LiveSession) -> dict[str, Any]:
    """Route post-commit Plot Cognition work using #61 freshness semantics."""
    from .plot_cognition_overlay_store import BoundednessPolicy, LoadStatus
    from .plot_cognition_lifecycle_api import _DEFAULT_POLICY

    orch = _orchestration(kernel)
    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    if overlay is None:
        return {
            "accepted": False,
            "operation": "blocked",
            "reason": "plot_cognition_overlay_unavailable",
            "fresh": True,
        }

    overlay_status = orch.assess_overlay_freshness(fixture) if orch else None
    pending = overlay_status.pending_work if overlay_status else None
    if overlay_status is not None and overlay_status.fresh and pending is None:
        return {
            "accepted": True,
            "operation": "none",
            "reason": "no_pending_work",
            "fresh": True,
            "pending_work": None,
        }

    scope_id = str(fixture.plot_cognition_scope_id or "")
    loaded = overlay.load(scope_id, policy=_DEFAULT_POLICY)
    init_svc = getattr(kernel.cognition, "plot_cognition_initialization", None)
    if loaded.status != LoadStatus.READY and init_svc is not None:
        eligible, reason = init_svc.is_initialization_eligible(fixture, policy=_DEFAULT_POLICY)
        if eligible or (pending is not None and pending.work_kind == "initialization"):
            return {
                "accepted": True,
                "operation": "initialization",
                "reason": reason,
                "fresh": False,
                "pending_work": pending.to_dict() if pending else None,
            }

    if loaded.status != LoadStatus.READY or loaded.store is None:
        return {
            "accepted": False,
            "operation": "blocked",
            "reason": f"overlay_{loaded.status.value}",
            "fresh": False,
            "pending_work": pending.to_dict() if pending else None,
        }

    update_svc = getattr(kernel.cognition, "plot_cognition_update", None)
    if update_svc is None:
        return {
            "accepted": False,
            "operation": "blocked",
            "reason": "plot_cognition_update_unavailable",
            "fresh": False,
            "pending_work": pending.to_dict() if pending else None,
        }

    assessment = update_svc.assess_freshness(fixture, loaded.store, _DEFAULT_POLICY)
    freshness_status = assessment.status
    snapshot_dict = (
        assessment.source_snapshot.to_dict() if assessment.source_snapshot is not None else None
    )

    if freshness_status == "freshness_unprovable":
        return {
            "accepted": True,
            "operation": "reconciliation",
            "reason": assessment.message,
            "freshness_status": freshness_status,
            "source_snapshot": snapshot_dict,
            "fresh": False,
            "pending_work": pending.to_dict() if pending else None,
        }

    if freshness_status == "authority_generation_changed_unchecked":
        return {
            "accepted": True,
            "operation": "authority_advance",
            "reason": assessment.message,
            "freshness_status": freshness_status,
            "source_snapshot": snapshot_dict,
            "fresh": False,
            "pending_work": pending.to_dict() if pending else None,
        }

    if freshness_status == "fresh":
        if pending is not None and orch is not None:
            return {
                "accepted": True,
                "operation": "clear_pending",
                "reason": "authority_fresh_pending_flag_stale",
                "freshness_status": freshness_status,
                "fresh": True,
                "pending_work": pending.to_dict(),
            }
        return {
            "accepted": True,
            "operation": "none",
            "reason": "fresh",
            "freshness_status": freshness_status,
            "fresh": True,
            "pending_work": None,
        }

    if freshness_status == "semantic_assimilation_pending":
        return {
            "accepted": True,
            "operation": "semantic_update",
            "reason": assessment.message,
            "freshness_status": freshness_status,
            "source_snapshot": snapshot_dict,
            "fresh": False,
            "pending_work": pending.to_dict() if pending else None,
        }

    return {
        "accepted": False,
        "operation": "blocked",
        "reason": assessment.message,
        "freshness_status": freshness_status,
        "fresh": False,
        "pending_work": pending.to_dict() if pending else None,
    }


__all__ = [
    "prepare_plot_cognition_projection",
    "register_plot_cognition_projection_semantic_result",
    "prepare_plot_cognition_projection_regeneration",
    "finalize_plot_cognition_projection_regeneration",
    "finalize_plot_cognition_projection",
    "record_plot_cognition_post_commit",
    "assess_plot_cognition_freshness",
    "plan_post_commit_plot_cognition_work",
    "clear_prepared_batches_for_tests",
]

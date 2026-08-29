"""Plot Cognition orchestration HTTP/kernel handlers (#63)."""

from __future__ import annotations

from typing import Any

from .plot_cognition_orchestration_contract import RegenerationGuidance
from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService
from .plot_cognition_projection_batch import (
    CharacterProjectionSemanticResult,
    clear_prepared_batches_for_tests,
    finalize_character_projection_batch,
    prepare_character_projection_batch,
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
    }


def finalize_plot_cognition_projection(
    kernel: Any,
    fixture: LiveSession,
    rnd: RoundFixture,
    data: dict[str, Any],
) -> dict[str, Any]:
    batch_id = str(data.get("batch_id", ""))
    raw_results = data.get("semantic_results") or []
    semantic_results: list[CharacterProjectionSemanticResult] = []
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
    try:
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=batch_id,
            semantic_results=tuple(semantic_results),
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
    except ValueError as exc:
        return {"accepted": False, "reason": str(exc), "contributions": [], "forensic": None}
    forensic = finalized.forensic
    return {
        "accepted": True,
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
    orch = _orchestration(kernel)
    if orch is None:
        return {"recorded": False, "reason": "plot_cognition_overlay_unavailable"}
    pending = orch.record_post_commit_pending_work(
        fixture,
        domain_commit_id=domain_commit_id,
    )
    return {
        "recorded": pending is not None,
        "pending_work": pending.to_dict() if pending is not None else None,
    }


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


__all__ = [
    "prepare_plot_cognition_projection",
    "finalize_plot_cognition_projection",
    "record_plot_cognition_post_commit",
    "assess_plot_cognition_freshness",
    "clear_prepared_batches_for_tests",
]

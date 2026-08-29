"""Plot Cognition lifecycle prepare/finalize handlers (#63)."""

from __future__ import annotations

from typing import Any

from .plot_cognition_initialization_contract import PlotCognitionInitializationProposal
from .plot_cognition_overlay_store import BoundednessPolicy
from .plot_cognition_projection_contract import CharacterAdvisoryCandidate
from .plot_cognition_update_contract import (
    PlotCognitionReplanEvaluation,
    PlotCognitionReplanProposal,
    PlotCognitionUpdateEvaluation,
    PlotCognitionUpdateProposal,
)
from .session_state import LiveSession

_DEFAULT_POLICY = BoundednessPolicy(max_active_goals=8, max_active_pressures=8)


def prepare_plot_cognition_init(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    init_svc = getattr(kernel.cognition, "plot_cognition_initialization", None)
    if init_svc is None:
        return {"accepted": False, "reason": "plot_cognition_initialization_unavailable"}
    policy = _DEFAULT_POLICY
    eligible, reason = init_svc.is_initialization_eligible(fixture, policy=policy)
    sources = init_svc.gather_sources(fixture)
    manifest_id = str(data.get("manifest_id", f"manifest-plot-init-{fixture.hg_scene_id}"))
    return {
        "accepted": eligible,
        "reason": reason,
        "manifest_id": manifest_id,
        "source_snapshot": sources.to_dict(),
        "source_snapshot_fingerprint": sources.fingerprint,
        "inference_kind": "plot_cognition_init",
    }


def finalize_plot_cognition_init(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    init_svc = getattr(kernel.cognition, "plot_cognition_initialization", None)
    if init_svc is None:
        return {"accepted": False, "reason": "plot_cognition_initialization_unavailable"}
    proposal_raw = data.get("proposal")
    if not isinstance(proposal_raw, dict):
        return {"accepted": False, "reason": "missing_proposal"}
    proposal = PlotCognitionInitializationProposal.from_dict(proposal_raw)
    sources = init_svc.gather_sources(fixture)

    def do_commit():
        return init_svc.commit_initial_overlay_if_absent(fixture, proposal, policy=_DEFAULT_POLICY)

    from .plot_cognition_forensics_integration import wafi_initialize

    result = wafi_initialize(
        kernel,
        fixture,
        proposal=proposal,
        sources=sources,
        policy=_DEFAULT_POLICY,
        commit_fn=do_commit,
    )
    return {
        "accepted": result.success,
        "code": result.code,
        "message": result.message,
        "store_revision": result.store_revision,
    }


def _loaded_store(kernel: Any, fixture: LiveSession):
    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    if overlay is None:
        return None, None
    scope_id = str(fixture.plot_cognition_scope_id or "")
    loaded = overlay.load(scope_id, policy=_DEFAULT_POLICY)
    return overlay, loaded


def prepare_plot_cognition_update(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    update_svc = getattr(kernel.cognition, "plot_cognition_update", None)
    overlay, loaded = _loaded_store(kernel, fixture)
    if update_svc is None or overlay is None or loaded is None or loaded.store is None:
        return {"accepted": False, "reason": "plot_cognition_update_unavailable"}
    contributors = tuple(str(item) for item in (data.get("contributors") or (fixture.hg_scene_id,)))
    snapshot = update_svc.gather_sources(
        fixture,
        loaded.store,
        None,
        contributors,
        catch_up_mode=str(data.get("catch_up_mode", "sequential")),
    )
    manifest_id = str(data.get("manifest_id", f"manifest-plot-update-{fixture.hg_scene_id}"))
    return {
        "accepted": True,
        "manifest_id": manifest_id,
        "source_snapshot": snapshot.to_dict(),
        "authority_source_fingerprint": snapshot.authority_source_fingerprint,
        "prior_store_revision": snapshot.prior_store_revision,
        "inference_kind": "plot_cognition_update",
    }


def finalize_plot_cognition_update(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    update_svc = getattr(kernel.cognition, "plot_cognition_update", None)
    if update_svc is None:
        return {"accepted": False, "reason": "plot_cognition_update_unavailable"}
    proposal_raw = data.get("proposal")
    evaluation_raw = data.get("evaluation")
    if not isinstance(proposal_raw, dict) or not isinstance(evaluation_raw, dict):
        return {"accepted": False, "reason": "missing_proposal_or_evaluation"}
    proposal = PlotCognitionUpdateProposal.from_dict(proposal_raw)
    evaluation = PlotCognitionUpdateEvaluation.from_dict(evaluation_raw)
    replan_proposal = None
    replan_eval = None
    if isinstance(data.get("replan_proposal"), dict):
        replan_proposal = PlotCognitionReplanProposal.from_dict(data["replan_proposal"])
    if isinstance(data.get("replan_evaluation"), dict):
        replan_eval = PlotCognitionReplanEvaluation.from_dict(data["replan_evaluation"])
    operation_kind = "replan" if replan_proposal is not None else "update"
    from .plot_cognition_forensics_integration import wafi_update_like
    from .plot_cognition_forensics_capture import capture_authority_projection_verbatim

    forensics = getattr(getattr(kernel, "store", None), "plot_cognition_forensics_service", None)
    authority_artifact_id = None
    if forensics is not None:
        authority_artifact_id = forensics.store_semantic_artifact(
            str(fixture.plot_cognition_scope_id or ""),
            capture_authority_projection_verbatim(
                fixture,
                None,
                proposal.source_snapshot_fingerprint,
            ),
        )

    def do_commit():
        return update_svc.commit_update(
            fixture,
            proposal,
            evaluation,
            policy=_DEFAULT_POLICY,
            replan_proposal=replan_proposal,
            replan_eval=replan_eval,
        )

    result, forensic_ok = wafi_update_like(
        kernel,
        fixture,
        operation_kind=operation_kind,
        idempotency_suffix=str(proposal.proposal_id),
        intent_payload={
            "proposal": proposal.to_dict(),
            "evaluation": evaluation.to_dict(),
            "replan_proposal": replan_proposal.to_dict() if replan_proposal else None,
            "replan_evaluation": replan_eval.to_dict() if replan_eval else None,
            "authority_artifact_id": authority_artifact_id,
        },
        correlation_extra={"domain_commit_id": proposal.source_snapshot_fingerprint},
        commit_fn=do_commit,
    )
    if not forensic_ok:
        return {
            "accepted": False,
            "code": "forensic_persistence_failed",
            "message": "plot cognition update forensic persistence failed",
            "store_revision": result.store_revision if hasattr(result, "store_revision") else None,
        }
    orch = getattr(kernel.cognition, "plot_cognition_overlay", None)
    if result.success and orch is not None:
        from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService

        PlotCognitionOrchestrationService(orch).clear_pending_work(fixture)
    return {
        "accepted": result.success,
        "code": result.code,
        "message": result.message,
        "store_revision": result.store_revision,
    }


def prepare_plot_cognition_replan(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    prepared = prepare_plot_cognition_update(kernel, fixture, data)
    if not prepared.get("accepted"):
        return prepared
    prepared["inference_kind"] = "plot_cognition_replan"
    prepared["replan_required"] = True
    return prepared


def finalize_plot_cognition_replan(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    return finalize_plot_cognition_update(kernel, fixture, data)


def prepare_character_advisory_generation(
    kernel: Any,
    fixture: LiveSession,
    rnd: Any,
    data: dict[str, Any],
) -> dict[str, Any]:
    overlay, loaded = _loaded_store(kernel, fixture)
    if overlay is None or loaded is None or loaded.store is None:
        return {"accepted": False, "reason": "overlay_unavailable"}
    view = overlay.operative_view(loaded.store, policy=_DEFAULT_POLICY, load_status=loaded.status)
    character_id = str(data.get("character_id", ""))
    manifest_id = str(data.get("manifest_id", f"manifest-advisory-gen-{rnd.hg_round_id}"))
    bounded_sources: list[dict[str, Any]] = []
    for goal in view.goals:
        if goal.applicability.applicability_kind == "global":
            bounded_sources.append(
                {
                    "kind": "global_goal",
                    "goal_id": goal.goal_id,
                    "direction_hint": "ensemble-level (do not quote verbatim to Character)",
                }
            )
    if view.active_frame is not None:
        bounded_sources.append(
            {
                "kind": "global_frame",
                "frame_id": view.active_frame.frame_id,
                "direction_hint": "frame-level (generate independently phrased Character advice)",
            }
        )
    return {
        "accepted": True,
        "manifest_id": manifest_id,
        "character_id": character_id,
        "bounded_sources": bounded_sources,
        "inference_kind": "character_advisory_generation",
        "overlay_revision": loaded.store.store_revision,
    }


def finalize_character_advisory_generation(
    kernel: Any,
    fixture: LiveSession,
    rnd: Any,
    data: dict[str, Any],
) -> dict[str, Any]:
    raw_candidates = data.get("candidates") or []
    parsed: list[dict[str, Any]] = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        parsed.append(
            {
                "candidate_id": str(item.get("candidate_id", "")),
                "text": text,
                "source_kind": str(item.get("source_kind", "global_derived")),
                "lineage": list(item.get("lineage") or []),
            }
        )
    return {
        "accepted": bool(parsed),
        "candidates": parsed,
        "reason": "ok" if parsed else "no_valid_candidates",
    }


def finalize_plot_cognition_reconciliation(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    update_svc = getattr(kernel.cognition, "plot_cognition_update", None)
    overlay, loaded = _loaded_store(kernel, fixture)
    if update_svc is None or loaded is None or loaded.store is None:
        return {"accepted": False, "reason": "plot_cognition_update_unavailable"}

    def do_commit():
        return update_svc.first_reconciliation(fixture, loaded.store, _DEFAULT_POLICY)

    from .plot_cognition_forensics_integration import wafi_update_like

    result, forensic_ok = wafi_update_like(
        kernel,
        fixture,
        operation_kind="reconciliation",
        idempotency_suffix=f"reconciliation:{fixture.hg_scene_id}",
        intent_payload={"reconciliation": True},
        correlation_extra={},
        commit_fn=do_commit,
    )
    if not forensic_ok:
        return {
            "accepted": False,
            "code": "forensic_persistence_failed",
            "message": "reconciliation forensic persistence failed",
        }
    if result.success and overlay is not None:
        from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService

        PlotCognitionOrchestrationService(overlay).clear_pending_work(fixture)
    return {
        "accepted": result.success,
        "code": result.code,
        "message": result.message,
        "store_revision": result.store_revision,
    }


def finalize_plot_cognition_authority_advance(kernel: Any, fixture: LiveSession, data: dict[str, Any]) -> dict[str, Any]:
    update_svc = getattr(kernel.cognition, "plot_cognition_update", None)
    overlay, loaded = _loaded_store(kernel, fixture)
    if update_svc is None or overlay is None or loaded is None or loaded.store is None:
        return {"accepted": False, "reason": "plot_cognition_update_unavailable"}
    contributors = tuple(str(item) for item in (data.get("contributors") or (fixture.hg_scene_id,)))
    snapshot_raw = data.get("source_snapshot")
    if isinstance(snapshot_raw, dict):
        from .plot_cognition_update_contract import CognitionUpdateSourceSnapshot

        snapshot = CognitionUpdateSourceSnapshot.from_dict(snapshot_raw)
    else:
        snapshot = update_svc.gather_sources(
            fixture,
            loaded.store,
            None,
            contributors,
            catch_up_mode=str(data.get("catch_up_mode", "sequential")),
        )

    from .plot_cognition_forensics_capture import capture_authority_projection_verbatim
    from .plot_cognition_forensics_integration import wafi_update_like

    forensics = getattr(getattr(kernel, "store", None), "plot_cognition_forensics_service", None)
    authority_artifact_id = None
    if forensics is not None:
        authority_artifact_id = forensics.store_semantic_artifact(
            str(fixture.plot_cognition_scope_id or ""),
            capture_authority_projection_verbatim(
                fixture,
                None,
                snapshot.through_domain_commit_id,
            ),
        )

    def do_commit():
        return update_svc.advance_authority_unchanged(
            fixture,
            loaded.store,
            _DEFAULT_POLICY,
            source_snapshot=snapshot,
        )

    result, forensic_ok = wafi_update_like(
        kernel,
        fixture,
        operation_kind="authority_advance",
        idempotency_suffix=str(snapshot.authority_source_fingerprint),
        intent_payload={
            "source_snapshot": snapshot.to_dict(),
            "authority_artifact_id": authority_artifact_id,
        },
        correlation_extra={"domain_commit_id": snapshot.through_domain_commit_id},
        commit_fn=do_commit,
    )
    if not forensic_ok:
        return {
            "accepted": False,
            "code": "forensic_persistence_failed",
            "message": "authority advance forensic persistence failed",
        }
    if result.success:
        from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService

        PlotCognitionOrchestrationService(overlay).clear_pending_work(fixture)
    return {
        "accepted": result.success,
        "code": result.code,
        "message": result.message,
        "store_revision": result.store_revision,
    }


def clear_plot_cognition_pending_work(kernel: Any, fixture: LiveSession) -> dict[str, Any]:
    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    if overlay is None:
        return {"cleared": False, "reason": "plot_cognition_overlay_unavailable"}
    from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService

    PlotCognitionOrchestrationService(overlay).clear_pending_work(fixture)
    return {"cleared": True}

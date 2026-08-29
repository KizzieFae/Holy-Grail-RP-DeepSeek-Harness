"""Ephemeral projection-batch runtime state and regeneration authority (#66)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from .character_epistemic import compute_known_by_snapshot_id
from .character_epistemic_projection_context import (
    EPISTEMIC_PROHIBITION_BLOCK,
    build_character_epistemic_context_envelope,
    envelope_to_evaluator_contributions,
)
from .plot_cognition_orchestration_contract import (
    CharacterProjectionSemanticResult,
    RegenerationGuidance,
    compute_binding_digest,
)
from .plot_cognition_projection_batch import (
    PreparedProjectionBatch,
    PreparedProjectionCandidate,
    _PREPARED_BATCHES,
    _validate_rewrite_guidance,
    get_prepared_batch,
)
from .plot_cognition_projection_contract import (
    CharacterAdvisoryCandidate,
    RegenerationCycleInput,
    SemanticEvaluationResult,
)
from .session_state import LiveSession

_VALID_VERDICTS = frozenset({"pass", "withhold", "rewrite_required", "evaluator_unavailable"})


@dataclass
class ProjectionBatchRuntimeState:
    registered_semantic: dict[str, CharacterProjectionSemanticResult] = field(default_factory=dict)
    evaluation_attempt_by_pass: dict[str, int] = field(default_factory=dict)
    evaluation_count_by_candidate: dict[str, int] = field(default_factory=dict)
    regeneration_attempted: set[str] = field(default_factory=set)
    regeneration_prepare_ids: dict[str, str] = field(default_factory=dict)
    regeneration_prepare_consumed: set[str] = field(default_factory=set)
    regeneration_cycle_inputs: dict[str, RegenerationCycleInput] = field(default_factory=dict)
    semantic_payload_fingerprints: dict[str, str] = field(default_factory=dict)


_BATCH_RUNTIME: dict[str, ProjectionBatchRuntimeState] = {}


def clear_batch_runtime(batch_id: str) -> None:
    _BATCH_RUNTIME.pop(batch_id, None)


def clear_all_batch_runtime_for_tests() -> None:
    _BATCH_RUNTIME.clear()


def _runtime(batch_id: str) -> ProjectionBatchRuntimeState:
    if batch_id not in _BATCH_RUNTIME:
        _BATCH_RUNTIME[batch_id] = ProjectionBatchRuntimeState()
    return _BATCH_RUNTIME[batch_id]


def _batch_item(batch: PreparedProjectionBatch, evaluation_pass_id: str) -> PreparedProjectionCandidate | None:
    for item in batch.items:
        if item.evaluation_pass_id == evaluation_pass_id:
            return item
    return None


def _binding_valid(
    fixture: LiveSession,
    batch: PreparedProjectionBatch,
    *,
    hg_round_id: str,
    turn_index: int,
) -> tuple[bool, str]:
    known_by_snapshot_id = compute_known_by_snapshot_id(fixture, batch.character_id)
    binding_digest = compute_binding_digest(
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        character_id=batch.character_id,
        known_by_snapshot_id=known_by_snapshot_id,
        authority_fingerprint=batch.authority_fingerprint,
        overlay_revision=batch.overlay_revision,
    )
    if not batch.binding_matches(
        known_by_snapshot_id=known_by_snapshot_id,
        authority_fingerprint=batch.authority_fingerprint,
        overlay_revision=batch.overlay_revision,
        binding_digest=binding_digest,
    ):
        return False, "stale_projection_batch_binding"
    return True, "ok"


def _parse_semantic(raw: dict[str, Any]) -> SemanticEvaluationResult:
    guidance_raw = raw.get("regeneration_guidance")
    guidance = (
        RegenerationGuidance.from_dict(guidance_raw)
        if isinstance(guidance_raw, dict)
        else None
    )
    verdict = str(raw.get("verdict", "evaluator_unavailable"))
    if verdict not in _VALID_VERDICTS:
        verdict = "evaluator_unavailable"
    return SemanticEvaluationResult(
        verdict=verdict,  # type: ignore[arg-type]
        rationale=str(raw.get("rationale", "")),
        leak_indicators=tuple(str(x) for x in (raw.get("leak_indicators") or [])),
        forensic_rationale=raw.get("forensic_rationale"),
        regeneration_guidance=guidance,
    )


def _semantic_fingerprint(result: CharacterProjectionSemanticResult) -> str:
    sem = result.semantic
    guidance = sem.regeneration_guidance
    guidance_key = ""
    if guidance is not None:
        if hasattr(guidance, "to_dict"):
            guidance_key = str(sorted(guidance.to_dict().items()))
        elif isinstance(guidance, dict):
            guidance_key = str(sorted(guidance.items()))
    return "|".join(
        [
            result.evaluation_pass_id,
            result.candidate_id,
            sem.verdict,
            sem.rationale,
            guidance_key,
        ]
    )


def register_projection_semantic_result(
    fixture: LiveSession,
    *,
    batch_id: str,
    evaluation_pass_id: str,
    candidate_id: str,
    semantic_raw: dict[str, Any],
    inference_evidence_id: str | None,
    hg_round_id: str,
    turn_index: int,
    evaluation_attempt: int = 1,
) -> dict[str, Any]:
    batch = get_prepared_batch(batch_id)
    if batch is None:
        return {"accepted": False, "reason": "unknown_or_expired_batch"}
    ok, reason = _binding_valid(fixture, batch, hg_round_id=hg_round_id, turn_index=turn_index)
    if not ok:
        return {"accepted": False, "reason": reason}
    item = _batch_item(batch, evaluation_pass_id)
    if item is None or item.candidate.candidate_id != candidate_id:
        return {"accepted": False, "reason": "candidate_or_pass_mismatch"}

    runtime = _runtime(batch_id)
    attempt = int(evaluation_attempt)
    if attempt not in (1, 2):
        return {"accepted": False, "reason": "invalid_evaluation_attempt"}
    storage_key = f"{evaluation_pass_id}:{attempt}"
    fp = _semantic_fingerprint(
        CharacterProjectionSemanticResult(
            evaluation_pass_id=evaluation_pass_id,
            candidate_id=candidate_id,
            semantic=_parse_semantic(semantic_raw),
            regeneration_guidance=None,
        )
    )
    if storage_key in runtime.registered_semantic:
        if runtime.semantic_payload_fingerprints.get(storage_key) == fp:
            return {"accepted": True, "reason": "idempotent_replay", "evaluation_attempt": attempt}
        return {"accepted": False, "reason": "conflicting_semantic_replay"}
    prior_count = runtime.evaluation_count_by_candidate.get(candidate_id, 0)
    if attempt == 2:
        if prior_count < 1:
            return {"accepted": False, "reason": "first_pass_not_registered"}
        if candidate_id not in runtime.regeneration_cycle_inputs:
            return {"accepted": False, "reason": "regeneration_not_finalized"}
    if prior_count >= 2:
        return {"accepted": False, "reason": "semantic_evaluation_budget_exceeded"}
    if attempt == 2 and prior_count >= 1 and candidate_id not in runtime.regeneration_cycle_inputs:
        return {"accepted": False, "reason": "regeneration_not_finalized"}
    semantic = _parse_semantic(semantic_raw)
    if semantic.verdict == "rewrite_required" and not _validate_rewrite_guidance(semantic):
        return {"accepted": False, "reason": "invalid_regeneration_guidance"}

    guidance = semantic.regeneration_guidance
    result = CharacterProjectionSemanticResult(
        evaluation_pass_id=evaluation_pass_id,
        candidate_id=candidate_id,
        semantic=semantic,
        regeneration_guidance=guidance if hasattr(guidance, "to_dict") else guidance,
        inference_evidence_id=inference_evidence_id,
    )
    runtime.registered_semantic[storage_key] = result
    runtime.evaluation_attempt_by_pass[evaluation_pass_id] = attempt
    runtime.evaluation_count_by_candidate[candidate_id] = prior_count + 1
    runtime.semantic_payload_fingerprints[storage_key] = fp
    second_pass_manifest: list[dict[str, Any]] | None = None
    if attempt == 2 and candidate_id in runtime.regeneration_cycle_inputs:
        regen_input = runtime.regeneration_cycle_inputs[candidate_id]
        if regen_input.regenerated_candidate is not None:
            manifest_id = f"{batch.manifest_id}-ep-eval-2-{evaluation_pass_id}"
            envelope = build_character_epistemic_context_envelope(
                fixture,
                character_id=batch.character_id,
                candidate=regen_input.regenerated_candidate,
                hg_round_id=hg_round_id,
                turn_index=turn_index,
                authority_fingerprint=batch.authority_fingerprint,
                overlay_revision=batch.overlay_revision,
            )
            second_pass_manifest = envelope_to_evaluator_contributions(
                envelope,
                manifest_id=manifest_id,
            )
    return {
        "accepted": True,
        "reason": "registered",
        "evaluation_attempt": attempt,
        "second_pass_evaluator_manifest": second_pass_manifest,
    }


def _bounded_direction_hints(kernel: Any, fixture: LiveSession) -> list[dict[str, str]]:
    if kernel is None:
        return []
    overlay = getattr(kernel.cognition, "plot_cognition_overlay", None)
    if overlay is None:
        return []
    from .plot_cognition_overlay_store import BoundednessPolicy, LoadStatus

    scope_id = str(fixture.plot_cognition_scope_id or "")
    loaded = overlay.load(scope_id, policy=BoundednessPolicy(max_active_goals=8, max_active_pressures=8))
    if loaded.status != LoadStatus.READY or loaded.store is None:
        return []
    view = overlay.operative_view(
        loaded.store,
        policy=BoundednessPolicy(max_active_goals=8, max_active_pressures=8),
        load_status=loaded.status,
    )
    hints: list[dict[str, str]] = []
    for goal in view.goals:
        if goal.applicability.applicability_kind == "global":
            hints.append(
                {
                    "kind": "global_goal",
                    "goal_id": goal.goal_id,
                    "direction_hint": "ensemble-level (do not quote verbatim to Character)",
                }
            )
    if view.active_frame is not None:
        hints.append(
            {
                "kind": "global_frame",
                "frame_id": view.active_frame.frame_id,
                "direction_hint": "frame-level (generate independently phrased Character advice)",
            }
        )
    return hints


def prepare_projection_regeneration(
    kernel: Any,
    fixture: LiveSession,
    *,
    batch_id: str,
    evaluation_pass_id: str,
    hg_round_id: str,
    turn_index: int,
) -> dict[str, Any]:
    batch = get_prepared_batch(batch_id)
    if batch is None:
        return {"accepted": False, "reason": "unknown_or_expired_batch"}
    ok, reason = _binding_valid(fixture, batch, hg_round_id=hg_round_id, turn_index=turn_index)
    if not ok:
        return {"accepted": False, "reason": reason}
    item = _batch_item(batch, evaluation_pass_id)
    if item is None:
        return {"accepted": False, "reason": "evaluation_pass_not_in_batch"}
    candidate_id = item.candidate.candidate_id
    runtime = _runtime(batch_id)
    if candidate_id in runtime.regeneration_attempted:
        return {"accepted": False, "reason": "regeneration_already_consumed"}
    stored = runtime.registered_semantic.get(f"{evaluation_pass_id}:1")
    if stored is None:
        return {"accepted": False, "reason": "first_pass_not_registered"}
    if stored.semantic.verdict != "rewrite_required":
        return {"accepted": False, "reason": "regeneration_not_authorized"}
    if not _validate_rewrite_guidance(stored.semantic):
        return {"accepted": False, "reason": "invalid_regeneration_guidance"}
    guidance = stored.semantic.regeneration_guidance
    if guidance is None:
        return {"accepted": False, "reason": "missing_regeneration_guidance"}
    regen_prepare_id = f"regen-prep-{uuid.uuid4().hex[:12]}"
    runtime.regeneration_attempted.add(candidate_id)
    runtime.regeneration_prepare_ids[evaluation_pass_id] = regen_prepare_id
    guidance_dict = guidance.to_dict() if hasattr(guidance, "to_dict") else dict(guidance)
    manifest_id = f"{batch.manifest_id}-advisory-gen-{evaluation_pass_id}"
    contributions: list[dict[str, Any]] = [
        {
            "contribution_id": f"{manifest_id}-prohibition",
            "source_kind": "active_constraints",
            "authority_class": "derived",
            "knowledge_ids": [f"regen:{candidate_id}"],
            "priority": 18,
            "content": EPISTEMIC_PROHIBITION_BLOCK,
            "provenance": {"regeneration_prepare_id": regen_prepare_id},
        },
        {
            "contribution_id": f"{manifest_id}-original-candidate",
            "source_kind": "derived",
            "authority_class": "derived",
            "knowledge_ids": list(item.candidate.lineage),
            "priority": 19,
            "content": f"Original candidate text to revise:\n{item.candidate.text.strip()}",
            "provenance": {
                "candidate_id": candidate_id,
                "evaluation_pass_id": evaluation_pass_id,
            },
        },
        {
            "contribution_id": f"{manifest_id}-guidance",
            "source_kind": "active_constraints",
            "authority_class": "derived",
            "knowledge_ids": [f"guidance:{candidate_id}"],
            "priority": 20,
            "content": (
                "Regeneration guidance (evaluator-issued):\n"
                f"violation_class: {guidance_dict.get('violation_class', 'other')}\n"
                f"safe_constraints: {guidance_dict.get('safe_constraints', [])}\n"
                f"do_not_introduce: {guidance_dict.get('do_not_introduce', [])}\n"
                f"affected_dimensions: {guidance_dict.get('affected_dimensions', [])}"
            ),
            "provenance": {"regeneration_prepare_id": regen_prepare_id},
        },
    ]
    for index, hint in enumerate(_bounded_direction_hints(kernel, fixture)):
        contributions.append(
            {
                "contribution_id": f"{manifest_id}-hint-{index}",
                "source_kind": "derived",
                "authority_class": "derived",
                "knowledge_ids": [hint.get("goal_id") or hint.get("frame_id", "hint")],
                "priority": 21 + index,
                "content": (
                    f"Direction hint ({hint.get('kind')}): {hint.get('direction_hint', '')}"
                ),
                "provenance": {"hint_kind": hint.get("kind")},
            }
        )
    return {
        "accepted": True,
        "regeneration_prepare_id": regen_prepare_id,
        "batch_id": batch_id,
        "evaluation_pass_id": evaluation_pass_id,
        "candidate_id": candidate_id,
        "character_id": batch.character_id,
        "inference_kind": "character_advisory_generation",
        "overlay_revision": batch.overlay_revision,
        "binding_digest": batch.binding_digest,
        "plot_cognition_scope_id": str(fixture.plot_cognition_scope_id or ""),
        "hg_round_id": hg_round_id,
        "turn_index": turn_index,
        "generator_manifest": {"contributions": contributions},
    }


def _candidate_from_regen_payload(
    original: CharacterAdvisoryCandidate,
    *,
    regenerated_text: str,
    candidate_id: str | None = None,
) -> CharacterAdvisoryCandidate:
    return CharacterAdvisoryCandidate(
        candidate_id=candidate_id or f"{original.candidate_id}-regen",
        text=regenerated_text.strip(),
        source_kind=original.source_kind,
        lineage=original.lineage,
        basis_refs=original.basis_refs,
        creation_provenance=original.creation_provenance,
        applicability=original.applicability,
        prospective_only=original.prospective_only,
        structural_evidence_refs=original.structural_evidence_refs,
        host_metadata=dict(original.host_metadata),
    )


def finalize_projection_regeneration(
    fixture: LiveSession,
    *,
    batch_id: str,
    evaluation_pass_id: str,
    regeneration_prepare_id: str,
    candidate_id: str,
    regenerated_text: str,
    generator_inference_evidence_id: str | None,
    hg_round_id: str,
    turn_index: int,
) -> dict[str, Any]:
    batch = get_prepared_batch(batch_id)
    if batch is None:
        return {"accepted": False, "reason": "unknown_or_expired_batch"}
    ok, reason = _binding_valid(fixture, batch, hg_round_id=hg_round_id, turn_index=turn_index)
    if not ok:
        return {"accepted": False, "reason": reason}
    runtime = _runtime(batch_id)
    if runtime.regeneration_prepare_ids.get(evaluation_pass_id) != regeneration_prepare_id:
        return {"accepted": False, "reason": "invalid_regeneration_prepare_id"}
    if regeneration_prepare_id in runtime.regeneration_prepare_consumed:
        return {"accepted": False, "reason": "regeneration_prepare_already_consumed"}
    item = _batch_item(batch, evaluation_pass_id)
    if item is None or item.candidate.candidate_id != candidate_id:
        return {"accepted": False, "reason": "candidate_or_pass_mismatch"}
    text = str(regenerated_text or "").strip()
    if not text:
        return {"accepted": False, "reason": "empty_regenerated_candidate"}
    stored = runtime.registered_semantic.get(f"{evaluation_pass_id}:1")
    if stored is None or stored.semantic.verdict != "rewrite_required":
        return {"accepted": False, "reason": "regeneration_not_authorized"}
    regenerated = _candidate_from_regen_payload(item.candidate, regenerated_text=text)
    runtime.regeneration_prepare_consumed.add(regeneration_prepare_id)
    runtime.regeneration_cycle_inputs[candidate_id] = RegenerationCycleInput(
        original_candidate=item.candidate,
        evaluator_result=stored.semantic,
        regenerated_candidate=regenerated,
    )
    manifest_id = f"{batch.manifest_id}-ep-eval-2-{evaluation_pass_id}"
    envelope = build_character_epistemic_context_envelope(
        fixture,
        character_id=batch.character_id,
        candidate=regenerated,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        authority_fingerprint=batch.authority_fingerprint,
        overlay_revision=batch.overlay_revision,
    )
    second_pass_manifest = envelope_to_evaluator_contributions(envelope, manifest_id=manifest_id)
    return {
        "accepted": True,
        "candidate_id": candidate_id,
        "evaluation_pass_id": evaluation_pass_id,
        "regenerated_candidate": regenerated.to_dict(),
        "generator_inference_evidence_id": generator_inference_evidence_id,
        "second_pass_evaluator_manifest": second_pass_manifest,
        "regeneration_cycle_input": {
            "candidate_id": candidate_id,
            "original_candidate_id": item.candidate.candidate_id,
        },
    }


def collect_registered_results_for_finalize(batch_id: str) -> tuple[
    list[CharacterProjectionSemanticResult],
    dict[str, SemanticEvaluationResult],
]:
    runtime = _runtime(batch_id)
    first_pass: list[CharacterProjectionSemanticResult] = []
    second_pass: dict[str, SemanticEvaluationResult] = {}
    for key, result in runtime.registered_semantic.items():
        if key.endswith(":1"):
            first_pass.append(result)
        elif key.endswith(":2"):
            pass_id = key.rsplit(":", 1)[0]
            second_pass[pass_id] = result.semantic
    return first_pass, second_pass


def collect_regeneration_inputs(batch_id: str) -> dict[str, RegenerationCycleInput]:
    return dict(_runtime(batch_id).regeneration_cycle_inputs)


def ensure_batch_runtime_initialized(batch_id: str) -> None:
    _runtime(batch_id)

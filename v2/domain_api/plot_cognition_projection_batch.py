"""Split-phase Character projection batch orchestration (#63)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .character_epistemic_projection_context import (
    build_character_epistemic_context_envelope,
    envelope_to_evaluator_contributions,
)
from .plot_cognition_orchestration_contract import (
    DEFAULT_ORCHESTRATION_POLICY,
    CharacterProjectionSemanticResult,
    FinalizedProjectionBatch,
    PreparedProjectionBatch,
    PreparedProjectionCandidate,
    RegenerationRequestDescriptor,
    StorytellerOrchestrationPolicy,
    compute_binding_digest,
    new_batch_id,
    new_evaluation_pass_id,
)
from .plot_cognition_projection_contract import (
    PROJECTION_FORENSIC_HANDOFF_SCHEMA,
    CandidateProjectionRecord,
    CharacterAdvisoryCandidate,
    ProjectionBudget,
    RegenerationCycleInput,
    RegenerationCycleResult,
    SemanticEvaluationResult,
    new_handoff_id,
)
from .plot_cognition_projection_semantic_safety import CharacterEpistemicLeakageEvaluator
from .character_epistemic import compute_known_by_snapshot_id
from .plot_cognition_projection_service import (
    ApprovedProjection,
    ProjectionServiceResult,
    _projection_mode_for,
    apply_evaluation_budget,
    apply_projection_budget,
    apply_regeneration_cycle,
    assess_structural_eligibility,
    deterministic_candidate_order_key,
    render_character_prompt_contribution,
)
from .session_state import LiveSession

_PREPARED_BATCHES: dict[str, PreparedProjectionBatch] = {}


def clear_prepared_batches_for_tests() -> None:
    _PREPARED_BATCHES.clear()


def get_prepared_batch(batch_id: str) -> PreparedProjectionBatch | None:
    return _PREPARED_BATCHES.get(batch_id)


@dataclass(frozen=True)
class PrepareProjectionBatchResult:
    batch: PreparedProjectionBatch
    evaluator_manifests: dict[str, list[dict[str, Any]]]


def prepare_character_projection_batch(
    fixture: LiveSession,
    *,
    manifest_id: str,
    character_id: str,
    candidates: tuple[CharacterAdvisoryCandidate, ...],
    budget: ProjectionBudget,
    hg_round_id: str,
    turn_index: int,
    authority_fingerprint: str | None = None,
    overlay_revision: int | None = None,
    policy: StorytellerOrchestrationPolicy | None = None,
) -> PrepareProjectionBatchResult:
    """Layer A + evaluation budget + epistemic envelopes; read-only on fixture."""
    orch_policy = policy or DEFAULT_ORCHESTRATION_POLICY
    known_by_snapshot_id = compute_known_by_snapshot_id(fixture, character_id)
    binding_digest = compute_binding_digest(
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        character_id=character_id,
        known_by_snapshot_id=known_by_snapshot_id,
        authority_fingerprint=authority_fingerprint,
        overlay_revision=overlay_revision,
    )
    records: list[CandidateProjectionRecord] = []
    structurally_admissible: list[tuple[CharacterAdvisoryCandidate, Any]] = []

    for candidate in candidates[: orch_policy.max_generated_candidates]:
        structural = assess_structural_eligibility(
            fixture,
            candidate=candidate,
            character_id=character_id,
        )
        if not structural.eligible:
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=character_id,
                    outcome="structurally_ineligible",
                    structural=structural,
                    semantic=None,
                    regeneration=None,
                    original_text=candidate.text,
                    regenerated_text=None,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=authority_fingerprint,
                    overlay_revision=overlay_revision,
                    rationale=structural.rationale,
                )
            )
            continue
        structurally_admissible.append((candidate, structural))

    eval_included, _ = apply_evaluation_budget(
        tuple(item[0] for item in structurally_admissible),
        budget,
    )
    eval_included_ids = {item.candidate_id for item in eval_included}
    for candidate, structural in structurally_admissible:
        if candidate.candidate_id not in eval_included_ids:
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=character_id,
                    outcome="evaluation_budget_excluded",
                    structural=structural,
                    semantic=None,
                    regeneration=None,
                    original_text=candidate.text,
                    regenerated_text=None,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=authority_fingerprint,
                    overlay_revision=overlay_revision,
                    rationale="excluded by evaluation budget",
                )
            )

    prepared_items: list[PreparedProjectionCandidate] = []
    manifests: dict[str, list[dict[str, Any]]] = {}
    for candidate in eval_included:
        structural = next(s for c, s in structurally_admissible if c.candidate_id == candidate.candidate_id)
        evaluation_pass_id = new_evaluation_pass_id()
        evaluator_manifest_id = f"{manifest_id}-ep-eval-{evaluation_pass_id}"
        envelope = build_character_epistemic_context_envelope(
            fixture,
            character_id=character_id,
            candidate=candidate,
            hg_round_id=hg_round_id,
            turn_index=turn_index,
            authority_fingerprint=authority_fingerprint,
            overlay_revision=overlay_revision,
            policy=orch_policy,
        )
        prepared_items.append(
            PreparedProjectionCandidate(
                candidate=candidate,
                structural=structural,
                epistemic_context=envelope,
                evaluation_pass_id=evaluation_pass_id,
                evaluator_manifest_id=evaluator_manifest_id,
            )
        )
        manifests[evaluation_pass_id] = envelope_to_evaluator_contributions(
            envelope,
            manifest_id=evaluator_manifest_id,
        )

    batch = PreparedProjectionBatch(
        schema="hg_plot_cognition_projection_batch_prepared_v1",
        batch_id=new_batch_id(),
        character_id=character_id,
        manifest_id=manifest_id,
        known_by_snapshot_id=known_by_snapshot_id,
        authority_fingerprint=authority_fingerprint,
        overlay_revision=overlay_revision,
        budget=budget,
        binding_digest=binding_digest,
        items=tuple(prepared_items),
        excluded_records=tuple(records),
    )
    _PREPARED_BATCHES[batch.batch_id] = batch
    return PrepareProjectionBatchResult(batch=batch, evaluator_manifests=manifests)


class _SuppliedSemanticEvaluator(CharacterEpistemicLeakageEvaluator):
    """Applies pre-parsed semantic results supplied by DSH finalize (no inference)."""

    def __init__(self, results_by_pass_id: dict[str, SemanticEvaluationResult]) -> None:
        self._results = results_by_pass_id

    def evaluate(
        self,
        *,
        character_id: str,
        candidate_text: str,
        basis_exposure: Any,
        known_by_snapshot_id: str,
    ) -> SemanticEvaluationResult:
        del character_id, candidate_text, basis_exposure, known_by_snapshot_id
        raise RuntimeError("supplied evaluator must not be called during finalize")


def _validate_rewrite_guidance(semantic: SemanticEvaluationResult) -> bool:
    if semantic.verdict != "rewrite_required":
        return True
    guidance = semantic.regeneration_guidance
    if guidance is None:
        return False
    if hasattr(guidance, "safe_constraints"):
        return bool(guidance.safe_constraints)
    if isinstance(guidance, dict):
        return bool(guidance.get("safe_constraints"))
    return False


def finalize_character_projection_batch(
    fixture: LiveSession,
    *,
    batch_id: str,
    semantic_results: tuple[CharacterProjectionSemanticResult, ...],
    hg_round_id: str,
    turn_index: int,
    regeneration_inputs: dict[str, RegenerationCycleInput] | None = None,
    second_pass_results: dict[str, SemanticEvaluationResult] | None = None,
    base_priority: int = 19,
    source_kind_map: dict[str, str] | None = None,
) -> FinalizedProjectionBatch:
    """Apply supplied semantic results; never calls DSH or live inference."""
    batch = _PREPARED_BATCHES.pop(batch_id, None)
    if batch is None:
        raise ValueError(f"unknown or expired projection batch: {batch_id}")

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
        raise ValueError("stale projection batch binding mismatch; fail closed")

    results_by_pass = {item.evaluation_pass_id: item for item in semantic_results}
    kind_map = source_kind_map or {
        "overlay_goal": "storyteller_progression_hooks",
        "overlay_pressure": "storyteller_active_tensions",
        "overlay_character_candidate": "storyteller_thematic_context",
        "model_a_observation": "storyteller_thematic_context",
        "model_a_tension": "storyteller_active_tensions",
        "model_a_opportunity": "storyteller_progression_hooks",
    }
    records: list[CandidateProjectionRecord] = list(batch.excluded_records)
    approved: list[ApprovedProjection] = []
    pending_regenerations: list[RegenerationRequestDescriptor] = []

    for item in batch.items:
        supplied = results_by_pass.get(item.evaluation_pass_id)
        structural = item.structural
        candidate = item.candidate
        basis = structural.basis_exposure

        if supplied is None:
            unavailable = SemanticEvaluationResult(
                verdict="evaluator_unavailable",
                rationale="semantic result not supplied for evaluation pass",
            )
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=batch.character_id,
                    outcome="semantic_evaluator_unavailable",
                    structural=structural,
                    semantic=unavailable,
                    regeneration=None,
                    original_text=candidate.text,
                    regenerated_text=None,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=batch.authority_fingerprint,
                    overlay_revision=batch.overlay_revision,
                    rationale=unavailable.rationale,
                )
            )
            continue

        semantic = supplied.semantic
        if semantic.verdict in {"evaluator_unavailable", "withhold"}:
            outcome = (
                "semantic_evaluator_unavailable"
                if semantic.verdict == "evaluator_unavailable"
                else "semantic_withhold"
            )
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=batch.character_id,
                    outcome=outcome,
                    structural=structural,
                    semantic=semantic,
                    regeneration=None,
                    original_text=candidate.text,
                    regenerated_text=None,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=batch.authority_fingerprint,
                    overlay_revision=batch.overlay_revision,
                    rationale=semantic.rationale,
                )
            )
            continue

        regeneration: RegenerationCycleResult | None = None
        final_candidate = candidate
        final_semantic = semantic
        regenerated_text: str | None = None

        if semantic.verdict == "rewrite_required":
            if not _validate_rewrite_guidance(semantic):
                records.append(
                    CandidateProjectionRecord(
                        candidate_id=candidate.candidate_id,
                        source_kind=candidate.source_kind,
                        consumer="character",
                        character_id=batch.character_id,
                        outcome="semantic_evaluator_unavailable",
                        structural=structural,
                        semantic=semantic,
                        regeneration=None,
                        original_text=candidate.text,
                        regenerated_text=None,
                        final_text=None,
                        projection_mode=None,
                        lineage=candidate.lineage,
                        known_by_snapshot_id=known_by_snapshot_id,
                        authority_fingerprint=batch.authority_fingerprint,
                        overlay_revision=batch.overlay_revision,
                        rationale="rewrite_required without valid regeneration guidance",
                    )
                )
                continue
            guidance = supplied.regeneration_guidance or semantic.regeneration_guidance
            if guidance is None:
                continue
            regen_input = (regeneration_inputs or {}).get(candidate.candidate_id)
            if regen_input is None or regen_input.regenerated_candidate is None:
                pending_regenerations.append(
                    RegenerationRequestDescriptor(
                        batch_id=batch.batch_id,
                        candidate_id=candidate.candidate_id,
                        evaluation_pass_id=item.evaluation_pass_id,
                        original_candidate=candidate,
                        regeneration_guidance=guidance,
                        forensic_rationale=semantic.forensic_rationale or semantic.rationale,
                    )
                )
                records.append(
                    CandidateProjectionRecord(
                        candidate_id=candidate.candidate_id,
                        source_kind=candidate.source_kind,
                        consumer="character",
                        character_id=batch.character_id,
                        outcome="semantic_rewrite_required",
                        structural=structural,
                        semantic=semantic,
                        regeneration=None,
                        original_text=candidate.text,
                        regenerated_text=None,
                        final_text=None,
                        projection_mode=None,
                        lineage=candidate.lineage,
                        known_by_snapshot_id=known_by_snapshot_id,
                        authority_fingerprint=batch.authority_fingerprint,
                        overlay_revision=batch.overlay_revision,
                        rationale=semantic.rationale,
                    )
                )
                continue
            second = (second_pass_results or {}).get(item.evaluation_pass_id)
            if second is None:
                evaluator = _SuppliedSemanticEvaluator({})
                cycle = apply_regeneration_cycle(
                    regen_input,
                    evaluator=evaluator,
                    character_id=batch.character_id,
                    known_by_snapshot_id=known_by_snapshot_id,
                    basis_exposure=basis,
                )
            else:
                cycle = _apply_regeneration_with_second_result(
                    regen_input,
                    second_result=second,
                    character_id=batch.character_id,
                    known_by_snapshot_id=known_by_snapshot_id,
                )
            regeneration = cycle
            if cycle.final_candidate is not None and cycle.final_verdict == "pass":
                final_candidate = cycle.final_candidate
                final_semantic = SemanticEvaluationResult(
                    verdict="pass",
                    rationale=cycle.rationale,
                )
                regenerated_text = cycle.final_candidate.text
            elif cycle.attempted or cycle.unavailable:
                outcome: str = (
                    "regeneration_unavailable" if cycle.unavailable else "regenerated_candidate_failed"
                )
                records.append(
                    CandidateProjectionRecord(
                        candidate_id=candidate.candidate_id,
                        source_kind=candidate.source_kind,
                        consumer="character",
                        character_id=batch.character_id,
                        outcome=outcome,  # type: ignore[arg-type]
                        structural=structural,
                        semantic=semantic,
                        regeneration=regeneration,
                        original_text=candidate.text,
                        regenerated_text=regenerated_text,
                        final_text=None,
                        projection_mode=None,
                        lineage=candidate.lineage,
                        known_by_snapshot_id=known_by_snapshot_id,
                        authority_fingerprint=batch.authority_fingerprint,
                        overlay_revision=batch.overlay_revision,
                        rationale=regeneration.rationale,
                    )
                )
                continue

        mode = _projection_mode_for(structural, final_semantic.verdict == "pass")
        if mode is None or final_semantic.verdict != "pass":
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=batch.character_id,
                    outcome="semantic_withhold",
                    structural=structural,
                    semantic=semantic,
                    regeneration=regeneration,
                    original_text=candidate.text,
                    regenerated_text=regenerated_text,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=batch.authority_fingerprint,
                    overlay_revision=batch.overlay_revision,
                    rationale=final_semantic.rationale,
                )
            )
            continue

        approved.append(
            ApprovedProjection(
                candidate=final_candidate,
                mode=mode,
                final_text=final_candidate.text,
                semantic=final_semantic,
                regeneration=regeneration,
            )
        )
        records.append(
            CandidateProjectionRecord(
                candidate_id=candidate.candidate_id,
                source_kind=candidate.source_kind,
                consumer="character",
                character_id=batch.character_id,
                outcome="regenerated_candidate_passed" if regenerated_text else "semantic_pass",
                structural=structural,
                semantic=semantic,
                regeneration=regeneration,
                original_text=candidate.text,
                regenerated_text=regenerated_text,
                final_text=final_candidate.text,
                projection_mode=mode,
                lineage=candidate.lineage,
                known_by_snapshot_id=known_by_snapshot_id,
                authority_fingerprint=batch.authority_fingerprint,
                overlay_revision=batch.overlay_revision,
                rationale=final_semantic.rationale,
            )
        )

    included, excluded = apply_projection_budget(tuple(approved), batch.budget)
    for item in excluded:
        records.append(
            CandidateProjectionRecord(
                candidate_id=item.candidate.candidate_id,
                source_kind=item.candidate.source_kind,
                consumer="character",
                character_id=batch.character_id,
                outcome="projection_budget_excluded",
                structural=None,
                semantic=item.semantic,
                regeneration=item.regeneration,
                original_text=item.candidate.text,
                regenerated_text=None,
                final_text=item.final_text,
                projection_mode=item.mode,
                lineage=item.candidate.lineage,
                known_by_snapshot_id=known_by_snapshot_id,
                authority_fingerprint=batch.authority_fingerprint,
                overlay_revision=batch.overlay_revision,
                rationale="excluded by projection budget",
            )
        )

    contributions = []
    priority = base_priority
    for item in sorted(included, key=lambda x: deterministic_candidate_order_key(x.candidate)):
        source_kind = kind_map.get(item.candidate.source_kind, "storyteller_thematic_context")
        contributions.append(
            render_character_prompt_contribution(
                manifest_id=batch.manifest_id,
                candidate=item.candidate,
                approved_text=item.final_text,
                mode=item.mode,
                priority=priority,
                character_id=batch.character_id,
                source_kind=source_kind,
            )
        )
        priority += 1

    from .plot_cognition_projection_contract import ProjectionForensicHandoff

    projected_count = len(contributions)
    withheld_count = sum(
        1
        for record in records
        if record.outcome
        not in {
            "projected_full",
            "projected_prospective",
            "semantic_pass",
            "regenerated_candidate_passed",
        }
    )
    forensic = ProjectionForensicHandoff(
        schema=PROJECTION_FORENSIC_HANDOFF_SCHEMA,
        handoff_id=new_handoff_id(),
        consumer="character",
        character_id=batch.character_id,
        records=tuple(records),
        projected_count=projected_count,
        withheld_count=withheld_count,
    )
    return FinalizedProjectionBatch(
        contributions=tuple(contributions),
        forensic=forensic,
        pending_regenerations=tuple(pending_regenerations),
    )


def _apply_regeneration_with_second_result(
    cycle: RegenerationCycleInput,
    *,
    second_result: SemanticEvaluationResult,
    character_id: str,
    known_by_snapshot_id: str,
) -> RegenerationCycleResult:
    del character_id, known_by_snapshot_id
    original = cycle.evaluator_result
    if original.verdict != "rewrite_required":
        return RegenerationCycleResult(
            attempted=False,
            unavailable=False,
            original_verdict=original.verdict,
            regenerated_verdict=None,
            final_candidate=cycle.original_candidate,
            final_verdict=original.verdict,
            rationale="regeneration not required",
        )
    if cycle.regenerated_candidate is None:
        return RegenerationCycleResult(
            attempted=False,
            unavailable=True,
            original_verdict=original.verdict,
            regenerated_verdict=None,
            final_candidate=None,
            final_verdict="withhold",
            rationale="regeneration unavailable; projection fails closed",
        )
    if second_result.verdict == "pass":
        return RegenerationCycleResult(
            attempted=True,
            unavailable=False,
            original_verdict=original.verdict,
            regenerated_verdict=second_result.verdict,
            final_candidate=cycle.regenerated_candidate,
            final_verdict="pass",
            rationale="regenerated candidate passed semantic evaluation",
        )
    return RegenerationCycleResult(
        attempted=True,
        unavailable=False,
        original_verdict=original.verdict,
        regenerated_verdict=second_result.verdict,
        final_candidate=None,
        final_verdict=second_result.verdict,
        rationale="regenerated candidate failed semantic evaluation",
    )


def finalize_batch_to_service_result(
    finalized: FinalizedProjectionBatch,
) -> ProjectionServiceResult:
    return ProjectionServiceResult(
        contributions=finalized.contributions,
        forensic=finalized.forensic,
    )

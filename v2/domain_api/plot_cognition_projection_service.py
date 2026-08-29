"""Plot Cognition consumer projection service (#62).

Shared projection infrastructure with Director/Character behavior profiles, Layer A
structural eligibility, Layer B semantic safety, bounded evaluation/projection, and
forensic handoff envelopes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .character_epistemic import (
    compute_known_by_snapshot_id,
    resolve_basis_exposure,
)
from .contract import PromptContribution
from .librarian_contract import StableReference
from .plot_cognition_overlay_contract import (
    CognitionApplicability,
    GlobalPlotFrame,
    PlotGoal,
    UnresolvedNarrativePressure,
)
from .plot_cognition_overlay_store import OperativePlotCognitionView
from .plot_cognition_projection_contract import (
    PROJECTION_FORENSIC_HANDOFF_SCHEMA,
    BasisExposureResult,
    CandidateProjectionRecord,
    CharacterAdvisoryCandidate,
    CognitionSourceKind,
    MODEL_A_CHARACTER_SCOPE_REF_KIND,
    ProjectionBudget,
    ProjectionConsumer,
    ProjectionForensicHandoff,
    ProjectionInvalidationContext,
    ProjectionMode,
    ProjectionOutcomeKind,
    RegenerationCycleInput,
    RegenerationCycleResult,
    SemanticEvaluationResult,
    StructuralEligibilityResult,
    frame_derived_character_candidate,
    global_goal_derived_character_candidate,
    new_candidate_id,
    new_handoff_id,
    overlay_goal_to_character_candidate,
    overlay_pressure_to_character_candidate,
)
from .plot_cognition_projection_semantic_safety import (
    CharacterEpistemicLeakageEvaluator,
)
from .session_state import LiveSession

CHARACTER_ADVISORY_HEADER = (
    "STORYTELLER CHARACTER ADVISORY (advisory interpretation; not authoritative):"
)
DIRECTOR_OVERLAY_HEADER = "PLOT COGNITION OVERLAY (advisory; not authoritative):"


@dataclass(frozen=True)
class ApprovedProjection:
    candidate: CharacterAdvisoryCandidate
    mode: ProjectionMode
    final_text: str
    semantic: SemanticEvaluationResult
    regeneration: RegenerationCycleResult | None


@dataclass(frozen=True)
class ProjectionServiceResult:
    contributions: tuple[PromptContribution, ...]
    forensic: ProjectionForensicHandoff


def _applicability_relevant(
    applicability: CognitionApplicability | None,
    character_id: str,
) -> bool:
    if applicability is None:
        return False
    kind = applicability.applicability_kind
    involved = {str(item) for item in applicability.involved_character_ids}
    primary = str(applicability.primary_character_id or "").strip()
    if kind == "global":
        return False
    if kind == "character":
        return primary.lower() == character_id.lower() and character_id in involved
    if kind == "relational":
        return character_id in involved
    return False


def assess_structural_eligibility(
    fixture: LiveSession,
    *,
    candidate: CharacterAdvisoryCandidate,
    character_id: str,
    forbid_direct_global: bool = True,
    forbid_direct_frame: bool = True,
) -> StructuralEligibilityResult:
    applicability = candidate.applicability
    if forbid_direct_frame and candidate.source_kind == "overlay_frame":
        return StructuralEligibilityResult(
            eligible=False,
            code="ineligible_frame_direct",
            character_relevant=False,
            basis_exposure=None,
            exposable_basis_summary=None,
            rationale="GlobalPlotFrame must never be directly projected to Character",
        )
    if forbid_direct_global and applicability and applicability.applicability_kind == "global":
        if candidate.source_kind in {"overlay_goal", "overlay_pressure"}:
            return StructuralEligibilityResult(
                eligible=False,
                code="ineligible_global_direct",
                character_relevant=False,
                basis_exposure=None,
                exposable_basis_summary=None,
                rationale="global PlotGoal/pressure must not be directly projected to Character",
            )

    character_relevant = _applicability_relevant(applicability, character_id)
    if candidate.source_kind.startswith("model_a_"):
        if not model_a_has_structural_character_evidence(
            candidate.structural_evidence_refs,
            character_id=character_id,
        ):
            return StructuralEligibilityResult(
                eligible=False,
                code="ineligible_model_a_insufficient",
                character_relevant=False,
                basis_exposure=None,
                exposable_basis_summary=None,
                rationale="Model A Character projection requires structural character_scope evidence",
            )
        character_relevant = True

    if applicability and not character_relevant and candidate.source_kind.startswith("overlay_"):
        return StructuralEligibilityResult(
            eligible=False,
            code="ineligible_applicability",
            character_relevant=False,
            basis_exposure=resolve_basis_exposure(
                fixture,
                character_id=character_id,
                basis_refs=candidate.basis_refs,
            ),
            exposable_basis_summary=None,
            rationale="cognition not applicable to target Character",
        )

    basis = resolve_basis_exposure(
        fixture,
        character_id=character_id,
        basis_refs=candidate.basis_refs,
    )
    if not basis.resolved:
        return StructuralEligibilityResult(
            eligible=False,
            code="ineligible_basis_unresolvable",
            character_relevant=character_relevant,
            basis_exposure=basis,
            exposable_basis_summary=None,
            rationale="required basis evidence could not be resolved",
        )
    if not basis.epistemic_eligible and not (
        not candidate.basis_refs
        and candidate.creation_provenance
        and candidate.creation_provenance.source
        in {"storyteller", "authored_material", "character_committed", "player_committed"}
    ):
        return StructuralEligibilityResult(
            eligible=False,
            code="ineligible_epistemic",
            character_relevant=character_relevant,
            basis_exposure=basis,
            exposable_basis_summary=None,
            rationale="relevance without epistemic eligibility",
        )

    exposable_summary = (
        ", ".join(basis.exposable_facet_ids) if basis.exposable_facet_ids else None
    )
    return StructuralEligibilityResult(
        eligible=True,
        code="eligible",
        character_relevant=character_relevant or candidate.source_kind.startswith("model_a_"),
        basis_exposure=basis,
        exposable_basis_summary=exposable_summary,
        rationale="structurally eligible",
    )


def model_a_has_structural_character_evidence(
    evidence_refs: tuple[StableReference, ...],
    *,
    character_id: str,
) -> bool:
    needle = character_id.strip().lower()
    if not needle:
        return False
    for ref in evidence_refs:
        kind = str(ref.ref_kind or "").strip()
        stable = str(ref.stable_ref or "").strip().lower()
        if kind == MODEL_A_CHARACTER_SCOPE_REF_KIND and stable == needle:
            return True
        if kind == "character" and stable == needle:
            return True
    return False


def deterministic_candidate_order_key(candidate: CharacterAdvisoryCandidate) -> tuple[str, str]:
    return (candidate.source_kind, candidate.candidate_id)


def apply_evaluation_budget(
    candidates: tuple[CharacterAdvisoryCandidate, ...],
    budget: ProjectionBudget,
) -> tuple[tuple[CharacterAdvisoryCandidate, ...], tuple[CharacterAdvisoryCandidate, ...]]:
    ordered = tuple(sorted(candidates, key=deterministic_candidate_order_key))
    included = ordered[: max(0, budget.max_evaluation_candidates)]
    excluded = ordered[max(0, budget.max_evaluation_candidates) :]
    return included, excluded


def apply_projection_budget(
    approved: tuple[ApprovedProjection, ...],
    budget: ProjectionBudget,
) -> tuple[tuple[ApprovedProjection, ...], tuple[ApprovedProjection, ...]]:
    ordered = tuple(
        sorted(
            approved,
            key=lambda item: deterministic_candidate_order_key(item.candidate),
        )
    )
    included = ordered[: max(0, budget.max_projection_candidates)]
    excluded = ordered[max(0, budget.max_projection_candidates) :]
    return included, excluded


def apply_regeneration_cycle(
    cycle: RegenerationCycleInput,
    *,
    evaluator: CharacterEpistemicLeakageEvaluator,
    character_id: str,
    known_by_snapshot_id: str,
    basis_exposure: BasisExposureResult | None,
) -> RegenerationCycleResult:
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
    second = evaluator.evaluate(
        character_id=character_id,
        candidate_text=cycle.regenerated_candidate.text,
        basis_exposure=basis_exposure,
        known_by_snapshot_id=known_by_snapshot_id,
    )
    if second.verdict == "pass":
        return RegenerationCycleResult(
            attempted=True,
            unavailable=False,
            original_verdict=original.verdict,
            regenerated_verdict=second.verdict,
            final_candidate=cycle.regenerated_candidate,
            final_verdict="pass",
            rationale="regenerated candidate passed semantic evaluation",
        )
    return RegenerationCycleResult(
        attempted=True,
        unavailable=False,
        original_verdict=original.verdict,
        regenerated_verdict=second.verdict,
        final_candidate=None,
        final_verdict=second.verdict,
        rationale="regenerated candidate failed semantic evaluation",
    )


def render_character_prompt_contribution(
    *,
    manifest_id: str,
    candidate: CharacterAdvisoryCandidate,
    approved_text: str,
    mode: ProjectionMode,
    priority: int,
    character_id: str,
    source_kind: str,
) -> PromptContribution:
    content = f"{CHARACTER_ADVISORY_HEADER}\n{approved_text.strip()}"
    return PromptContribution(
        contribution_id=f"{manifest_id}-plot-proj-{candidate.candidate_id}",
        source_kind=source_kind,  # type: ignore[arg-type]
        authority_class="suggestive",
        knowledge_ids=tuple(candidate.lineage),
        priority=priority,
        content=content,
        provenance={
            "projection_kind": "plot_cognition_projection_service",
            "character_id": character_id,
            "candidate_id": candidate.candidate_id,
            "lineage": list(candidate.lineage),
            "projection_mode": mode,
            "approved_text_only": True,
        },
    )


def _projection_mode_for(
    structural: StructuralEligibilityResult,
    semantic_pass: bool,
) -> ProjectionMode | None:
    if not semantic_pass:
        return None
    basis = structural.basis_exposure
    if basis and basis.has_hidden_basis and basis.exposable_facet_ids:
        return "projected_prospective"
    if basis and basis.has_hidden_basis and not basis.exposable_facet_ids:
        return None
    return "projected_full"


def project_character_candidates(
    fixture: LiveSession,
    *,
    manifest_id: str,
    character_id: str,
    candidates: tuple[CharacterAdvisoryCandidate, ...],
    budget: ProjectionBudget,
    evaluator: CharacterEpistemicLeakageEvaluator | None = None,
    regeneration_inputs: dict[str, RegenerationCycleInput] | None = None,
    overlay_revision: int | None = None,
    authority_fingerprint: str | None = None,
    base_priority: int = 19,
    source_kind_map: dict[CognitionSourceKind, str] | None = None,
) -> ProjectionServiceResult:
    known_by_snapshot_id = compute_known_by_snapshot_id(fixture, character_id)
    regen_inputs = regeneration_inputs or {}
    kind_map = source_kind_map or {
        "overlay_goal": "storyteller_progression_hooks",
        "overlay_pressure": "storyteller_active_tensions",
        "overlay_character_candidate": "storyteller_thematic_context",
        "model_a_observation": "storyteller_thematic_context",
        "model_a_tension": "storyteller_active_tensions",
        "model_a_opportunity": "storyteller_progression_hooks",
    }
    records: list[CandidateProjectionRecord] = []
    structurally_admissible: list[tuple[CharacterAdvisoryCandidate, StructuralEligibilityResult]] = []

    for candidate in candidates:
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

    eval_included, eval_excluded = apply_evaluation_budget(
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

    approved: list[ApprovedProjection] = []
    structural_by_id = {item[0].candidate_id: item[1] for item in structurally_admissible}
    for candidate in eval_included:
        structural = structural_by_id[candidate.candidate_id]
        basis = structural.basis_exposure
        if evaluator is None:
            unavailable = SemanticEvaluationResult(
                verdict="evaluator_unavailable",
                rationale="production semantic evaluator not supplied; projection fails closed",
            )
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=character_id,
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
                    authority_fingerprint=authority_fingerprint,
                    overlay_revision=overlay_revision,
                    rationale=unavailable.rationale,
                )
            )
            continue
        semantic = evaluator.evaluate(
            character_id=character_id,
            candidate_text=candidate.text,
            basis_exposure=basis,
            known_by_snapshot_id=known_by_snapshot_id,
        )
        regeneration: RegenerationCycleResult | None = None
        final_candidate = candidate
        final_semantic = semantic
        regenerated_text: str | None = None

        if semantic.verdict == "rewrite_required":
            cycle = apply_regeneration_cycle(
                regen_inputs.get(
                    candidate.candidate_id,
                    RegenerationCycleInput(
                        original_candidate=candidate,
                        evaluator_result=semantic,
                    ),
                ),
                evaluator=evaluator,
                character_id=character_id,
                known_by_snapshot_id=known_by_snapshot_id,
                basis_exposure=basis,
            )
            regeneration = cycle
            if cycle.final_candidate is not None and cycle.final_verdict == "pass":
                final_candidate = cycle.final_candidate
                final_semantic = SemanticEvaluationResult(
                    verdict="pass",
                    rationale=cycle.rationale,
                )
                regenerated_text = cycle.final_candidate.text
                records.append(
                    CandidateProjectionRecord(
                        candidate_id=candidate.candidate_id,
                        source_kind=candidate.source_kind,
                        consumer="character",
                        character_id=character_id,
                        outcome="regenerated_candidate_passed",
                        structural=structural,
                        semantic=semantic,
                        regeneration=regeneration,
                        original_text=candidate.text,
                        regenerated_text=regenerated_text,
                        final_text=regenerated_text,
                        projection_mode=_projection_mode_for(structural, True),
                        lineage=candidate.lineage,
                        known_by_snapshot_id=known_by_snapshot_id,
                        authority_fingerprint=authority_fingerprint,
                        overlay_revision=overlay_revision,
                        rationale=regeneration.rationale,
                    )
                )
            elif cycle.attempted:
                outcome: ProjectionOutcomeKind = "regenerated_candidate_failed"
                records.append(
                    CandidateProjectionRecord(
                        candidate_id=candidate.candidate_id,
                        source_kind=candidate.source_kind,
                        consumer="character",
                        character_id=character_id,
                        outcome=outcome,
                        structural=structural,
                        semantic=semantic,
                        regeneration=regeneration,
                        original_text=candidate.text,
                        regenerated_text=regenerated_text,
                        final_text=None,
                        projection_mode=None,
                        lineage=candidate.lineage,
                        known_by_snapshot_id=known_by_snapshot_id,
                        authority_fingerprint=authority_fingerprint,
                        overlay_revision=overlay_revision,
                        rationale=regeneration.rationale,
                    )
                )
                continue
            elif cycle.unavailable:
                records.append(
                    CandidateProjectionRecord(
                        candidate_id=candidate.candidate_id,
                        source_kind=candidate.source_kind,
                        consumer="character",
                        character_id=character_id,
                        outcome="regeneration_unavailable",
                        structural=structural,
                        semantic=semantic,
                        regeneration=regeneration,
                        original_text=candidate.text,
                        regenerated_text=None,
                        final_text=None,
                        projection_mode=None,
                        lineage=candidate.lineage,
                        known_by_snapshot_id=known_by_snapshot_id,
                        authority_fingerprint=authority_fingerprint,
                        overlay_revision=overlay_revision,
                        rationale=regeneration.rationale,
                    )
                )
                continue

        if semantic.verdict == "evaluator_unavailable":
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=character_id,
                    outcome="semantic_evaluator_unavailable",
                    structural=structural,
                    semantic=semantic,
                    regeneration=regeneration,
                    original_text=candidate.text,
                    regenerated_text=regenerated_text,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=authority_fingerprint,
                    overlay_revision=overlay_revision,
                    rationale=semantic.rationale,
                )
            )
            continue
        if final_semantic.verdict == "withhold":
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=character_id,
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
                    authority_fingerprint=authority_fingerprint,
                    overlay_revision=overlay_revision,
                    rationale=semantic.rationale,
                )
            )
            continue
        if final_semantic.verdict == "rewrite_required":
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=character_id,
                    outcome="semantic_rewrite_required",
                    structural=structural,
                    semantic=semantic,
                    regeneration=regeneration,
                    original_text=candidate.text,
                    regenerated_text=regenerated_text,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=authority_fingerprint,
                    overlay_revision=overlay_revision,
                    rationale=semantic.rationale,
                )
            )
            continue

        mode = _projection_mode_for(structural, final_semantic.verdict == "pass")
        if mode is None:
            records.append(
                CandidateProjectionRecord(
                    candidate_id=candidate.candidate_id,
                    source_kind=candidate.source_kind,
                    consumer="character",
                    character_id=character_id,
                    outcome="semantic_withhold",
                    structural=structural,
                    semantic=final_semantic,
                    regeneration=regeneration,
                    original_text=candidate.text,
                    regenerated_text=regenerated_text,
                    final_text=None,
                    projection_mode=None,
                    lineage=candidate.lineage,
                    known_by_snapshot_id=known_by_snapshot_id,
                    authority_fingerprint=authority_fingerprint,
                    overlay_revision=overlay_revision,
                    rationale="basis withholding alone does not authorize prospective projection",
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
        outcome_kind: ProjectionOutcomeKind = (
            "projected_prospective" if mode == "projected_prospective" else "projected_full"
        )
        records.append(
            CandidateProjectionRecord(
                candidate_id=candidate.candidate_id,
                source_kind=candidate.source_kind,
                consumer="character",
                character_id=character_id,
                outcome=outcome_kind,
                structural=structural,
                semantic=final_semantic,
                regeneration=regeneration,
                original_text=candidate.text,
                regenerated_text=regenerated_text,
                final_text=final_candidate.text,
                projection_mode=mode,
                lineage=candidate.lineage,
                known_by_snapshot_id=known_by_snapshot_id,
                authority_fingerprint=authority_fingerprint,
                overlay_revision=overlay_revision,
                rationale=final_semantic.rationale,
            )
        )

    proj_included, proj_excluded = apply_projection_budget(tuple(approved), budget)
    included_ids = {item.candidate.candidate_id for item in proj_included}
    for item in proj_excluded:
        records.append(
            CandidateProjectionRecord(
                candidate_id=item.candidate.candidate_id,
                source_kind=item.candidate.source_kind,
                consumer="character",
                character_id=character_id,
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
                authority_fingerprint=authority_fingerprint,
                overlay_revision=overlay_revision,
                rationale="excluded by projection budget",
            )
        )

    contributions: list[PromptContribution] = []
    priority = base_priority
    for item in proj_included:
        contributions.append(
            render_character_prompt_contribution(
                manifest_id=manifest_id,
                candidate=item.candidate,
                approved_text=item.final_text,
                mode=item.mode,
                priority=priority,
                character_id=character_id,
                source_kind=kind_map.get(item.candidate.source_kind, "storyteller_thematic_context"),
            )
        )
        priority += 1

    projected_count = len(contributions)
    withheld_count = sum(
        1
        for record in records
        if record.outcome
        not in {"projected_full", "projected_prospective", "semantic_pass"}
    )
    forensic = ProjectionForensicHandoff(
        schema=PROJECTION_FORENSIC_HANDOFF_SCHEMA,
        handoff_id=new_handoff_id(),
        consumer="character",
        character_id=character_id,
        records=tuple(records),
        projected_count=projected_count,
        withheld_count=withheld_count,
    )
    return ProjectionServiceResult(contributions=tuple(contributions), forensic=forensic)


def collect_overlay_character_candidates(
    view: OperativePlotCognitionView,
    *,
    character_id: str,
    supplemental_candidates: tuple[CharacterAdvisoryCandidate, ...] = (),
) -> tuple[CharacterAdvisoryCandidate, ...]:
    items: list[CharacterAdvisoryCandidate] = []
    for goal in view.goals:
        if goal.applicability.applicability_kind == "global":
            continue
        if _applicability_relevant(goal.applicability, character_id):
            items.append(overlay_goal_to_character_candidate(goal))
    for pressure in view.pressures:
        if pressure.applicability.applicability_kind == "global":
            continue
        if _applicability_relevant(pressure.applicability, character_id):
            items.append(overlay_pressure_to_character_candidate(pressure))
    items.extend(supplemental_candidates)
    return tuple(items)


def project_director_overlay(
    view: OperativePlotCognitionView,
    *,
    manifest_id: str,
    base_priority: int = 17,
) -> tuple[PromptContribution, ...]:
    contributions: list[PromptContribution] = []
    priority = base_priority
    if view.active_frame is not None:
        frame = view.active_frame
        lines = [DIRECTOR_OVERLAY_HEADER, f"Direction sense: {frame.direction_sense.strip()}"]
        for label, value in (
            ("Pacing", frame.pacing_note),
            ("Cross-character", frame.cross_character_note),
            ("Opportunity", frame.opportunity_note),
        ):
            if value and str(value).strip():
                lines.append(f"{label}: {str(value).strip()}")
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-overlay-frame-{frame.frame_id}",
                source_kind="storyteller_narrative_priorities",
                authority_class="suggestive",
                knowledge_ids=(frame.frame_id,),
                priority=priority,
                content="\n".join(lines),
                provenance={
                    "projection_kind": "plot_cognition_projection_service",
                    "consumer_target": "director",
                    "overlay_kind": "global_plot_frame",
                    "frame_id": frame.frame_id,
                },
            )
        )
        priority += 1
    for goal in sorted(view.goals, key=lambda item: item.goal_id):
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-overlay-goal-{goal.goal_id}",
                source_kind="storyteller_narrative_priorities",
                authority_class="suggestive",
                knowledge_ids=(goal.goal_id,),
                priority=priority,
                content=(
                    f"{DIRECTOR_OVERLAY_HEADER}\n"
                    f"Plot goal ({goal.planning_horizon}): {goal.intended_direction.strip()}"
                ),
                provenance={
                    "projection_kind": "plot_cognition_projection_service",
                    "consumer_target": "director",
                    "overlay_kind": "plot_goal",
                    "goal_id": goal.goal_id,
                    "applicability_kind": goal.applicability.applicability_kind,
                },
            )
        )
        priority += 1
    for pressure in sorted(view.pressures, key=lambda item: item.pressure_id):
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-overlay-pressure-{pressure.pressure_id}",
                source_kind="storyteller_active_tensions",
                authority_class="suggestive",
                knowledge_ids=(pressure.pressure_id,),
                priority=priority,
                content=(
                    f"{DIRECTOR_OVERLAY_HEADER}\n"
                    f"Pressure: {pressure.pressure_text.strip()} — {pressure.dramatic_rationale.strip()}"
                ),
                provenance={
                    "projection_kind": "plot_cognition_projection_service",
                    "consumer_target": "director",
                    "overlay_kind": "unresolved_narrative_pressure",
                    "pressure_id": pressure.pressure_id,
                },
            )
        )
        priority += 1
    return tuple(contributions)


def build_projection_invalidation_context(
    *,
    overlay_revision: int | None,
    authority_fingerprint: str | None,
    known_by_snapshot_id: str | None,
    cognition_lifecycle_token: str | None = None,
    model_a_package_id: str | None = None,
    packaging_binding_digest: str | None = None,
) -> ProjectionInvalidationContext:
    return ProjectionInvalidationContext(
        overlay_revision=overlay_revision,
        authority_fingerprint=authority_fingerprint,
        known_by_snapshot_id=known_by_snapshot_id,
        cognition_lifecycle_token=cognition_lifecycle_token,
        model_a_package_id=model_a_package_id,
        packaging_binding_digest=packaging_binding_digest,
    )


def overlay_frame_candidate_for_tests(
    frame: GlobalPlotFrame,
    text: str,
) -> CharacterAdvisoryCandidate:
    return frame_derived_character_candidate(frame, text=text)


def overlay_global_goal_candidate_for_tests(
    goal: PlotGoal,
    text: str,
    *,
    character_id: str,
) -> CharacterAdvisoryCandidate:
    return global_goal_derived_character_candidate(
        goal,
        text=text,
        character_id=character_id,
    )

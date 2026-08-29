"""Storyteller consumer projection and epistemic-isolation contracts (#62).

Defines normative types for overlay + Model A advisory projection to Director/Character
consumers. Orchestration (#63) and durable forensic storage (#64) are out of scope.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from .librarian_contract import StableReference
from .plot_cognition_overlay_contract import (
    CognitionApplicability,
    CreationProvenance,
    GlobalPlotFrame,
    PlotGoal,
    UnresolvedNarrativePressure,
)

PROJECTION_FORENSIC_HANDOFF_SCHEMA = "hg_plot_cognition_projection_forensic_handoff_v1"
MODEL_A_CHARACTER_SCOPE_REF_KIND = "character_scope"

ProjectionConsumer = Literal["director", "character"]
ProjectionMode = Literal["projected_full", "projected_prospective"]
SemanticVerdictKind = Literal[
    "pass",
    "withhold",
    "rewrite_required",
    "evaluator_unavailable",
]
StructuralEligibilityCode = Literal[
    "eligible",
    "ineligible_applicability",
    "ineligible_epistemic",
    "ineligible_basis_unresolvable",
    "ineligible_global_direct",
    "ineligible_frame_direct",
    "ineligible_model_a_insufficient",
    "ineligible_inactive",
    "ineligible_overlay_unavailable",
]
ProjectionOutcomeKind = Literal[
    "structurally_ineligible",
    "evaluation_budget_excluded",
    "semantic_pass",
    "semantic_withhold",
    "semantic_rewrite_required",
    "semantic_evaluator_unavailable",
    "regeneration_attempted",
    "regeneration_unavailable",
    "regenerated_candidate_passed",
    "regenerated_candidate_failed",
    "projected_full",
    "projected_prospective",
    "projection_budget_excluded",
]
CognitionSourceKind = Literal[
    "overlay_goal",
    "overlay_pressure",
    "overlay_frame",
    "overlay_character_candidate",
    "model_a_observation",
    "model_a_tension",
    "model_a_opportunity",
    "model_a_priority",
    "model_a_thread",
]


@dataclass(frozen=True)
class ProjectionBudget:
    """Caller-supplied bounds; production tuning belongs to #63/#65."""

    max_evaluation_candidates: int
    max_projection_candidates: int


@dataclass(frozen=True)
class CharacterAdvisoryCandidate:
    """Hard semantic boundary for Character prompt exposure."""

    candidate_id: str
    text: str
    source_kind: CognitionSourceKind
    lineage: tuple[str, ...]
    basis_refs: tuple[StableReference, ...]
    creation_provenance: CreationProvenance | None = None
    applicability: CognitionApplicability | None = None
    prospective_only: bool = False
    structural_evidence_refs: tuple[StableReference, ...] = ()
    host_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "text": self.text,
            "source_kind": self.source_kind,
            "lineage": list(self.lineage),
            "basis_refs": [
                {
                    "ref_kind": ref.ref_kind,
                    "stable_ref": ref.stable_ref,
                    "display_hint": ref.display_hint,
                }
                for ref in self.basis_refs
            ],
            "creation_provenance": (
                {
                    "source": self.creation_provenance.source,
                    "provenance_note": self.creation_provenance.provenance_note,
                }
                if self.creation_provenance
                else None
            ),
            "applicability": (
                {
                    "applicability_kind": self.applicability.applicability_kind,
                    "primary_character_id": self.applicability.primary_character_id,
                    "involved_character_ids": list(self.applicability.involved_character_ids),
                }
                if self.applicability
                else None
            ),
            "prospective_only": self.prospective_only,
            "structural_evidence_refs": [
                {
                    "ref_kind": ref.ref_kind,
                    "stable_ref": ref.stable_ref,
                    "display_hint": ref.display_hint,
                }
                for ref in self.structural_evidence_refs
            ],
            "host_metadata": dict(self.host_metadata),
        }


@dataclass(frozen=True)
class BasisExposureResult:
    resolved: bool
    exposable_facet_ids: tuple[str, ...]
    withheld_facet_ids: tuple[str, ...]
    has_hidden_basis: bool
    epistemic_eligible: bool
    rationale: str


@dataclass(frozen=True)
class StructuralEligibilityResult:
    eligible: bool
    code: StructuralEligibilityCode
    character_relevant: bool
    basis_exposure: BasisExposureResult | None
    exposable_basis_summary: str | None
    rationale: str


@dataclass(frozen=True)
class SemanticEvaluationResult:
    verdict: SemanticVerdictKind
    rationale: str
    leak_indicators: tuple[str, ...] = ()
    forensic_rationale: str | None = None
    regeneration_guidance: Any | None = None  # RegenerationGuidance when rewrite_required


@dataclass(frozen=True)
class RegenerationCycleInput:
    original_candidate: CharacterAdvisoryCandidate
    evaluator_result: SemanticEvaluationResult
    regenerated_candidate: CharacterAdvisoryCandidate | None = None


@dataclass(frozen=True)
class RegenerationCycleResult:
    attempted: bool
    unavailable: bool
    original_verdict: SemanticVerdictKind
    regenerated_verdict: SemanticVerdictKind | None
    final_candidate: CharacterAdvisoryCandidate | None
    final_verdict: SemanticVerdictKind
    rationale: str


@dataclass(frozen=True)
class CandidateProjectionRecord:
    candidate_id: str
    source_kind: CognitionSourceKind
    consumer: ProjectionConsumer
    character_id: str | None
    outcome: ProjectionOutcomeKind
    structural: StructuralEligibilityResult | None
    semantic: SemanticEvaluationResult | None
    regeneration: RegenerationCycleResult | None
    original_text: str
    regenerated_text: str | None
    final_text: str | None
    projection_mode: ProjectionMode | None
    lineage: tuple[str, ...]
    known_by_snapshot_id: str | None
    authority_fingerprint: str | None
    overlay_revision: int | None
    rationale: str


@dataclass(frozen=True)
class ProjectionForensicHandoff:
    schema: str
    handoff_id: str
    consumer: ProjectionConsumer
    character_id: str | None
    records: tuple[CandidateProjectionRecord, ...]
    projected_count: int
    withheld_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "handoff_id": self.handoff_id,
            "consumer": self.consumer,
            "character_id": self.character_id,
            "projected_count": self.projected_count,
            "withheld_count": self.withheld_count,
            "records": [
                {
                    "candidate_id": record.candidate_id,
                    "source_kind": record.source_kind,
                    "consumer": record.consumer,
                    "character_id": record.character_id,
                    "outcome": record.outcome,
                    "original_text": record.original_text,
                    "regenerated_text": record.regenerated_text,
                    "final_text": record.final_text,
                    "projection_mode": record.projection_mode,
                    "lineage": list(record.lineage),
                    "known_by_snapshot_id": record.known_by_snapshot_id,
                    "authority_fingerprint": record.authority_fingerprint,
                    "overlay_revision": record.overlay_revision,
                    "rationale": record.rationale,
                    "structural": (
                        {
                            "eligible": record.structural.eligible,
                            "code": record.structural.code,
                            "character_relevant": record.structural.character_relevant,
                            "rationale": record.structural.rationale,
                            "exposable_basis_summary": record.structural.exposable_basis_summary,
                        }
                        if record.structural
                        else None
                    ),
                    "semantic": (
                        {
                            "verdict": record.semantic.verdict,
                            "rationale": record.semantic.rationale,
                            "leak_indicators": list(record.semantic.leak_indicators),
                        }
                        if record.semantic
                        else None
                    ),
                    "regeneration": (
                        {
                            "attempted": record.regeneration.attempted,
                            "unavailable": record.regeneration.unavailable,
                            "original_verdict": record.regeneration.original_verdict,
                            "regenerated_verdict": record.regeneration.regenerated_verdict,
                            "final_verdict": record.regeneration.final_verdict,
                            "rationale": record.regeneration.rationale,
                        }
                        if record.regeneration
                        else None
                    ),
                }
                for record in self.records
            ],
        }


@dataclass(frozen=True)
class ProjectionInvalidationContext:
    overlay_revision: int | None
    authority_fingerprint: str | None
    known_by_snapshot_id: str | None
    cognition_lifecycle_token: str | None
    model_a_package_id: str | None
    packaging_binding_digest: str | None


def new_handoff_id() -> str:
    return f"proj-handoff-{uuid.uuid4().hex[:12]}"


def new_candidate_id(prefix: str = "char-cand") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def projection_invalidation_predicates_match(
    prior: ProjectionInvalidationContext,
    current: ProjectionInvalidationContext,
) -> bool:
    """Return True when reprojection is required."""
    fields = (
        "overlay_revision",
        "authority_fingerprint",
        "known_by_snapshot_id",
        "cognition_lifecycle_token",
        "model_a_package_id",
        "packaging_binding_digest",
    )
    for name in fields:
        if getattr(prior, name) != getattr(current, name):
            return True
    return False


def overlay_goal_to_character_candidate(goal: PlotGoal) -> CharacterAdvisoryCandidate:
    return CharacterAdvisoryCandidate(
        candidate_id=goal.goal_id,
        text=goal.intended_direction.strip(),
        source_kind="overlay_goal",
        lineage=(goal.goal_id,),
        basis_refs=goal.basis_refs,
        creation_provenance=goal.creation_provenance,
        applicability=goal.applicability,
    )


def overlay_pressure_to_character_candidate(
    pressure: UnresolvedNarrativePressure,
) -> CharacterAdvisoryCandidate:
    text = f"{pressure.pressure_text.strip()} — {pressure.dramatic_rationale.strip()}".strip(" —")
    return CharacterAdvisoryCandidate(
        candidate_id=pressure.pressure_id,
        text=text,
        source_kind="overlay_pressure",
        lineage=(pressure.pressure_id,),
        basis_refs=pressure.basis_refs,
        creation_provenance=pressure.creation_provenance,
        applicability=pressure.applicability,
    )


def frame_derived_character_candidate(
    frame: GlobalPlotFrame,
    *,
    text: str,
    candidate_id: str | None = None,
) -> CharacterAdvisoryCandidate:
    """Independent Character-facing candidate with lineage to a frame (never raw frame projection)."""
    return CharacterAdvisoryCandidate(
        candidate_id=candidate_id or new_candidate_id("frame-cand"),
        text=text.strip(),
        source_kind="overlay_character_candidate",
        lineage=(frame.frame_id,),
        basis_refs=frame.basis_refs,
        creation_provenance=frame.creation_provenance,
        structural_evidence_refs=(
            StableReference(
                ref_kind="plot_cognition_frame_lineage",
                stable_ref=frame.frame_id,
            ),
        ),
    )


def global_goal_derived_character_candidate(
    goal: PlotGoal,
    *,
    text: str,
    character_id: str,
    candidate_id: str | None = None,
) -> CharacterAdvisoryCandidate:
    return CharacterAdvisoryCandidate(
        candidate_id=candidate_id or new_candidate_id("global-goal-cand"),
        text=text.strip(),
        source_kind="overlay_character_candidate",
        lineage=(goal.goal_id,),
        basis_refs=goal.basis_refs,
        creation_provenance=goal.creation_provenance,
        applicability=CognitionApplicability(
            applicability_kind="character",
            primary_character_id=character_id,
            involved_character_ids=(character_id,),
        ),
        structural_evidence_refs=(
            StableReference(
                ref_kind="plot_cognition_goal_lineage",
                stable_ref=goal.goal_id,
            ),
        ),
    )

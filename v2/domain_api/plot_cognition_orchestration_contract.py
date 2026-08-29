"""Plot Cognition runtime orchestration contracts (#63)."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from .plot_cognition_projection_contract import (
    CandidateProjectionRecord,
    CharacterAdvisoryCandidate,
    ProjectionBudget,
    ProjectionForensicHandoff,
    SemanticEvaluationResult,
    StructuralEligibilityResult,
)

PLOT_COGNITION_ORCHESTRATION_POLICY_SCHEMA = "hg_plot_cognition_orchestration_policy_v1"
PLOT_COGNITION_PENDING_WORK_SCHEMA = "hg_plot_cognition_pending_work_v1"
CHARACTER_EPISTEMIC_CONTEXT_SCHEMA = "hg_character_epistemic_context_v1"
REGENERATION_GUIDANCE_SCHEMA = "hg_regeneration_guidance_v1"
PREPARED_PROJECTION_BATCH_SCHEMA = "hg_plot_cognition_projection_batch_prepared_v1"
EPISTEMIC_PROJECTION_EVAL_SCHEMA = "hg_epistemic_projection_eval_v1"

PendingWorkKind = Literal["update", "replan", "initialization"]
ViolationClass = Literal[
    "third_party_private_knowledge",
    "withheld_basis_exposure",
    "global_cognition_leak",
    "over_specific_prospective",
    "relationship_boundary",
    "other",
]


@dataclass(frozen=True)
class StorytellerOrchestrationPolicy:
    """Hard orchestration ceilings; numeric defaults are operational, not architecture."""

    schema: str
    max_generated_candidates: int = 12
    max_semantic_context_items: int = 16
    max_semantic_context_chars: int = 12000
    max_forensic_rationale_chars: int = 4000
    max_evaluator_output_chars: int = 8000
    max_parallel_epistemic_evals: int = 4
    phase_timeout_seconds: int = 45
    max_regeneration_attempts: int = 1
    max_semantic_evaluations_per_candidate: int = 2

    def __post_init__(self) -> None:
        if self.max_regeneration_attempts != 1:
            raise ValueError("max_regeneration_attempts must be 1")
        if self.max_semantic_evaluations_per_candidate != 2:
            raise ValueError("max_semantic_evaluations_per_candidate must be 2")


DEFAULT_ORCHESTRATION_POLICY = StorytellerOrchestrationPolicy(
    schema=PLOT_COGNITION_ORCHESTRATION_POLICY_SCHEMA,
)


@dataclass(frozen=True)
class RegenerationGuidance:
    schema: str
    violation_class: ViolationClass
    safe_constraints: tuple[str, ...]
    affected_dimensions: tuple[str, ...] = ()
    do_not_introduce: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "violation_class": self.violation_class,
            "safe_constraints": list(self.safe_constraints),
            "affected_dimensions": list(self.affected_dimensions),
            "do_not_introduce": list(self.do_not_introduce),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegenerationGuidance:
        return cls(
            schema=str(data.get("schema", REGENERATION_GUIDANCE_SCHEMA)),
            violation_class=data.get("violation_class", "other"),  # type: ignore[arg-type]
            safe_constraints=tuple(str(item) for item in (data.get("safe_constraints") or [])),
            affected_dimensions=tuple(
                str(item) for item in (data.get("affected_dimensions") or [])
            ),
            do_not_introduce=tuple(str(item) for item in (data.get("do_not_introduce") or [])),
        )


@dataclass(frozen=True)
class CharacterEpistemicContextEnvelope:
    """Bounded semantic material + identity/freshness evidence for Layer B."""

    schema: str
    character_id: str
    known_by_snapshot_id: str
    authority_fingerprint: str | None
    overlay_revision: int | None
    visibility_digest: str
    hg_round_id: str
    turn_index: int
    candidate_id: str
    source_kind: str
    lineage: tuple[str, ...]
    semantic_material: tuple[str, ...]
    withheld_basis_index: tuple[dict[str, str], ...]
    identity_evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "character_id": self.character_id,
            "known_by_snapshot_id": self.known_by_snapshot_id,
            "authority_fingerprint": self.authority_fingerprint,
            "overlay_revision": self.overlay_revision,
            "visibility_digest": self.visibility_digest,
            "hg_round_id": self.hg_round_id,
            "turn_index": self.turn_index,
            "candidate_id": self.candidate_id,
            "source_kind": self.source_kind,
            "lineage": list(self.lineage),
            "semantic_material": list(self.semantic_material),
            "withheld_basis_index": [dict(item) for item in self.withheld_basis_index],
            "identity_evidence": dict(self.identity_evidence),
        }


@dataclass(frozen=True)
class PreparedProjectionCandidate:
    candidate: CharacterAdvisoryCandidate
    structural: StructuralEligibilityResult
    epistemic_context: CharacterEpistemicContextEnvelope
    evaluation_pass_id: str
    evaluator_manifest_id: str


@dataclass(frozen=True)
class PreparedProjectionBatch:
    schema: str
    batch_id: str
    character_id: str
    manifest_id: str
    known_by_snapshot_id: str
    authority_fingerprint: str | None
    overlay_revision: int | None
    budget: ProjectionBudget
    binding_digest: str
    items: tuple[PreparedProjectionCandidate, ...]
    excluded_records: tuple[CandidateProjectionRecord, ...]

    def binding_matches(
        self,
        *,
        known_by_snapshot_id: str,
        authority_fingerprint: str | None,
        overlay_revision: int | None,
        binding_digest: str,
    ) -> bool:
        return (
            self.known_by_snapshot_id == known_by_snapshot_id
            and self.authority_fingerprint == authority_fingerprint
            and self.overlay_revision == overlay_revision
            and self.binding_digest == binding_digest
        )


@dataclass(frozen=True)
class CharacterProjectionSemanticResult:
    evaluation_pass_id: str
    candidate_id: str
    semantic: SemanticEvaluationResult
    regeneration_guidance: RegenerationGuidance | None
    inference_evidence_id: str | None = None


@dataclass(frozen=True)
class RegenerationRequestDescriptor:
    batch_id: str
    candidate_id: str
    evaluation_pass_id: str
    original_candidate: CharacterAdvisoryCandidate
    regeneration_guidance: RegenerationGuidance
    forensic_rationale: str


@dataclass(frozen=True)
class FinalizedProjectionBatch:
    contributions: tuple[Any, ...]
    forensic: ProjectionForensicHandoff
    pending_regenerations: tuple[RegenerationRequestDescriptor, ...]


@dataclass
class PlotCognitionPendingWork:
    """Domain-owned scope-associated pending cognition obligation."""

    schema: str
    plot_cognition_scope_id: str
    trigger_domain_commit_id: str
    work_kind: PendingWorkKind
    recorded_at_continuity_version: int
    authority_source_fingerprint: str
    required_before_projection: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "trigger_domain_commit_id": self.trigger_domain_commit_id,
            "work_kind": self.work_kind,
            "recorded_at_continuity_version": self.recorded_at_continuity_version,
            "authority_source_fingerprint": self.authority_source_fingerprint,
            "required_before_projection": self.required_before_projection,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionPendingWork:
        return cls(
            schema=str(data.get("schema", PLOT_COGNITION_PENDING_WORK_SCHEMA)),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            trigger_domain_commit_id=str(data.get("trigger_domain_commit_id", "")),
            work_kind=data.get("work_kind", "update"),  # type: ignore[arg-type]
            recorded_at_continuity_version=int(data.get("recorded_at_continuity_version", 0)),
            authority_source_fingerprint=str(data.get("authority_source_fingerprint", "")),
            required_before_projection=bool(data.get("required_before_projection", True)),
        )


def new_batch_id() -> str:
    return f"proj-batch-{uuid.uuid4().hex[:12]}"


def new_evaluation_pass_id() -> str:
    return f"ep-eval-{uuid.uuid4().hex[:12]}"


def compute_binding_digest(
    *,
    hg_round_id: str,
    turn_index: int,
    character_id: str,
    known_by_snapshot_id: str,
    authority_fingerprint: str | None,
    overlay_revision: int | None,
) -> str:
    payload = "|".join(
        [
            hg_round_id,
            str(turn_index),
            character_id,
            known_by_snapshot_id,
            authority_fingerprint or "",
            str(overlay_revision if overlay_revision is not None else ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_visibility_digest(semantic_material: tuple[str, ...]) -> str:
    joined = "\n".join(semantic_material)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]

"""Storyteller Plot Cognition initialization contracts (#60).

Semantic adoption inference and evaluator invocation are owned by #63.
This module defines schemas, objective validation, and result envelopes only.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .plot_cognition_overlay_contract import (
    PlotGoal,
    UnresolvedNarrativePressure,
    global_plot_frame_from_dict,
    plot_goal_from_dict,
    unresolved_narrative_pressure_from_dict,
    validate_global_plot_frame,
    validate_plot_goal,
    validate_unresolved_narrative_pressure,
)

INITIALIZATION_SOURCE_SNAPSHOT_SCHEMA = "hg_plot_cognition_init_source_snapshot_v1"
INITIALIZATION_PROPOSAL_SCHEMA = "hg_plot_cognition_init_proposal_v1"
INITIALIZATION_EVALUATION_SCHEMA = "hg_plot_cognition_init_eval_v1"
INITIALIZATION_FORENSIC_HANDOFF_SCHEMA = "hg_plot_cognition_init_forensic_handoff_v1"

OpeningCompleteness = Literal["prose_present", "prose_not_expected", "prose_pending"]
InitializationEvaluationResult = Literal["accept", "revise", "reject"]
CommitPreconditionCode = Literal[
    "committed",
    "already_initialized",
    "stale_source",
    "opening_incomplete",
    "blocked_status",
    "integrity_invalid",
    "budget_exceeded",
    "persistence_failed",
    "revision_conflict",
]

AUTHORED_STORYTELLER_DIRECTION_REF_KIND = "storyteller_plot_direction"


@dataclass(frozen=True)
class InitializationSourceSnapshot:
    schema: str
    snapshot_id: str
    fingerprint: str
    plot_cognition_scope_id: str
    session_id: str
    opening_mode: str
    opening_completeness: OpeningCompleteness
    opening_entry_id: str | None
    canonical_body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "snapshot_id": self.snapshot_id,
            "fingerprint": self.fingerprint,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "session_id": self.session_id,
            "opening_mode": self.opening_mode,
            "opening_completeness": self.opening_completeness,
            "opening_entry_id": self.opening_entry_id,
            "canonical_body": self.canonical_body,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InitializationSourceSnapshot:
        return cls(
            schema=str(data.get("schema", "")),
            snapshot_id=str(data.get("snapshot_id", "")),
            fingerprint=str(data.get("fingerprint", "")),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            session_id=str(data.get("session_id", "")),
            opening_mode=str(data.get("opening_mode", "")),
            opening_completeness=str(data.get("opening_completeness", "")),  # type: ignore[arg-type]
            opening_entry_id=data.get("opening_entry_id"),
            canonical_body=dict(data.get("canonical_body") or {}),
        )


@dataclass(frozen=True)
class PlotCognitionInitializationProposal:
    schema: str
    proposal_id: str
    source_snapshot_id: str
    source_snapshot_fingerprint: str
    plot_cognition_scope_id: str
    adoption_rationale: str
    goals: tuple[dict[str, Any], ...]
    pressures: tuple[dict[str, Any], ...]
    global_frame: dict[str, Any] | None
    per_item_rationale: tuple[dict[str, Any], ...] = ()
    revision_of_proposal_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "proposal_id": self.proposal_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_snapshot_fingerprint": self.source_snapshot_fingerprint,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "adoption_rationale": self.adoption_rationale,
            "goals": list(self.goals),
            "pressures": list(self.pressures),
            "global_frame": self.global_frame,
            "per_item_rationale": list(self.per_item_rationale),
            "revision_of_proposal_id": self.revision_of_proposal_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionInitializationProposal:
        return cls(
            schema=str(data.get("schema", "")),
            proposal_id=str(data.get("proposal_id", "")),
            source_snapshot_id=str(data.get("source_snapshot_id", "")),
            source_snapshot_fingerprint=str(data.get("source_snapshot_fingerprint", "")),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            adoption_rationale=str(data.get("adoption_rationale", "")),
            goals=tuple(dict(item) for item in (data.get("goals") or []) if isinstance(item, dict)),
            pressures=tuple(
                dict(item) for item in (data.get("pressures") or []) if isinstance(item, dict)
            ),
            global_frame=(
                dict(data["global_frame"])
                if isinstance(data.get("global_frame"), dict)
                else None
            ),
            per_item_rationale=tuple(
                dict(item)
                for item in (data.get("per_item_rationale") or [])
                if isinstance(item, dict)
            ),
            revision_of_proposal_id=data.get("revision_of_proposal_id"),
        )


@dataclass(frozen=True)
class PlotCognitionInitializationEvaluation:
    schema: str
    evaluation_id: str
    proposal_id: str
    overall_result: InitializationEvaluationResult
    findings: tuple[dict[str, Any], ...]
    revision_brief: str | None = None
    accepted_item_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "evaluation_id": self.evaluation_id,
            "proposal_id": self.proposal_id,
            "overall_result": self.overall_result,
            "findings": list(self.findings),
            "revision_brief": self.revision_brief,
            "accepted_item_ids": list(self.accepted_item_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionInitializationEvaluation:
        return cls(
            schema=str(data.get("schema", "")),
            evaluation_id=str(data.get("evaluation_id", "")),
            proposal_id=str(data.get("proposal_id", "")),
            overall_result=str(data.get("overall_result", "")),  # type: ignore[arg-type]
            findings=tuple(
                dict(item) for item in (data.get("findings") or []) if isinstance(item, dict)
            ),
            revision_brief=data.get("revision_brief"),
            accepted_item_ids=tuple(
                str(item).strip()
                for item in (data.get("accepted_item_ids") or [])
                if str(item).strip()
            ),
        )


@dataclass(frozen=True)
class ObjectiveValidationResult:
    ok: bool
    violations: tuple[str, ...] = ()
    over_budget: bool = False


@dataclass(frozen=True)
class InitializationCommitResult:
    success: bool
    code: CommitPreconditionCode
    message: str
    store_revision: int | None = None
    prior_revision: int | None = None
    load_status: str | None = None
    violations: tuple[str, ...] = ()


@dataclass
class InitializationForensicHandoff:
    schema: str = INITIALIZATION_FORENSIC_HANDOFF_SCHEMA
    source_snapshot: InitializationSourceSnapshot | None = None
    proposals: list[dict[str, Any]] = field(default_factory=list)
    evaluations: list[dict[str, Any]] = field(default_factory=list)
    accepted_proposal_id: str | None = None
    materialized_store: dict[str, Any] | None = None
    commit_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_snapshot": (
                self.source_snapshot.to_dict() if self.source_snapshot is not None else None
            ),
            "proposals": list(self.proposals),
            "evaluations": list(self.evaluations),
            "accepted_proposal_id": self.accepted_proposal_id,
            "materialized_store": self.materialized_store,
            "commit_result": self.commit_result,
        }


def new_snapshot_id(prefix: str = "hg-plot-init-snapshot") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_proposal_id(prefix: str = "hg-plot-init-proposal") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_evaluation_id(prefix: str = "hg-plot-init-eval") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _non_empty_text(value: str | None) -> bool:
    return bool(str(value or "").strip())


def _creation_provenance_source(item: dict[str, Any]) -> str:
    provenance = item.get("creation_provenance") or {}
    if isinstance(provenance, dict):
        return str(provenance.get("source", "")).strip()
    return ""


def _provenance_refs(item: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    provenance = item.get("creation_provenance") or {}
    if not isinstance(provenance, dict):
        return ()
    refs = provenance.get("provenance_refs") or []
    if not isinstance(refs, list):
        return ()
    return tuple(dict(ref) for ref in refs if isinstance(ref, dict))


def _has_storyteller_direction_ref(item: dict[str, Any]) -> bool:
    for ref in _provenance_refs(item):
        if str(ref.get("ref_kind", "")).strip() == AUTHORED_STORYTELLER_DIRECTION_REF_KIND:
            return True
    return False


def validate_authored_material_provenance(item: dict[str, Any]) -> tuple[bool, tuple[str, ...]]:
    if _creation_provenance_source(item) != "authored_material":
        return True, ()
    if _has_storyteller_direction_ref(item):
        return True, ()
    return False, ("authored_material_requires_storyteller_plot_direction_ref",)


def validate_initialization_proposal_objective(
    proposal: PlotCognitionInitializationProposal,
    *,
    policy_max_active_goals: int,
    policy_max_active_pressures: int,
) -> ObjectiveValidationResult:
    violations: list[str] = []

    if proposal.schema != INITIALIZATION_PROPOSAL_SCHEMA:
        violations.append("schema_mismatch")
    if not _non_empty_text(proposal.proposal_id):
        violations.append("proposal_id_required")
    if not _non_empty_text(proposal.source_snapshot_fingerprint):
        violations.append("source_snapshot_fingerprint_required")
    if not _non_empty_text(proposal.plot_cognition_scope_id):
        violations.append("plot_cognition_scope_id_required")
    if not _non_empty_text(proposal.adoption_rationale):
        violations.append("adoption_rationale_required")

    goal_ids: set[str] = set()
    for index, goal_raw in enumerate(proposal.goals):
        goal = plot_goal_from_dict(goal_raw)
        ok, goal_violations = validate_plot_goal(goal)
        if not ok:
            violations.extend(f"goal[{index}].{item}" for item in goal_violations)
        if goal.goal_id in goal_ids:
            violations.append(f"duplicate_goal_id:{goal.goal_id}")
        goal_ids.add(goal.goal_id)
        if goal.activity_state == "retired":
            violations.append(f"goal[{index}].retired_not_allowed_in_initial_snapshot")
        prov_ok, prov_violations = validate_authored_material_provenance(goal_raw)
        if not prov_ok:
            violations.extend(f"goal[{index}].{item}" for item in prov_violations)

    pressure_ids: set[str] = set()
    for index, pressure_raw in enumerate(proposal.pressures):
        pressure = unresolved_narrative_pressure_from_dict(pressure_raw)
        ok, pressure_violations = validate_unresolved_narrative_pressure(pressure)
        if not ok:
            violations.extend(f"pressure[{index}].{item}" for item in pressure_violations)
        if pressure.pressure_id in pressure_ids:
            violations.append(f"duplicate_pressure_id:{pressure.pressure_id}")
        pressure_ids.add(pressure.pressure_id)
        if pressure.activity_state == "retired":
            violations.append(f"pressure[{index}].retired_not_allowed_in_initial_snapshot")
        prov_ok, prov_violations = validate_authored_material_provenance(pressure_raw)
        if not prov_ok:
            violations.extend(f"pressure[{index}].{item}" for item in prov_violations)

    if proposal.global_frame is not None:
        frame = global_plot_frame_from_dict(proposal.global_frame)
        ok, frame_violations = validate_global_plot_frame(frame)
        if not ok:
            violations.extend(f"global_frame.{item}" for item in frame_violations)
        prov_ok, prov_violations = validate_authored_material_provenance(proposal.global_frame)
        if not prov_ok:
            violations.extend(f"global_frame.{item}" for item in prov_violations)

    active_goals = sum(
        1
        for goal_raw in proposal.goals
        if str((goal_raw.get("activity_state") or "active")).strip() == "active"
    )
    active_pressures = sum(
        1
        for pressure_raw in proposal.pressures
        if str((pressure_raw.get("activity_state") or "active")).strip() == "active"
    )
    over_budget = False
    if active_goals > policy_max_active_goals:
        over_budget = True
        violations.append("active_goals_over_budget")
    if active_pressures > policy_max_active_pressures:
        over_budget = True
        violations.append("active_pressures_over_budget")

    return ObjectiveValidationResult(
        ok=len(violations) == 0,
        violations=tuple(violations),
        over_budget=over_budget,
    )


def validate_initialization_evaluation_contract(
    evaluation: PlotCognitionInitializationEvaluation,
) -> ObjectiveValidationResult:
    violations: list[str] = []
    if evaluation.schema != INITIALIZATION_EVALUATION_SCHEMA:
        violations.append("schema_mismatch")
    if not _non_empty_text(evaluation.evaluation_id):
        violations.append("evaluation_id_required")
    if not _non_empty_text(evaluation.proposal_id):
        violations.append("proposal_id_required")
    if evaluation.overall_result not in {"accept", "revise", "reject"}:
        violations.append("overall_result_invalid")
    if evaluation.overall_result == "revise" and not _non_empty_text(evaluation.revision_brief):
        violations.append("revision_brief_required_for_revise")
    return ObjectiveValidationResult(ok=len(violations) == 0, violations=tuple(violations))


def materialize_initial_overlay(
    proposal: PlotCognitionInitializationProposal,
    *,
    plot_cognition_scope_id: str,
) -> tuple[Any, ObjectiveValidationResult]:
    """Transform an objectively valid proposal into a #59 initial store snapshot."""
    from .plot_cognition_overlay_store import PlotCognitionOverlayStore

    validation = validate_initialization_proposal_objective(
        proposal,
        policy_max_active_goals=10_000,
        policy_max_active_pressures=10_000,
    )
    if not validation.ok:
        return None, validation

    goals: dict[str, PlotGoal] = {}
    for goal_raw in proposal.goals:
        goal = plot_goal_from_dict(goal_raw)
        goals[goal.goal_id] = goal

    pressures: dict[str, UnresolvedNarrativePressure] = {}
    for pressure_raw in proposal.pressures:
        pressure = unresolved_narrative_pressure_from_dict(pressure_raw)
        pressures[pressure.pressure_id] = pressure

    active_frame = (
        global_plot_frame_from_dict(proposal.global_frame)
        if proposal.global_frame is not None
        else None
    )

    store = PlotCognitionOverlayStore(
        store_schema="hg_plot_cognition_overlay_store_v1",
        plot_cognition_scope_id=plot_cognition_scope_id,
        store_revision=1,
        assimilated_through_domain_commit_id=None,
        goals=goals,
        pressures=pressures,
        active_frame=active_frame,
    )
    return store, ObjectiveValidationResult(ok=True)

"""Plot Cognition update and semantic replan contracts (#61).

Semantic assimilation inference and evaluator invocation are owned by #63.
This module defines schemas, objective validation, materialization, and envelopes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from .plot_cognition_initialization_contract import (
    AUTHORED_STORYTELLER_DIRECTION_REF_KIND,
    ObjectiveValidationResult,
    validate_authored_material_provenance,
)
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
from .plot_cognition_overlay_store import (
    ASSIMILATED_AUTHORITY_SCHEMA,
    PlotCognitionOverlayStore,
)

UPDATE_SOURCE_SNAPSHOT_SCHEMA = "hg_plot_cognition_update_source_snapshot_v1"
UPDATE_PROPOSAL_SCHEMA = "hg_plot_cognition_update_proposal_v1"
UPDATE_EVALUATION_SCHEMA = "hg_plot_cognition_update_eval_v1"
REPLAN_PROPOSAL_SCHEMA = "hg_plot_cognition_replan_proposal_v1"
REPLAN_EVALUATION_SCHEMA = "hg_plot_cognition_replan_eval_v1"
UPDATE_FORENSIC_HANDOFF_SCHEMA = "hg_plot_cognition_update_forensic_handoff_v1"
PRIOR_OPERATIVE_COGNITION_SCHEMA = "hg_plot_cognition_prior_operative_cognition_v1"

CatchUpMode = Literal["sequential", "endpoint_reconciliation"]
UpdateEvaluationResult = Literal["accept", "revise", "reject", "no_change"]
ReplanEvaluationResult = Literal["accept", "revise", "reject"]
ForensicOutcome = Literal[
    "semantic_update",
    "semantic_replan",
    "semantic_no_change",
    "objective_authority_unchanged",
    "endpoint_reconciliation",
]
ModelAStatus = Literal[
    "fresh",
    "authority_generation_changed_unchecked",
    "semantic_assimilation_pending",
    "lineage_incomplete",
    "shared_scope_ambiguous",
    "freshness_unprovable",
    "overlay_unavailable",
]
UpdateCommitPreconditionCode = Literal[
    "committed",
    "authority_unchanged",
    "semantic_no_change",
    "stale_source",
    "stale_revision",
    "stale_continuity_version",
    "blocked_status",
    "integrity_invalid",
    "budget_exceeded",
    "persistence_failed",
    "revision_conflict",
    "lineage_incomplete",
    "overlay_unavailable",
    "reconciliation_established",
]


@dataclass(frozen=True)
class ContributorAuthoritySnapshot:
    hg_scene_id: str
    through_domain_commit_id: str | None
    through_continuity_version: int
    authority_source_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "hg_scene_id": self.hg_scene_id,
            "through_domain_commit_id": self.through_domain_commit_id,
            "through_continuity_version": self.through_continuity_version,
            "authority_source_fingerprint": self.authority_source_fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContributorAuthoritySnapshot:
        return cls(
            hg_scene_id=str(data.get("hg_scene_id", "")),
            through_domain_commit_id=data.get("through_domain_commit_id"),
            through_continuity_version=int(data.get("through_continuity_version", 0)),
            authority_source_fingerprint=str(data.get("authority_source_fingerprint", "")),
        )


@dataclass(frozen=True)
class CognitionUpdateSourceSnapshot:
    schema: str
    snapshot_id: str
    plot_cognition_scope_id: str
    prior_store_revision: int
    prior_assimilated_authority: tuple[ContributorAuthoritySnapshot, ...]
    contributors: tuple[str, ...]
    through_domain_commit_id: str | None
    continuity_version: int
    authority_source_fingerprint: str
    committed_move_refs: tuple[str, ...]
    catch_up_mode: CatchUpMode
    evidence_gap: bool
    evidence_gap_detail: str | None
    canonical_body: dict[str, Any]
    semantic_authority_excerpts: dict[str, Any] = field(default_factory=dict)
    prior_operative_cognition: dict[str, Any] = field(default_factory=dict)
    model_facing_transport: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "snapshot_id": self.snapshot_id,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "prior_store_revision": self.prior_store_revision,
            "prior_assimilated_authority": [
                item.to_dict() for item in self.prior_assimilated_authority
            ],
            "contributors": list(self.contributors),
            "through_domain_commit_id": self.through_domain_commit_id,
            "continuity_version": self.continuity_version,
            "authority_source_fingerprint": self.authority_source_fingerprint,
            "committed_move_refs": list(self.committed_move_refs),
            "catch_up_mode": self.catch_up_mode,
            "evidence_gap": self.evidence_gap,
            "evidence_gap_detail": self.evidence_gap_detail,
            "canonical_body": self.canonical_body,
            "semantic_authority_excerpts": self.semantic_authority_excerpts,
            "prior_operative_cognition": self.prior_operative_cognition,
            "model_facing_transport": self.model_facing_transport,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CognitionUpdateSourceSnapshot:
        prior_raw = data.get("prior_assimilated_authority") or []
        prior: list[ContributorAuthoritySnapshot] = []
        if isinstance(prior_raw, list):
            for item in prior_raw:
                if isinstance(item, dict):
                    prior.append(ContributorAuthoritySnapshot.from_dict(item))
        return cls(
            schema=str(data.get("schema", "")),
            snapshot_id=str(data.get("snapshot_id", "")),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            prior_store_revision=int(data.get("prior_store_revision", 0)),
            prior_assimilated_authority=tuple(prior),
            contributors=tuple(str(item) for item in (data.get("contributors") or [])),
            through_domain_commit_id=data.get("through_domain_commit_id"),
            continuity_version=int(data.get("continuity_version", 0)),
            authority_source_fingerprint=str(data.get("authority_source_fingerprint", "")),
            committed_move_refs=tuple(
                str(item).strip()
                for item in (data.get("committed_move_refs") or [])
                if str(item).strip()
            ),
            catch_up_mode=str(data.get("catch_up_mode", "sequential")),  # type: ignore[arg-type]
            evidence_gap=bool(data.get("evidence_gap")),
            evidence_gap_detail=data.get("evidence_gap_detail"),
            canonical_body=dict(data.get("canonical_body") or {}),
            semantic_authority_excerpts=dict(data.get("semantic_authority_excerpts") or {}),
            prior_operative_cognition=dict(data.get("prior_operative_cognition") or {}),
            model_facing_transport=dict(data.get("model_facing_transport") or {}),
        )

    def contributor_authority_targets(self) -> tuple[ContributorAuthoritySnapshot, ...]:
        return tuple(
            ContributorAuthoritySnapshot(
                hg_scene_id=scene_id,
                through_domain_commit_id=self.through_domain_commit_id,
                through_continuity_version=self.continuity_version,
                authority_source_fingerprint=self.authority_source_fingerprint,
            )
            for scene_id in self.contributors
        )


@dataclass(frozen=True)
class PlotCognitionUpdateProposal:
    schema: str
    proposal_id: str
    source_snapshot_id: str
    source_snapshot_fingerprint: str
    plot_cognition_scope_id: str
    prior_store_revision: int
    assimilation_rationale: str
    goals: tuple[dict[str, Any], ...]
    pressures: tuple[dict[str, Any], ...]
    global_frame: dict[str, Any] | None
    retained_goal_ids: tuple[str, ...] = ()
    retained_pressure_ids: tuple[str, ...] = ()
    inactivated_goal_ids: tuple[str, ...] = ()
    inactivated_pressure_ids: tuple[str, ...] = ()
    replan_required: bool = False
    per_item_rationale: tuple[dict[str, Any], ...] = ()
    revision_of_proposal_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "proposal_id": self.proposal_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_snapshot_fingerprint": self.source_snapshot_fingerprint,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "prior_store_revision": self.prior_store_revision,
            "assimilation_rationale": self.assimilation_rationale,
            "goals": list(self.goals),
            "pressures": list(self.pressures),
            "global_frame": self.global_frame,
            "retained_goal_ids": list(self.retained_goal_ids),
            "retained_pressure_ids": list(self.retained_pressure_ids),
            "inactivated_goal_ids": list(self.inactivated_goal_ids),
            "inactivated_pressure_ids": list(self.inactivated_pressure_ids),
            "replan_required": self.replan_required,
            "per_item_rationale": list(self.per_item_rationale),
            "revision_of_proposal_id": self.revision_of_proposal_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionUpdateProposal:
        return cls(
            schema=str(data.get("schema", "")),
            proposal_id=str(data.get("proposal_id", "")),
            source_snapshot_id=str(data.get("source_snapshot_id", "")),
            source_snapshot_fingerprint=str(data.get("source_snapshot_fingerprint", "")),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            prior_store_revision=int(data.get("prior_store_revision", 0)),
            assimilation_rationale=str(data.get("assimilation_rationale", "")),
            goals=tuple(dict(item) for item in (data.get("goals") or []) if isinstance(item, dict)),
            pressures=tuple(
                dict(item) for item in (data.get("pressures") or []) if isinstance(item, dict)
            ),
            global_frame=(
                dict(data["global_frame"])
                if isinstance(data.get("global_frame"), dict)
                else None
            ),
            retained_goal_ids=tuple(
                str(item).strip()
                for item in (data.get("retained_goal_ids") or [])
                if str(item).strip()
            ),
            retained_pressure_ids=tuple(
                str(item).strip()
                for item in (data.get("retained_pressure_ids") or [])
                if str(item).strip()
            ),
            inactivated_goal_ids=tuple(
                str(item).strip()
                for item in (data.get("inactivated_goal_ids") or [])
                if str(item).strip()
            ),
            inactivated_pressure_ids=tuple(
                str(item).strip()
                for item in (data.get("inactivated_pressure_ids") or [])
                if str(item).strip()
            ),
            replan_required=bool(data.get("replan_required")),
            per_item_rationale=tuple(
                dict(item)
                for item in (data.get("per_item_rationale") or [])
                if isinstance(item, dict)
            ),
            revision_of_proposal_id=data.get("revision_of_proposal_id"),
        )


@dataclass(frozen=True)
class PlotCognitionUpdateEvaluation:
    schema: str
    evaluation_id: str
    proposal_id: str
    overall_result: UpdateEvaluationResult
    findings: tuple[dict[str, Any], ...]
    revision_brief: str | None = None
    accepted_item_ids: tuple[str, ...] = ()
    no_change_rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "evaluation_id": self.evaluation_id,
            "proposal_id": self.proposal_id,
            "overall_result": self.overall_result,
            "findings": list(self.findings),
            "revision_brief": self.revision_brief,
            "accepted_item_ids": list(self.accepted_item_ids),
            "no_change_rationale": self.no_change_rationale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionUpdateEvaluation:
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
            no_change_rationale=data.get("no_change_rationale"),
        )


@dataclass(frozen=True)
class PlotCognitionReplanProposal:
    schema: str
    proposal_id: str
    source_snapshot_id: str
    source_snapshot_fingerprint: str
    plot_cognition_scope_id: str
    prior_store_revision: int
    replan_rationale: str
    trigger_summary: str
    goals: tuple[dict[str, Any], ...]
    pressures: tuple[dict[str, Any], ...]
    global_frame: dict[str, Any] | None
    superseded_goal_ids: tuple[str, ...] = ()
    superseded_pressure_ids: tuple[str, ...] = ()
    retained_goal_ids: tuple[str, ...] = ()
    retained_pressure_ids: tuple[str, ...] = ()
    per_item_rationale: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "proposal_id": self.proposal_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_snapshot_fingerprint": self.source_snapshot_fingerprint,
            "plot_cognition_scope_id": self.plot_cognition_scope_id,
            "prior_store_revision": self.prior_store_revision,
            "replan_rationale": self.replan_rationale,
            "trigger_summary": self.trigger_summary,
            "goals": list(self.goals),
            "pressures": list(self.pressures),
            "global_frame": self.global_frame,
            "superseded_goal_ids": list(self.superseded_goal_ids),
            "superseded_pressure_ids": list(self.superseded_pressure_ids),
            "retained_goal_ids": list(self.retained_goal_ids),
            "retained_pressure_ids": list(self.retained_pressure_ids),
            "per_item_rationale": list(self.per_item_rationale),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionReplanProposal:
        return cls(
            schema=str(data.get("schema", "")),
            proposal_id=str(data.get("proposal_id", "")),
            source_snapshot_id=str(data.get("source_snapshot_id", "")),
            source_snapshot_fingerprint=str(data.get("source_snapshot_fingerprint", "")),
            plot_cognition_scope_id=str(data.get("plot_cognition_scope_id", "")),
            prior_store_revision=int(data.get("prior_store_revision", 0)),
            replan_rationale=str(data.get("replan_rationale", "")),
            trigger_summary=str(data.get("trigger_summary", "")),
            goals=tuple(dict(item) for item in (data.get("goals") or []) if isinstance(item, dict)),
            pressures=tuple(
                dict(item) for item in (data.get("pressures") or []) if isinstance(item, dict)
            ),
            global_frame=(
                dict(data["global_frame"])
                if isinstance(data.get("global_frame"), dict)
                else None
            ),
            superseded_goal_ids=tuple(
                str(item).strip()
                for item in (data.get("superseded_goal_ids") or [])
                if str(item).strip()
            ),
            superseded_pressure_ids=tuple(
                str(item).strip()
                for item in (data.get("superseded_pressure_ids") or [])
                if str(item).strip()
            ),
            retained_goal_ids=tuple(
                str(item).strip()
                for item in (data.get("retained_goal_ids") or [])
                if str(item).strip()
            ),
            retained_pressure_ids=tuple(
                str(item).strip()
                for item in (data.get("retained_pressure_ids") or [])
                if str(item).strip()
            ),
            per_item_rationale=tuple(
                dict(item)
                for item in (data.get("per_item_rationale") or [])
                if isinstance(item, dict)
            ),
        )


@dataclass(frozen=True)
class PlotCognitionReplanEvaluation:
    schema: str
    evaluation_id: str
    proposal_id: str
    overall_result: ReplanEvaluationResult
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
    def from_dict(cls, data: dict[str, Any]) -> PlotCognitionReplanEvaluation:
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
class UpdateCommitResult:
    success: bool
    code: UpdateCommitPreconditionCode
    message: str
    store_revision: int | None = None
    prior_revision: int | None = None
    load_status: str | None = None
    forensic_outcome: ForensicOutcome | None = None
    violations: tuple[str, ...] = ()


@dataclass(frozen=True)
class FreshnessAssessment:
    status: ModelAStatus
    message: str
    source_snapshot: CognitionUpdateSourceSnapshot | None = None


@dataclass
class UpdateForensicHandoff:
    schema: str = UPDATE_FORENSIC_HANDOFF_SCHEMA
    outcome: ForensicOutcome | None = None
    source_snapshot: CognitionUpdateSourceSnapshot | None = None
    update_proposals: list[dict[str, Any]] = field(default_factory=list)
    update_evaluations: list[dict[str, Any]] = field(default_factory=list)
    replan_proposals: list[dict[str, Any]] = field(default_factory=list)
    replan_evaluations: list[dict[str, Any]] = field(default_factory=list)
    accepted_update_proposal_id: str | None = None
    accepted_replan_proposal_id: str | None = None
    prior_authority: list[dict[str, Any]] = field(default_factory=list)
    resulting_authority: list[dict[str, Any]] = field(default_factory=list)
    materialized_store: dict[str, Any] | None = None
    commit_result: dict[str, Any] | None = None
    evidence_gap: bool = False
    evidence_gap_detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "outcome": self.outcome,
            "source_snapshot": (
                self.source_snapshot.to_dict() if self.source_snapshot is not None else None
            ),
            "update_proposals": list(self.update_proposals),
            "update_evaluations": list(self.update_evaluations),
            "replan_proposals": list(self.replan_proposals),
            "replan_evaluations": list(self.replan_evaluations),
            "accepted_update_proposal_id": self.accepted_update_proposal_id,
            "accepted_replan_proposal_id": self.accepted_replan_proposal_id,
            "prior_authority": list(self.prior_authority),
            "resulting_authority": list(self.resulting_authority),
            "materialized_store": self.materialized_store,
            "commit_result": self.commit_result,
            "evidence_gap": self.evidence_gap,
            "evidence_gap_detail": self.evidence_gap_detail,
        }


def new_snapshot_id(prefix: str = "hg-plot-update-snapshot") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_proposal_id(prefix: str = "hg-plot-update-proposal") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_evaluation_id(prefix: str = "hg-plot-update-eval") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_replan_proposal_id(prefix: str = "hg-plot-replan-proposal") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_replan_evaluation_id(prefix: str = "hg-plot-replan-eval") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _non_empty_text(value: str | None) -> bool:
    return bool(str(value or "").strip())


def is_inactive(item: dict[str, Any]) -> bool:
    return str(item.get("activity_state") or "").strip() == "inactive"


def is_superseded(item: dict[str, Any]) -> bool:
    lineage = item.get("lineage") or {}
    if isinstance(lineage, dict) and str(lineage.get("superseded_by_goal_id") or "").strip():
        return True
    return str(item.get("superseded_by_frame_id") or "").strip() != ""


def cognition_identity_preserved(
    prior: dict[str, Any],
    updated: dict[str, Any],
) -> bool:
    return str(prior.get("goal_id") or prior.get("pressure_id") or prior.get("frame_id")) == str(
        updated.get("goal_id") or updated.get("pressure_id") or updated.get("frame_id")
    )


def _validate_cognition_items(
    goals: tuple[dict[str, Any], ...],
    pressures: tuple[dict[str, Any], ...],
    global_frame: dict[str, Any] | None,
    *,
    policy_max_active_goals: int,
    policy_max_active_pressures: int,
    allow_retired: bool,
) -> ObjectiveValidationResult:
    violations: list[str] = []
    goal_ids: set[str] = set()
    for index, goal_raw in enumerate(goals):
        goal = plot_goal_from_dict(goal_raw)
        ok, goal_violations = validate_plot_goal(goal)
        if not ok:
            violations.extend(f"goal[{index}].{item}" for item in goal_violations)
        if goal.goal_id in goal_ids:
            violations.append(f"duplicate_goal_id:{goal.goal_id}")
        goal_ids.add(goal.goal_id)
        if goal.activity_state == "retired" and not allow_retired:
            violations.append(f"goal[{index}].retired_not_allowed_in_current_store")
        prov_ok, prov_violations = validate_authored_material_provenance(goal_raw)
        if not prov_ok:
            violations.extend(f"goal[{index}].{item}" for item in prov_violations)

    pressure_ids: set[str] = set()
    for index, pressure_raw in enumerate(pressures):
        pressure = unresolved_narrative_pressure_from_dict(pressure_raw)
        ok, pressure_violations = validate_unresolved_narrative_pressure(pressure)
        if not ok:
            violations.extend(f"pressure[{index}].{item}" for item in pressure_violations)
        if pressure.pressure_id in pressure_ids:
            violations.append(f"duplicate_pressure_id:{pressure.pressure_id}")
        pressure_ids.add(pressure.pressure_id)
        if pressure.activity_state == "retired" and not allow_retired:
            violations.append(f"pressure[{index}].retired_not_allowed_in_current_store")
        prov_ok, prov_violations = validate_authored_material_provenance(pressure_raw)
        if not prov_ok:
            violations.extend(f"pressure[{index}].{item}" for item in prov_violations)

    if global_frame is not None:
        frame = global_plot_frame_from_dict(global_frame)
        ok, frame_violations = validate_global_plot_frame(frame)
        if not ok:
            violations.extend(f"global_frame.{item}" for item in frame_violations)
        prov_ok, prov_violations = validate_authored_material_provenance(global_frame)
        if not prov_ok:
            violations.extend(f"global_frame.{item}" for item in prov_violations)

    active_goals = sum(
        1
        for goal_raw in goals
        if str((goal_raw.get("activity_state") or "active")).strip() == "active"
    )
    active_pressures = sum(
        1
        for pressure_raw in pressures
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


def validate_update_proposal_objective(
    proposal: PlotCognitionUpdateProposal,
    *,
    policy_max_active_goals: int,
    policy_max_active_pressures: int,
) -> ObjectiveValidationResult:
    violations: list[str] = []
    if proposal.schema != UPDATE_PROPOSAL_SCHEMA:
        violations.append("schema_mismatch")
    if not _non_empty_text(proposal.proposal_id):
        violations.append("proposal_id_required")
    if not _non_empty_text(proposal.source_snapshot_fingerprint):
        violations.append("source_snapshot_fingerprint_required")
    if not _non_empty_text(proposal.plot_cognition_scope_id):
        violations.append("plot_cognition_scope_id_required")
    if not _non_empty_text(proposal.assimilation_rationale):
        violations.append("assimilation_rationale_required")
    if proposal.prior_store_revision < 0:
        violations.append("prior_store_revision_invalid")

    item_validation = _validate_cognition_items(
        proposal.goals,
        proposal.pressures,
        proposal.global_frame,
        policy_max_active_goals=policy_max_active_goals,
        policy_max_active_pressures=policy_max_active_pressures,
        allow_retired=False,
    )
    violations.extend(item_validation.violations)
    return ObjectiveValidationResult(
        ok=len(violations) == 0,
        violations=tuple(violations),
        over_budget=item_validation.over_budget,
    )


def validate_replan_proposal_objective(
    proposal: PlotCognitionReplanProposal,
    *,
    policy_max_active_goals: int,
    policy_max_active_pressures: int,
) -> ObjectiveValidationResult:
    violations: list[str] = []
    if proposal.schema != REPLAN_PROPOSAL_SCHEMA:
        violations.append("schema_mismatch")
    if not _non_empty_text(proposal.proposal_id):
        violations.append("proposal_id_required")
    if not _non_empty_text(proposal.source_snapshot_fingerprint):
        violations.append("source_snapshot_fingerprint_required")
    if not _non_empty_text(proposal.plot_cognition_scope_id):
        violations.append("plot_cognition_scope_id_required")
    if not _non_empty_text(proposal.replan_rationale):
        violations.append("replan_rationale_required")
    if not _non_empty_text(proposal.trigger_summary):
        violations.append("trigger_summary_required")

    item_validation = _validate_cognition_items(
        proposal.goals,
        proposal.pressures,
        proposal.global_frame,
        policy_max_active_goals=policy_max_active_goals,
        policy_max_active_pressures=policy_max_active_pressures,
        allow_retired=False,
    )
    violations.extend(item_validation.violations)
    return ObjectiveValidationResult(
        ok=len(violations) == 0,
        violations=tuple(violations),
        over_budget=item_validation.over_budget,
    )


def validate_update_evaluation_contract(
    evaluation: PlotCognitionUpdateEvaluation,
) -> ObjectiveValidationResult:
    violations: list[str] = []
    if evaluation.schema != UPDATE_EVALUATION_SCHEMA:
        violations.append("schema_mismatch")
    if evaluation.overall_result not in {"accept", "revise", "reject", "no_change"}:
        violations.append("overall_result_invalid")
    if evaluation.overall_result == "revise" and not _non_empty_text(evaluation.revision_brief):
        violations.append("revision_brief_required_for_revise")
    if evaluation.overall_result == "no_change" and not _non_empty_text(
        evaluation.no_change_rationale
    ):
        violations.append("no_change_rationale_required")
    return ObjectiveValidationResult(ok=len(violations) == 0, violations=tuple(violations))


def validate_replan_evaluation_contract(
    evaluation: PlotCognitionReplanEvaluation,
) -> ObjectiveValidationResult:
    violations: list[str] = []
    if evaluation.schema != REPLAN_EVALUATION_SCHEMA:
        violations.append("schema_mismatch")
    if evaluation.overall_result not in {"accept", "revise", "reject"}:
        violations.append("overall_result_invalid")
    if evaluation.overall_result == "revise" and not _non_empty_text(evaluation.revision_brief):
        violations.append("revision_brief_required_for_revise")
    return ObjectiveValidationResult(ok=len(violations) == 0, violations=tuple(violations))


def _materialize_overlay_from_items(
    *,
    store: PlotCognitionOverlayStore,
    goals: tuple[dict[str, Any], ...],
    pressures: tuple[dict[str, Any], ...],
    global_frame: dict[str, Any] | None,
    assimilated_authority: Any,
    through_domain_commit_id: str | None,
) -> PlotCognitionOverlayStore:
    from .plot_cognition_overlay_store import sync_legacy_commit_lineage

    goal_map = {goal_id: plot_goal_from_dict(raw) for goal_id, raw in _goal_entries(goals)}
    pressure_map = {
        pressure_id: unresolved_narrative_pressure_from_dict(raw)
        for pressure_id, raw in _pressure_entries(pressures)
    }
    active_frame = (
        global_plot_frame_from_dict(global_frame) if global_frame is not None else store.active_frame
    )
    materialized = PlotCognitionOverlayStore(
        store_schema=store.store_schema,
        plot_cognition_scope_id=store.plot_cognition_scope_id,
        store_revision=store.store_revision + 1,
        assimilated_through_domain_commit_id=through_domain_commit_id,
        goals=goal_map,
        pressures=pressure_map,
        active_frame=active_frame,
        assimilated_authority=assimilated_authority,
    )
    return sync_legacy_commit_lineage(materialized)


def _goal_entries(goals: tuple[dict[str, Any], ...]) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    for raw in goals:
        goal = plot_goal_from_dict(raw)
        entries.append((goal.goal_id, raw))
    return entries


def _pressure_entries(
    pressures: tuple[dict[str, Any], ...],
) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    for raw in pressures:
        pressure = unresolved_narrative_pressure_from_dict(raw)
        entries.append((pressure.pressure_id, raw))
    return entries


def materialize_update_overlay(
    store: PlotCognitionOverlayStore,
    proposal: PlotCognitionUpdateProposal,
    evaluation: PlotCognitionUpdateEvaluation,
    *,
    assimilated_authority: Any,
    through_domain_commit_id: str | None,
) -> tuple[PlotCognitionOverlayStore | None, ObjectiveValidationResult]:
    validation = validate_update_proposal_objective(
        proposal,
        policy_max_active_goals=10_000,
        policy_max_active_pressures=10_000,
    )
    if not validation.ok:
        return None, validation
    eval_validation = validate_update_evaluation_contract(evaluation)
    if not eval_validation.ok:
        return None, eval_validation
    if evaluation.overall_result not in {"accept", "no_change"}:
        return None, ObjectiveValidationResult(
            ok=False,
            violations=("evaluation_not_accepted",),
        )

    merged_goals = _merge_update_goals(store, proposal)
    merged_pressures = _merge_update_pressures(store, proposal)
    materialized = _materialize_overlay_from_items(
        store=store,
        goals=merged_goals,
        pressures=merged_pressures,
        global_frame=proposal.global_frame if proposal.global_frame is not None else None,
        assimilated_authority=assimilated_authority,
        through_domain_commit_id=through_domain_commit_id,
    )
    return materialized, ObjectiveValidationResult(ok=True)


def materialize_replan_overlay(
    store: PlotCognitionOverlayStore,
    proposal: PlotCognitionReplanProposal,
    evaluation: PlotCognitionReplanEvaluation,
    *,
    assimilated_authority: Any,
    through_domain_commit_id: str | None,
) -> tuple[PlotCognitionOverlayStore | None, ObjectiveValidationResult]:
    validation = validate_replan_proposal_objective(
        proposal,
        policy_max_active_goals=10_000,
        policy_max_active_pressures=10_000,
    )
    if not validation.ok:
        return None, validation
    eval_validation = validate_replan_evaluation_contract(evaluation)
    if not eval_validation.ok:
        return None, eval_validation
    if evaluation.overall_result != "accept":
        return None, ObjectiveValidationResult(
            ok=False,
            violations=("evaluation_not_accepted",),
        )

    goals = _merge_replan_goals(store, proposal)
    pressures = _merge_replan_pressures(store, proposal)
    materialized = _materialize_overlay_from_items(
        store=store,
        goals=goals,
        pressures=pressures,
        global_frame=proposal.global_frame,
        assimilated_authority=assimilated_authority,
        through_domain_commit_id=through_domain_commit_id,
    )
    return materialized, ObjectiveValidationResult(ok=True)


def _merge_update_goals(
    store: PlotCognitionOverlayStore,
    proposal: PlotCognitionUpdateProposal,
) -> tuple[dict[str, Any], ...]:
    from .plot_cognition_overlay_contract import plot_goal_to_dict

    result = {goal_id: plot_goal_to_dict(goal) for goal_id, goal in store.goals.items()}
    for goal_id in proposal.inactivated_goal_ids:
        if goal_id in result:
            item = dict(result[goal_id])
            item["activity_state"] = "inactive"
            result[goal_id] = item
    for raw in proposal.goals:
        goal = plot_goal_from_dict(raw)
        result[goal.goal_id] = raw
    return tuple(result.values())


def _merge_update_pressures(
    store: PlotCognitionOverlayStore,
    proposal: PlotCognitionUpdateProposal,
) -> tuple[dict[str, Any], ...]:
    from .plot_cognition_overlay_contract import unresolved_narrative_pressure_to_dict

    result = {
        pressure_id: unresolved_narrative_pressure_to_dict(pressure)
        for pressure_id, pressure in store.pressures.items()
    }
    for pressure_id in proposal.inactivated_pressure_ids:
        if pressure_id in result:
            item = dict(result[pressure_id])
            item["activity_state"] = "inactive"
            result[pressure_id] = item
    for raw in proposal.pressures:
        pressure = unresolved_narrative_pressure_from_dict(raw)
        result[pressure.pressure_id] = raw
    return tuple(result.values())


def _merge_replan_goals(
    store: PlotCognitionOverlayStore,
    proposal: PlotCognitionReplanProposal,
) -> tuple[dict[str, Any], ...]:
    from .plot_cognition_overlay_contract import plot_goal_to_dict

    result = {goal_id: plot_goal_to_dict(goal) for goal_id, goal in store.goals.items()}
    for goal_id in proposal.superseded_goal_ids:
        if goal_id in result:
            item = dict(result[goal_id])
            item["activity_state"] = "inactive"
            result[goal_id] = item
    for raw in proposal.goals:
        goal = plot_goal_from_dict(raw)
        result[goal.goal_id] = raw
    return tuple(result.values())


def _merge_replan_pressures(
    store: PlotCognitionOverlayStore,
    proposal: PlotCognitionReplanProposal,
) -> tuple[dict[str, Any], ...]:
    from .plot_cognition_overlay_contract import unresolved_narrative_pressure_to_dict

    result = {
        pressure_id: unresolved_narrative_pressure_to_dict(pressure)
        for pressure_id, pressure in store.pressures.items()
    }
    for pressure_id in proposal.superseded_pressure_ids:
        if pressure_id in result:
            item = dict(result[pressure_id])
            item["activity_state"] = "inactive"
            result[pressure_id] = item
    for raw in proposal.pressures:
        pressure = unresolved_narrative_pressure_from_dict(raw)
        result[pressure.pressure_id] = raw
    return tuple(result.values())


def validate_authority_vector_consistency(
    store: PlotCognitionOverlayStore,
    *,
    sole_contributor_hg_scene_id: str | None = None,
) -> ObjectiveValidationResult:
    authority = store.assimilated_authority
    if authority is None:
        return ObjectiveValidationResult(ok=True)
    if authority.schema != ASSIMILATED_AUTHORITY_SCHEMA:
        return ObjectiveValidationResult(ok=False, violations=("assimilated_authority_schema_mismatch",))
    violations: list[str] = []
    if len(authority.sessions) == 1 and sole_contributor_hg_scene_id:
        session = authority.sessions[0]
        scalar = str(store.assimilated_through_domain_commit_id or "").strip() or None
        vector = str(session.through_domain_commit_id or "").strip() or None
        if scalar != vector:
            violations.append("legacy_scalar_vector_commit_mismatch")
    return ObjectiveValidationResult(ok=len(violations) == 0, violations=tuple(violations))

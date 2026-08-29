"""Storyteller Plot Cognition Overlay semantic contracts (#58 Phase 1).

Persistent advisory plot cognition types distinct from round-local Model A
(``storyteller_contract.StorytellerAdvisoryPackage``). Persistence, update,
projection, and forensic evidence planes are out of scope for this module.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .librarian_contract import StableReference

PLOT_GOAL_SCHEMA = "hg_plot_goal_v1"
UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA = "hg_unresolved_narrative_pressure_v1"
GLOBAL_PLOT_FRAME_SCHEMA = "hg_global_plot_frame_v1"

PlanningHorizon = Literal["LONG", "MEDIUM", "SHORT"]
ApplicabilityKind = Literal["character", "relational", "global"]
CognitionActivityState = Literal["active", "inactive", "retired"]
FrameActivityState = Literal["active", "inactive"]
CreationProvenanceSource = Literal[
    "authored_material",
    "storyteller",
    "character_committed",
    "player_committed",
]

_PLANNING_HORIZONS = frozenset({"LONG", "MEDIUM", "SHORT"})
_APPLICABILITY_KINDS = frozenset({"character", "relational", "global"})
_COGNITION_ACTIVITY_STATES = frozenset({"active", "inactive", "retired"})
_FRAME_ACTIVITY_STATES = frozenset({"active", "inactive"})
_CREATION_PROVENANCE_SOURCES = frozenset(
    {
        "authored_material",
        "storyteller",
        "character_committed",
        "player_committed",
    }
)


@dataclass(frozen=True)
class CognitionApplicability:
    applicability_kind: ApplicabilityKind
    primary_character_id: str | None
    involved_character_ids: tuple[str, ...]


@dataclass(frozen=True)
class CreationProvenance:
    source: CreationProvenanceSource
    provenance_note: str | None = None
    provenance_refs: tuple[StableReference, ...] = ()


@dataclass(frozen=True)
class GoalLineage:
    parent_goal_id: str | None = None
    superseded_by_goal_id: str | None = None


@dataclass(frozen=True)
class PlotGoal:
    schema: str
    goal_id: str
    intended_direction: str
    basis_note: str | None
    basis_refs: tuple[StableReference, ...]
    applicability: CognitionApplicability
    planning_horizon: PlanningHorizon
    creation_provenance: CreationProvenance
    lineage: GoalLineage
    activity_state: CognitionActivityState
    momentum_note: str | None = None
    feasibility_note: str | None = None


@dataclass(frozen=True)
class UnresolvedNarrativePressure:
    schema: str
    pressure_id: str
    pressure_text: str
    dramatic_rationale: str
    basis_note: str | None
    basis_refs: tuple[StableReference, ...]
    continuity_issue_refs: tuple[str, ...]
    applicability: CognitionApplicability
    creation_provenance: CreationProvenance
    activity_state: CognitionActivityState
    related_goal_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GlobalPlotFrame:
    schema: str
    frame_id: str
    direction_sense: str
    pacing_note: str | None
    cross_character_note: str | None
    opportunity_note: str | None
    basis_refs: tuple[StableReference, ...]
    activity_state: FrameActivityState
    superseded_by_frame_id: str | None
    creation_provenance: CreationProvenance


def new_goal_id(prefix: str = "hg-plot-goal") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_pressure_id(prefix: str = "hg-plot-pressure") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def new_frame_id(prefix: str = "hg-plot-frame") -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _stable_ref_from_dict(data: dict[str, Any]) -> StableReference:
    return StableReference(
        ref_kind=str(data.get("ref_kind", "")),
        stable_ref=str(data.get("stable_ref", "")),
        display_hint=data.get("display_hint"),
    )


def _parse_stable_refs(raw: Any) -> tuple[StableReference, ...]:
    if not isinstance(raw, list):
        return ()
    refs: list[StableReference] = []
    for item in raw:
        if isinstance(item, dict) and str(item.get("stable_ref", "")).strip():
            refs.append(_stable_ref_from_dict(item))
    return tuple(refs)


def _parse_character_ids(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        str(item).strip()
        for item in raw
        if str(item).strip()
    )


def _non_empty_text(value: str | None) -> bool:
    return bool(str(value or "").strip())


def validate_applicability(
    applicability: CognitionApplicability,
) -> tuple[bool, tuple[str, ...]]:
    violations: list[str] = []
    kind = applicability.applicability_kind
    primary = (applicability.primary_character_id or "").strip() or None
    involved = tuple(
        character_id.strip()
        for character_id in applicability.involved_character_ids
        if character_id.strip()
    )

    if kind not in _APPLICABILITY_KINDS:
        violations.append("applicability_kind_invalid")

    if kind == "character":
        if len(involved) != 1:
            violations.append("character_applicability_requires_one_involved_character")
        if not primary:
            violations.append("character_applicability_requires_primary_character_id")
        elif len(involved) == 1 and primary != involved[0]:
            violations.append("character_applicability_primary_must_match_involved_character")

    elif kind == "relational":
        if len(involved) < 2:
            violations.append("relational_applicability_requires_two_or_more_characters")
        if not primary:
            violations.append("relational_applicability_requires_primary_character_id")
        elif primary not in involved:
            violations.append("relational_applicability_primary_must_be_involved")

    elif kind == "global":
        if involved:
            violations.append("global_applicability_requires_empty_involved_character_ids")
        if primary is not None:
            violations.append("global_applicability_requires_null_primary_character_id")

    return (len(violations) == 0, tuple(violations))


def validate_creation_provenance(
    provenance: CreationProvenance,
) -> tuple[bool, tuple[str, ...]]:
    violations: list[str] = []
    if provenance.source not in _CREATION_PROVENANCE_SOURCES:
        violations.append("creation_provenance_source_invalid")
    return (len(violations) == 0, tuple(violations))


def validate_plot_goal(goal: PlotGoal) -> tuple[bool, tuple[str, ...]]:
    violations: list[str] = []
    if goal.schema != PLOT_GOAL_SCHEMA:
        violations.append("schema_mismatch")
    if not _non_empty_text(goal.goal_id):
        violations.append("goal_id_required")
    if not _non_empty_text(goal.intended_direction):
        violations.append("intended_direction_required")
    if goal.planning_horizon not in _PLANNING_HORIZONS:
        violations.append("planning_horizon_invalid")
    if goal.activity_state not in _COGNITION_ACTIVITY_STATES:
        violations.append("activity_state_invalid")
    violations.extend(validate_applicability(goal.applicability)[1])
    violations.extend(validate_creation_provenance(goal.creation_provenance)[1])
    return (len(violations) == 0, tuple(violations))


def validate_unresolved_narrative_pressure(
    pressure: UnresolvedNarrativePressure,
) -> tuple[bool, tuple[str, ...]]:
    violations: list[str] = []
    if pressure.schema != UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA:
        violations.append("schema_mismatch")
    if not _non_empty_text(pressure.pressure_id):
        violations.append("pressure_id_required")
    if not _non_empty_text(pressure.pressure_text):
        violations.append("pressure_text_required")
    if not _non_empty_text(pressure.dramatic_rationale):
        violations.append("dramatic_rationale_required")
    if pressure.activity_state not in _COGNITION_ACTIVITY_STATES:
        violations.append("activity_state_invalid")
    violations.extend(validate_applicability(pressure.applicability)[1])
    violations.extend(validate_creation_provenance(pressure.creation_provenance)[1])
    return (len(violations) == 0, tuple(violations))


def validate_global_plot_frame(frame: GlobalPlotFrame) -> tuple[bool, tuple[str, ...]]:
    violations: list[str] = []
    if frame.schema != GLOBAL_PLOT_FRAME_SCHEMA:
        violations.append("schema_mismatch")
    if not _non_empty_text(frame.frame_id):
        violations.append("frame_id_required")
    if not _non_empty_text(frame.direction_sense):
        violations.append("direction_sense_required")
    if frame.activity_state not in _FRAME_ACTIVITY_STATES:
        violations.append("activity_state_invalid")
    violations.extend(validate_creation_provenance(frame.creation_provenance)[1])
    return (len(violations) == 0, tuple(violations))


def applicability_to_dict(applicability: CognitionApplicability) -> dict[str, Any]:
    return {
        "applicability_kind": applicability.applicability_kind,
        "primary_character_id": applicability.primary_character_id,
        "involved_character_ids": list(applicability.involved_character_ids),
    }


def applicability_from_dict(data: dict[str, Any]) -> CognitionApplicability:
    return CognitionApplicability(
        applicability_kind=str(data.get("applicability_kind", "")),  # type: ignore[arg-type]
        primary_character_id=data.get("primary_character_id"),
        involved_character_ids=_parse_character_ids(data.get("involved_character_ids")),
    )


def creation_provenance_to_dict(provenance: CreationProvenance) -> dict[str, Any]:
    return {
        "source": provenance.source,
        "provenance_note": provenance.provenance_note,
        "provenance_refs": [asdict(ref) for ref in provenance.provenance_refs],
    }


def creation_provenance_from_dict(data: dict[str, Any]) -> CreationProvenance:
    return CreationProvenance(
        source=str(data.get("source", "")),  # type: ignore[arg-type]
        provenance_note=data.get("provenance_note"),
        provenance_refs=_parse_stable_refs(data.get("provenance_refs")),
    )


def goal_lineage_to_dict(lineage: GoalLineage) -> dict[str, Any]:
    return asdict(lineage)


def goal_lineage_from_dict(data: dict[str, Any]) -> GoalLineage:
    return GoalLineage(
        parent_goal_id=data.get("parent_goal_id"),
        superseded_by_goal_id=data.get("superseded_by_goal_id"),
    )


def plot_goal_to_dict(goal: PlotGoal) -> dict[str, Any]:
    return {
        "schema": goal.schema,
        "goal_id": goal.goal_id,
        "intended_direction": goal.intended_direction,
        "basis_note": goal.basis_note,
        "basis_refs": [asdict(ref) for ref in goal.basis_refs],
        "applicability": applicability_to_dict(goal.applicability),
        "planning_horizon": goal.planning_horizon,
        "creation_provenance": creation_provenance_to_dict(goal.creation_provenance),
        "lineage": goal_lineage_to_dict(goal.lineage),
        "activity_state": goal.activity_state,
        "momentum_note": goal.momentum_note,
        "feasibility_note": goal.feasibility_note,
    }


def plot_goal_from_dict(data: dict[str, Any]) -> PlotGoal:
    return PlotGoal(
        schema=str(data.get("schema", "")),
        goal_id=str(data.get("goal_id", "")),
        intended_direction=str(data.get("intended_direction", "")),
        basis_note=data.get("basis_note"),
        basis_refs=_parse_stable_refs(data.get("basis_refs")),
        applicability=applicability_from_dict(dict(data.get("applicability") or {})),
        planning_horizon=str(data.get("planning_horizon", "")),  # type: ignore[arg-type]
        creation_provenance=creation_provenance_from_dict(
            dict(data.get("creation_provenance") or {})
        ),
        lineage=goal_lineage_from_dict(dict(data.get("lineage") or {})),
        activity_state=str(data.get("activity_state", "")),  # type: ignore[arg-type]
        momentum_note=data.get("momentum_note"),
        feasibility_note=data.get("feasibility_note"),
    )


def unresolved_narrative_pressure_to_dict(
    pressure: UnresolvedNarrativePressure,
) -> dict[str, Any]:
    return {
        "schema": pressure.schema,
        "pressure_id": pressure.pressure_id,
        "pressure_text": pressure.pressure_text,
        "dramatic_rationale": pressure.dramatic_rationale,
        "basis_note": pressure.basis_note,
        "basis_refs": [asdict(ref) for ref in pressure.basis_refs],
        "continuity_issue_refs": list(pressure.continuity_issue_refs),
        "applicability": applicability_to_dict(pressure.applicability),
        "creation_provenance": creation_provenance_to_dict(pressure.creation_provenance),
        "activity_state": pressure.activity_state,
        "related_goal_ids": list(pressure.related_goal_ids),
    }


def unresolved_narrative_pressure_from_dict(
    data: dict[str, Any],
) -> UnresolvedNarrativePressure:
    return UnresolvedNarrativePressure(
        schema=str(data.get("schema", "")),
        pressure_id=str(data.get("pressure_id", "")),
        pressure_text=str(data.get("pressure_text", "")),
        dramatic_rationale=str(data.get("dramatic_rationale", "")),
        basis_note=data.get("basis_note"),
        basis_refs=_parse_stable_refs(data.get("basis_refs")),
        continuity_issue_refs=tuple(
            str(item).strip()
            for item in (data.get("continuity_issue_refs") or [])
            if str(item).strip()
        ),
        applicability=applicability_from_dict(dict(data.get("applicability") or {})),
        creation_provenance=creation_provenance_from_dict(
            dict(data.get("creation_provenance") or {})
        ),
        activity_state=str(data.get("activity_state", "")),  # type: ignore[arg-type]
        related_goal_ids=tuple(
            str(item).strip()
            for item in (data.get("related_goal_ids") or [])
            if str(item).strip()
        ),
    )


def global_plot_frame_to_dict(frame: GlobalPlotFrame) -> dict[str, Any]:
    return {
        "schema": frame.schema,
        "frame_id": frame.frame_id,
        "direction_sense": frame.direction_sense,
        "pacing_note": frame.pacing_note,
        "cross_character_note": frame.cross_character_note,
        "opportunity_note": frame.opportunity_note,
        "basis_refs": [asdict(ref) for ref in frame.basis_refs],
        "activity_state": frame.activity_state,
        "superseded_by_frame_id": frame.superseded_by_frame_id,
        "creation_provenance": creation_provenance_to_dict(frame.creation_provenance),
    }


def global_plot_frame_from_dict(data: dict[str, Any]) -> GlobalPlotFrame:
    return GlobalPlotFrame(
        schema=str(data.get("schema", "")),
        frame_id=str(data.get("frame_id", "")),
        direction_sense=str(data.get("direction_sense", "")),
        pacing_note=data.get("pacing_note"),
        cross_character_note=data.get("cross_character_note"),
        opportunity_note=data.get("opportunity_note"),
        basis_refs=_parse_stable_refs(data.get("basis_refs")),
        activity_state=str(data.get("activity_state", "")),  # type: ignore[arg-type]
        superseded_by_frame_id=data.get("superseded_by_frame_id"),
        creation_provenance=creation_provenance_from_dict(
            dict(data.get("creation_provenance") or {})
        ),
    )


def plot_goal_json_round_trip(goal: PlotGoal) -> PlotGoal:
    payload = json.loads(json.dumps(plot_goal_to_dict(goal)))
    return plot_goal_from_dict(payload)

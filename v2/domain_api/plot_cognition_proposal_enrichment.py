"""Deterministic Storyteller proposal enrichment before objective validation (#68 Part C)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .plot_cognition_initialization_contract import PlotCognitionInitializationProposal
from .plot_cognition_overlay_contract import (
    GLOBAL_PLOT_FRAME_SCHEMA,
    PLOT_GOAL_SCHEMA,
    UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
)
from .plot_cognition_update_contract import (
    PlotCognitionReplanProposal,
    PlotCognitionUpdateProposal,
)


def _is_absent_text(value: Any) -> bool:
    return not str(value or "").strip()


def _provenance_source_absent(item: dict[str, Any]) -> bool:
    provenance = item.get("creation_provenance")
    if not isinstance(provenance, dict):
        return True
    return _is_absent_text(provenance.get("source"))


def _activity_state_absent(item: dict[str, Any]) -> bool:
    return _is_absent_text(item.get("activity_state"))


def enrich_storyteller_proposed_goal(raw: dict[str, Any]) -> dict[str, Any]:
    item = dict(raw)
    if _is_absent_text(item.get("schema")):
        item["schema"] = PLOT_GOAL_SCHEMA
    if _provenance_source_absent(item):
        item["creation_provenance"] = {"source": "storyteller"}
    if _activity_state_absent(item):
        item["activity_state"] = "active"
    return item


def enrich_storyteller_proposed_pressure(raw: dict[str, Any]) -> dict[str, Any]:
    item = dict(raw)
    if _is_absent_text(item.get("schema")):
        item["schema"] = UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA
    if _provenance_source_absent(item):
        item["creation_provenance"] = {"source": "storyteller"}
    if _activity_state_absent(item):
        item["activity_state"] = "active"
    return item


def enrich_storyteller_proposed_global_frame(raw: dict[str, Any]) -> dict[str, Any]:
    item = dict(raw)
    if _is_absent_text(item.get("schema")):
        item["schema"] = GLOBAL_PLOT_FRAME_SCHEMA
    if _provenance_source_absent(item):
        item["creation_provenance"] = {"source": "storyteller"}
    if _activity_state_absent(item):
        item["activity_state"] = "active"
    return item


def enrich_storyteller_cognition_items(
    goals: tuple[dict[str, Any], ...],
    pressures: tuple[dict[str, Any], ...],
    global_frame: dict[str, Any] | None,
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], dict[str, Any] | None]:
    enriched_goals = tuple(enrich_storyteller_proposed_goal(item) for item in goals)
    enriched_pressures = tuple(enrich_storyteller_proposed_pressure(item) for item in pressures)
    enriched_frame = (
        enrich_storyteller_proposed_global_frame(global_frame)
        if isinstance(global_frame, dict)
        else None
    )
    return enriched_goals, enriched_pressures, enriched_frame


def enrich_initialization_proposal(
    proposal: PlotCognitionInitializationProposal,
) -> PlotCognitionInitializationProposal:
    goals, pressures, global_frame = enrich_storyteller_cognition_items(
        proposal.goals,
        proposal.pressures,
        proposal.global_frame,
    )
    return replace(
        proposal,
        goals=goals,
        pressures=pressures,
        global_frame=global_frame,
    )


def enrich_update_proposal(
    proposal: PlotCognitionUpdateProposal,
) -> PlotCognitionUpdateProposal:
    goals, pressures, global_frame = enrich_storyteller_cognition_items(
        proposal.goals,
        proposal.pressures,
        proposal.global_frame,
    )
    return replace(
        proposal,
        goals=goals,
        pressures=pressures,
        global_frame=global_frame,
    )


def enrich_replan_proposal(
    proposal: PlotCognitionReplanProposal,
) -> PlotCognitionReplanProposal:
    goals, pressures, global_frame = enrich_storyteller_cognition_items(
        proposal.goals,
        proposal.pressures,
        proposal.global_frame,
    )
    return replace(
        proposal,
        goals=goals,
        pressures=pressures,
        global_frame=global_frame,
    )

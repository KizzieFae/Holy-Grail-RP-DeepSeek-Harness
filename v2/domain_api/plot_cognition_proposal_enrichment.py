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


def _dedupe_character_ids(character_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for character_id in character_ids:
        if character_id not in seen:
            seen.add(character_id)
            deduped.append(character_id)
    return deduped


def canonicalize_applicability_dict(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Representation-preserving applicability canonicalization (#162).

    Enforces declared applicability_kind scope rules without reclassifying kinds.
    """
    if not isinstance(raw, dict):
        return {}
    kind = str(raw.get("applicability_kind") or "").strip()
    primary = str(raw.get("primary_character_id") or "").strip() or None
    involved = _dedupe_character_ids(
        [
            character_id.strip()
            for character_id in (raw.get("involved_character_ids") or [])
            if str(character_id).strip()
        ]
    )

    if kind == "character" and primary:
        return {
            "applicability_kind": "character",
            "primary_character_id": primary,
            "involved_character_ids": [primary],
        }

    if kind == "relational" and primary:
        if primary not in involved:
            involved = [primary, *involved]
        return {
            "applicability_kind": "relational",
            "primary_character_id": primary,
            "involved_character_ids": involved,
        }

    if kind == "global":
        return {
            "applicability_kind": "global",
            "primary_character_id": None,
            "involved_character_ids": [],
        }

    return {
        "applicability_kind": kind,
        "primary_character_id": primary,
        "involved_character_ids": involved,
    }


def _canonicalize_item_applicability(item: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(item)
    applicability = item.get("applicability")
    if isinstance(applicability, dict):
        enriched["applicability"] = canonicalize_applicability_dict(applicability)
    return enriched


def enrich_storyteller_proposed_goal(raw: dict[str, Any]) -> dict[str, Any]:
    item = _canonicalize_item_applicability(raw)
    if _is_absent_text(item.get("schema")):
        item["schema"] = PLOT_GOAL_SCHEMA
    if _provenance_source_absent(item):
        item["creation_provenance"] = {"source": "storyteller"}
    if _activity_state_absent(item):
        item["activity_state"] = "active"
    return item


def enrich_storyteller_proposed_pressure(raw: dict[str, Any]) -> dict[str, Any]:
    item = _canonicalize_item_applicability(raw)
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

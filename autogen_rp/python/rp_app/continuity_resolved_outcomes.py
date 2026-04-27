"""Resolved outcomes from structured move fields (registry-backed facets)."""

from __future__ import annotations

from typing import Any

from resolved_outcome_engine import apply_registered_resolved_outcomes
from resolved_outcome_registry import (
    ACCESS_LOCATION_ENTRY_ALLOWED_RULE_ID,
    ACCESS_LOCATION_ENTRY_ASPECT_ID,
    ACCESS_LOCATION_ENTRY_DENIED_RULE_ID,
    COMMUNICATION_HOUSING_CALL_ASPECT_ID,
    FALLBACK_SLEEPING_SURFACE_IDS,
    MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID,
    LODGING_SLEEP_SURFACE_ASPECT_ID,
    HOUSING_CALL_COMPLETED_RULE_ID,
    HOUSING_CALL_FAILED_RULE_ID,
    SUPPRESSANT_FORMULATION_COMPATIBLE_RULE_ID,
    SUPPRESSANT_FORMULATION_INCOMPATIBLE_RULE_ID,
    SLEEPING_SURFACE_CONSEQUENCE_RULE_ID,
    SLEEPING_SURFACE_ISSUE_PREFIX,
    SLEEPING_SURFACE_ISSUE_RULE_ID,
    TRANSACTION_SCENE_COMMITMENT_ASPECT_ID,
    get_valid_sleeping_surface_ids,
    get_valid_location_entry_ids,
    parse_housing_call_outcome_candidates,
    parse_lodging_sleep_surface_candidates,
    parse_location_entry_outcome_candidates,
    parse_suppressant_formulation_outcome_candidates,
    parse_scene_commitment_outcome_candidates,
)

__all__ = [
    "FALLBACK_SLEEPING_SURFACE_IDS",
    "ACCESS_LOCATION_ENTRY_ALLOWED_RULE_ID",
    "ACCESS_LOCATION_ENTRY_DENIED_RULE_ID",
    "SLEEPING_SURFACE_ISSUE_RULE_ID",
    "SLEEPING_SURFACE_CONSEQUENCE_RULE_ID",
    "SLEEPING_SURFACE_ISSUE_PREFIX",
    "LODGING_SLEEP_SURFACE_ASPECT_ID",
    "COMMUNICATION_HOUSING_CALL_ASPECT_ID",
    "MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID",
    "ACCESS_LOCATION_ENTRY_ASPECT_ID",
    "TRANSACTION_SCENE_COMMITMENT_ASPECT_ID",
    "HOUSING_CALL_COMPLETED_RULE_ID",
    "HOUSING_CALL_FAILED_RULE_ID",
    "SUPPRESSANT_FORMULATION_COMPATIBLE_RULE_ID",
    "SUPPRESSANT_FORMULATION_INCOMPATIBLE_RULE_ID",
    "get_valid_sleeping_surface_ids",
    "get_valid_location_entry_ids",
    "parse_scene_commitment_outcome_candidates",
    "extract_sleeping_surface_candidates",
    "extract_housing_call_outcome_candidates",
    "extract_suppressant_formulation_outcome_candidates",
    "extract_location_entry_outcome_candidates",
    "build_sleeping_surface_state_change",
    "build_housing_call_state_change",
    "build_suppressant_formulation_state_change",
    "build_location_entry_state_change",
    "apply_registered_resolved_outcome_updates",
    "apply_sleeping_surface_outcome_updates",
    "apply_housing_call_outcome_updates",
    "apply_suppressant_formulation_outcome_updates",
    "apply_location_entry_outcome_updates",
    "apply_scene_commitment_outcome_updates",
]


def extract_sleeping_surface_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[dict[str, str]], str]:
    """Backward-compatible dict list for consequence classifier; ingest is registry-owned."""
    normalized, reason = parse_lodging_sleep_surface_candidates(move, scene_state)
    if not normalized:
        return [], reason
    return (
        [
            {
                "assignee_id": c.subject_id,
                "surface_id": str(c.value.get("surface_id", "") or ""),
            }
            for c in normalized
        ],
        "",
    )


def build_sleeping_surface_state_change(move: dict[str, Any], scene_state: Any) -> str:
    normalized, _ = parse_lodging_sleep_surface_candidates(move, scene_state)
    if len(normalized) != 1:
        return ""
    c = normalized[0]
    return (
        f"{c.subject_id} sleeping assignment set to "
        f"{c.value.get('surface_id', '')}."
    )


def extract_housing_call_outcome_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[dict[str, str]], str]:
    normalized, reason = parse_housing_call_outcome_candidates(move, scene_state)
    if not normalized:
        return [], reason
    return ([{"status": str(c.value.get("status", "") or "")} for c in normalized], "")


def build_housing_call_state_change(move: dict[str, Any], scene_state: Any) -> str:
    normalized, _ = parse_housing_call_outcome_candidates(move, scene_state)
    if len(normalized) != 1:
        return ""
    status = str(normalized[0].value.get("status", "") or "")
    if not status:
        return ""
    return f"Housing call status set to {status}."


def extract_suppressant_formulation_outcome_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[dict[str, str]], str]:
    normalized, reason = parse_suppressant_formulation_outcome_candidates(
        move, scene_state
    )
    if not normalized:
        return [], reason
    return (
        [
            {
                "subject_id": c.subject_id,
                "status": str(c.value.get("status", "") or ""),
            }
            for c in normalized
        ],
        "",
    )


def build_suppressant_formulation_state_change(
    move: dict[str, Any], scene_state: Any
) -> str:
    normalized, _ = parse_suppressant_formulation_outcome_candidates(move, scene_state)
    if len(normalized) != 1:
        return ""
    c = normalized[0]
    status = str(c.value.get("status", "") or "")
    if not c.subject_id or not status:
        return ""
    return f"{c.subject_id} suppressant formulation set to {status}."


def extract_location_entry_outcome_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[dict[str, str]], str]:
    normalized, reason = parse_location_entry_outcome_candidates(move, scene_state)
    if not normalized:
        return [], reason
    return (
        [
            {
                "subject_id": c.subject_id,
                "location_id": str(c.value.get("location_id", "") or ""),
                "status": str(c.value.get("status", "") or ""),
            }
            for c in normalized
        ],
        "",
    )


def build_location_entry_state_change(move: dict[str, Any], scene_state: Any) -> str:
    normalized, _ = parse_location_entry_outcome_candidates(move, scene_state)
    if len(normalized) != 1:
        return ""
    c = normalized[0]
    location_id = str(c.value.get("location_id", "") or "")
    status = str(c.value.get("status", "") or "")
    if not c.subject_id or not location_id or not status:
        return ""
    return f"{c.subject_id} entry to {location_id} set to {status}."


def apply_registered_resolved_outcome_updates(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, dict[str, Any]]:
    return apply_registered_resolved_outcomes(
        manager=manager,
        move=move,
        event=event,
        turn_consequences=turn_consequences,
        turn_index=turn_index,
    )


def apply_sleeping_surface_outcome_updates(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, Any]:
    return apply_registered_resolved_outcome_updates(
        manager=manager,
        move=move,
        event=event,
        turn_consequences=turn_consequences,
        turn_index=turn_index,
    ).get("sleeping_surface", {"reason": "no_candidate", "decision": "none"})


def apply_housing_call_outcome_updates(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, Any]:
    return apply_registered_resolved_outcome_updates(
        manager=manager,
        move=move,
        event=event,
        turn_consequences=turn_consequences,
        turn_index=turn_index,
    ).get("housing_call", {"reason": "no_candidate", "decision": "none"})


def apply_suppressant_formulation_outcome_updates(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, Any]:
    return apply_registered_resolved_outcome_updates(
        manager=manager,
        move=move,
        event=event,
        turn_consequences=turn_consequences,
        turn_index=turn_index,
    ).get("suppressant_formulation", {"reason": "no_candidate", "decision": "none"})


def apply_location_entry_outcome_updates(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, Any]:
    return apply_registered_resolved_outcome_updates(
        manager=manager,
        move=move,
        event=event,
        turn_consequences=turn_consequences,
        turn_index=turn_index,
    ).get("location_entry", {"reason": "no_candidate", "decision": "none"})


def apply_scene_commitment_outcome_updates(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, Any]:
    return apply_registered_resolved_outcome_updates(
        manager=manager,
        move=move,
        event=event,
        turn_consequences=turn_consequences,
        turn_index=turn_index,
    ).get("scene_commitment", {"reason": "no_candidate", "decision": "none"})

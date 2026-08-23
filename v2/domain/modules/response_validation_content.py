"""Character response validation for production runtime and offline scenario hooks.

Production Host path (#18): ``validate_bot_response_for_runtime`` enforces objective
machine contracts and move-shape invariants only (R02a placeholders, R03).

Semantic/textual quality heuristics (R02b, R11–R15) are deferred to sibling #19.
Investigation-recall scenario contracts use ``validate_bot_response_for_scenario``.
"""

from __future__ import annotations

from typing import Any

from progression_simulation_scenarios import load_scenario
from response_validation_investigation_recall import (
    validate_investigation_recall_contract,
)
from continuity_mutation_pipeline import (
    validate_excursion_lifecycle_move_shape,
    validate_spatial_transition_move_shape,
)
from continuity_reintegration import validate_reintegration_move_shape
from response_validation_registry_slots import validate_registry_scene_state_updates

USER_PLACEHOLDER_PREFIX = "[USER_PLACEHOLDER]"


def contains_unresolved_user_placeholders(content: str) -> tuple[bool, str]:
    """R02a — literal unresolved template placeholders (objective machine contract)."""
    content_lower = content.lower()
    if "{{user}}" in content_lower:
        return True, "Unresolved user placeholder"
    if "{{user_name}}" in content_lower:
        return True, "Unresolved user placeholder"
    return False, ""


def _validate_runtime_user_placeholders(content: str) -> tuple[bool, str]:
    has_placeholder, reason = contains_unresolved_user_placeholders(content)
    if has_placeholder:
        return False, f"{USER_PLACEHOLDER_PREFIX} {reason}"
    return True, ""


def validate_bot_response_for_runtime(
    content: str,
    speaker: str,
    *,
    move: dict[str, Any] | None = None,
    scene_state: dict[str, Any] | None = None,
    continuity_manager: Any | None = None,
) -> tuple[bool, str]:
    """Production Character validation — objective runtime authority only."""
    ok, msg = _validate_runtime_user_placeholders(content)
    if not ok:
        return False, msg

    ok, msg = validate_registry_scene_state_updates(
        move,
        scene_state=scene_state,
        _continuity_manager=continuity_manager,
    )
    if not ok:
        return False, msg

    ok, msg = validate_spatial_transition_move_shape(move)
    if not ok:
        return False, msg

    ok, msg = validate_excursion_lifecycle_move_shape(move)
    if not ok:
        return False, msg

    ok, msg = validate_reintegration_move_shape(move)
    if not ok:
        return False, msg

    return True, ""


def validate_bot_response_for_scenario(
    content: str,
    speaker: str,
    user_name: str,
    chat_history: list[dict],
    state: Any | None = None,
    move: dict[str, Any] | None = None,
    canon_anchors: list[Any] | None = None,
    scene_state: dict[str, Any] | None = None,
    continuity_manager: Any | None = None,
    scene_grounding: dict[str, Any] | None = None,
    effective_user_trigger: str = "",
    character_system_prompt: str | None = None,
    simulation_scenario_id: str | None = None,
    orchestration_turn_number: int | None = None,
) -> tuple[bool, str]:
    """Offline/scenario validation: runtime objective checks plus investigation recall."""
    _ = (
        speaker,
        user_name,
        chat_history,
        state,
        canon_anchors,
        scene_grounding,
        effective_user_trigger,
        character_system_prompt,
    )
    ok, msg = validate_bot_response_for_runtime(
        content,
        speaker,
        move=move,
        scene_state=scene_state,
        continuity_manager=continuity_manager,
    )
    if not ok:
        return False, msg

    if (
        simulation_scenario_id
        and orchestration_turn_number is not None
        and move is not None
    ):
        try:
            scenario_raw = load_scenario(str(simulation_scenario_id).strip())
        except (OSError, ValueError, KeyError, TypeError):
            scenario_raw = None
        if isinstance(scenario_raw, dict):
            ok, msg = validate_investigation_recall_contract(
                move=move,
                orchestration_turn_number=int(orchestration_turn_number),
                scenario_raw=scenario_raw,
                effective_user_trigger=effective_user_trigger,
                character_system_prompt=character_system_prompt,
            )
            if not ok:
                return False, msg

    return True, ""

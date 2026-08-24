"""Event promotion policy for turn consequence classification.

Policy only: event type, significance, summary selection, grounding promotion,
and should_create_event gates. Does not mutate scene state or build PublicEvent.
"""

from typing import Any

from character_move_adapters import (
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)
from scene_grounding import compute_grounding_markers, grounding_markers_event_summary

from continuity_state import ConsequenceCategory


def determine_event_type(
    detected: list[Any],
    dialogue: str,
    action: str,
    environment_event: str,
) -> str:
    """Determine event type from detected consequence categories."""
    categories = {c.category for c in detected}

    if ConsequenceCategory.PHYSICAL_STATE_SET in categories:
        return "state"
    if ConsequenceCategory.MEDICAL_STATE_SET in categories:
        return "state"
    if ConsequenceCategory.REVELATION in categories:
        return "revelation"
    if {
        ConsequenceCategory.REFUSAL,
        ConsequenceCategory.AGREEMENT,
        ConsequenceCategory.COMMITMENT,
        ConsequenceCategory.ACCESS_GRANTED,
        ConsequenceCategory.ACCESS_DENIED,
    }.intersection(categories):
        return "decision"
    if environment_event and not (dialogue or action or categories):
        return "environment"
    if dialogue and not categories:
        return "dialogue"
    return "action"


def determine_significance(
    detected: list[Any],
    risk_level: str,
    tension_shift: str,
    dialogue: str,
    environment_event: str,
) -> str:
    """Determine event significance from consequences and metadata."""
    categories = {c.category for c in detected}

    pivotal_categories = {
        ConsequenceCategory.AUTHORITY_ASSERTED,
        ConsequenceCategory.AUTHORITY_CHALLENGED,
        ConsequenceCategory.TERRITORIAL_CLAIM,
        ConsequenceCategory.TERRITORIAL_DENIAL,
        ConsequenceCategory.REVELATION,
        ConsequenceCategory.COMMITMENT,
    }
    if categories.intersection(pivotal_categories):
        return "pivotal"

    if risk_level in ["high", "extreme"] or tension_shift == "escalate":
        return "major"
    if dialogue and any(marker in dialogue for marker in ["?", "you", "why"]):
        return "major"
    if environment_event or categories:
        return "major"

    return "minor"


def compute_event_promotion_policy_fields(
    *,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    detected: list[Any],
    state_changes: list[str],
    actionable_implications: list[str],
) -> dict[str, Any]:
    """Derive promotion fields after classifier + resolved-outcome state changes."""
    motivation = move.get("motivation", {})
    if not isinstance(motivation, dict):
        motivation = {}
    risk_level = str(motivation.get("risk_level", "medium") or "medium").lower()
    if is_canonical_v2_move(move):
        dialogue = legacy_flat_dialogue_text(move).lower()
        action = legacy_flat_action_text(move).lower()
    else:
        dialogue = str(move.get("dialogue", "") or "").lower()
        action = str(move.get("action", "") or "").lower()
    environment_event = str(
        director_decision.get("environment_event", "") or ""
    ).lower()
    tension_shift = str(director_decision.get("tension_shift", "") or "").lower()

    event_type = determine_event_type(
        detected, dialogue, action, environment_event
    )
    significance = determine_significance(
        detected, risk_level, tension_shift, dialogue, environment_event
    )

    if state_changes:
        summary = state_changes[0]
    elif action and dialogue:
        summary = f'{acting_character} {action}; said: "{dialogue}"'
    elif action:
        summary = f"{acting_character} {action}"
    elif dialogue:
        summary = f'{acting_character} said: "{dialogue}"'
    elif environment_event:
        summary = environment_event
    else:
        summary = f"{acting_character} took action"

    has_durable_change = bool(detected or state_changes or actionable_implications)
    has_scene_shift = bool(
        environment_event
        or risk_level in ["high", "extreme"]
        or tension_shift == "escalate"
    )
    base_promotion = has_durable_change or has_scene_shift

    move_for_grounding = (
        {
            **move,
            "action": legacy_flat_action_text(move),
            "dialogue": legacy_flat_dialogue_text(move),
        }
        if is_canonical_v2_move(move)
        else move
    )
    grounding_markers = compute_grounding_markers(
        acting_character, move_for_grounding, detected
    )
    should_create_event = base_promotion or bool(grounding_markers)

    if should_create_event and not base_promotion and grounding_markers:
        summary = grounding_markers_event_summary(grounding_markers)
        event_type = "state"
        significance = "minor"

    return {
        "should_create_event": should_create_event,
        "event_type": event_type,
        "summary": summary,
        "significance": significance,
        "grounding_markers": grounding_markers,
    }

"""Turn consequence classification for ContinuityManager (Issue #155 Slice E)."""

from __future__ import annotations

from typing import Any

from continuity_consequence_classifier import ConsequenceClassifier
from continuity_consequence_phrase_maps import (
    CATEGORY_ACTIONABLE_IMPLICATIONS,
    category_state_change_phrases,
)
from continuity_event_promotion_policy import compute_event_promotion_policy_fields
from continuity_resolved_outcomes import (
    build_housing_call_state_change,
    build_location_entry_state_change,
    build_sleeping_surface_state_change,
    build_suppressant_formulation_state_change,
)


def classify_turn_consequences_for_manager(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    *,
    consequence_classifier: ConsequenceClassifier,
) -> dict[str, Any]:
    """Classify turn consequences (façade: ``_classify_turn_consequences``)."""
    scene_state = (
        manager.scene_state.to_dict() if manager.scene_state is not None else None
    )
    detected = consequence_classifier.classify_turn(
        acting_character, move, director_decision, scene_state
    )

    state_changes: list[str] = []
    actionable_implications: list[str] = []
    tags: set[str] = set()

    category_state_change = category_state_change_phrases(acting_character)
    category_implication = CATEGORY_ACTIONABLE_IMPLICATIONS

    for consequence in detected:
        tags.add(consequence.category.value)

        state_change = category_state_change.get(consequence.category)
        if state_change and state_change not in state_changes:
            state_changes.append(state_change)

        implication = category_implication.get(consequence.category)
        if implication and implication not in actionable_implications:
            actionable_implications.append(implication)

    sleeping_assignment_state_change = build_sleeping_surface_state_change(
        move, manager.scene_state
    )
    if (
        sleeping_assignment_state_change
        and sleeping_assignment_state_change not in state_changes
    ):
        state_changes.append(sleeping_assignment_state_change)
        actionable_implications.append(
            "Sleeping arrangement state may now be ready for continuity settlement."
        )
    housing_call_state_change = build_housing_call_state_change(
        move, manager.scene_state
    )
    if housing_call_state_change and housing_call_state_change not in state_changes:
        state_changes.append(housing_call_state_change)
        actionable_implications.append(
            "Housing call outcome may now be ready for continuity settlement."
        )
    suppressant_formulation_state_change = (
        build_suppressant_formulation_state_change(move, manager.scene_state)
    )
    if (
        suppressant_formulation_state_change
        and suppressant_formulation_state_change not in state_changes
    ):
        state_changes.append(suppressant_formulation_state_change)
        actionable_implications.append(
            "Suppressant formulation state may now be ready for continuity settlement."
        )
    location_entry_state_change = build_location_entry_state_change(
        move, manager.scene_state
    )
    if (
        location_entry_state_change
        and location_entry_state_change not in state_changes
    ):
        state_changes.append(location_entry_state_change)
        actionable_implications.append(
            "Location entry permission may now be ready for continuity settlement."
        )

    promo = compute_event_promotion_policy_fields(
        acting_character=acting_character,
        move=move,
        director_decision=director_decision,
        detected=detected,
        state_changes=state_changes,
        actionable_implications=actionable_implications,
    )
    return {
        "should_create_event": promo["should_create_event"],
        "event_type": promo["event_type"],
        "summary": promo["summary"],
        "significance": promo["significance"],
        "state_changes": state_changes,
        "actionable_implications": actionable_implications,
        "tags": sorted(tags),
        "consequences": [c.category.value for c in detected],
        "grounding_markers": promo["grounding_markers"],
    }

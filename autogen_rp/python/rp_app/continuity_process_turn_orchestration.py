"""``process_turn`` sequencing after resolved mutations are applied (Issue #149 Slice 5).

Steps mirror ``ContinuityManager.process_turn`` exactly: consequence classification,
optional mutation audit payload attachment, scene-state update, event creation, issue
updates, resolved-outcome registration, interpretations, knowledge propagation,
turn metadata, summary block generation, and pipeline audit origin recording.

Mutation **composition**, **global validation**, and **apply** remain on the manager
entrypoint before this runs — no reordering and no deferred writes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from continuity_audit_origin import CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN
from continuity_mutation_pipeline import resolved_mutations_audit_payload
from continuity_resolved_outcomes import apply_registered_resolved_outcome_updates


def run_process_turn_after_resolved_mutations_applied(
    manager: Any,
    *,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    other_characters: list[str],
    timestamp: datetime,
    turn_index: int,
    resolved_mutations: list[Any],
) -> Any:
    turn_consequences = manager._classify_turn_consequences(
        acting_character,
        move,
        director_decision,
    )
    if resolved_mutations:
        turn_consequences["continuity_mutation_resolution"] = (
            resolved_mutations_audit_payload(resolved_mutations)
        )

    manager._update_scene_state(
        acting_character,
        move,
        director_decision,
        None,
        turn_consequences,
    )

    event = manager._maybe_create_event(
        acting_character,
        move,
        director_decision,
        timestamp,
        turn_index,
        turn_consequences,
    )
    if event:
        manager.public_events.append(event)
        manager.scene_state.recent_event_ids.append(event.event_id)
        manager.scene_state.recent_event_ids = manager.scene_state.recent_event_ids[-10:]

    manager._maybe_create_issue(
        acting_character,
        move,
        director_decision,
        event,
        timestamp,
        turn_consequences,
    )

    manager._update_issues(
        acting_character,
        move,
        event,
        turn_consequences,
    )

    resolved_outcome_debug = apply_registered_resolved_outcome_updates(
        manager=manager,
        move=move,
        event=event,
        turn_consequences=turn_consequences,
        turn_index=turn_index,
    )
    turn_consequences.setdefault("resolved_outcomes", {}).update(
        resolved_outcome_debug
    )

    manager._update_interpretations(
        acting_character, move, director_decision, other_characters, timestamp
    )

    manager._propagate_knowledge_from_turn(acting_character, move, other_characters)

    manager.turn_counter = turn_index
    manager.turn_metadata_by_index[turn_index] = turn_consequences
    manager._maybe_generate_summary_block(timestamp)

    manager._pending_pipeline_audit_origin_index = turn_index
    manager._record_continuity_audit_event(
        CONTINUITY_AUDIT_ORIGIN_KIND_PIPELINE_TURN, turn_index
    )

    return manager.get_snapshot(timestamp)

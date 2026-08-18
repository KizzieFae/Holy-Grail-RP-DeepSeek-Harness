"""Public event and summary-block surface for ContinuityManager (mechanical extraction)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from continuity_summary_helpers import (
    build_summary_block as build_summary_block_helper,
    collect_interpretation_shifts as collect_interpretation_shifts_helper,
    maybe_generate_summary_block as maybe_generate_summary_block_helper,
)
from perception_audibility import event_knowledge_recipients, public_safe_event_summary

from continuity_state import PublicEvent, SummaryBlock


def maybe_create_event_for_manager(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    timestamp: datetime,
    turn_index: int,
    turn_consequences: dict[str, Any],
) -> Optional[PublicEvent]:
    if not turn_consequences.get("should_create_event", False):
        return None

    manager.event_counter += 1
    event_id = f"evt_{timestamp.isoformat()}_{manager.event_counter}"

    present_list = (
        list(manager.scene_state.present_characters[:])
        if manager.scene_state
        else [acting_character]
    )
    recipients = event_knowledge_recipients(
        move,
        acting_character=acting_character,
        present_characters=present_list,
    )
    if not recipients:
        recipients = [acting_character]
    raw_summary = str(
        turn_consequences.get("summary", "")
        or f"{acting_character} took action"
    )
    safe_summary = public_safe_event_summary(
        acting_character=acting_character,
        move=move,
        provisional_summary=raw_summary,
    )

    return PublicEvent(
        event_id=event_id,
        timestamp=timestamp,
        event_type=str(turn_consequences.get("event_type", "action") or "action"),
        participants=[acting_character],
        summary=safe_summary,
        turn_index=turn_index,
        location=manager.scene_state.location if manager.scene_state else None,
        significance=str(turn_consequences.get("significance", "minor") or "minor"),
        observed_by=list(recipients),
        known_by=list(recipients),
        state_changes=[
            str(item)
            for item in turn_consequences.get("state_changes", [])
            if str(item).strip()
        ],
        actionable_implications=[
            str(item)
            for item in turn_consequences.get("actionable_implications", [])
            if str(item).strip()
        ],
        grounding_markers=[
            str(item)
            for item in turn_consequences.get("grounding_markers", [])
            if str(item).strip()
        ],
    )


def maybe_generate_summary_block_for_manager(
    manager: Any, timestamp: datetime
) -> SummaryBlock | None:
    return maybe_generate_summary_block_helper(manager=manager, timestamp=timestamp)


def build_summary_block_for_manager(
    manager: Any, events: list[PublicEvent], generated_at: datetime
) -> SummaryBlock:
    return build_summary_block_helper(
        manager=manager, events=events, generated_at=generated_at
    )


def collect_interpretation_shifts_for_manager(
    manager: Any, start_time: datetime, end_time: datetime
) -> list[dict[str, object]]:
    return collect_interpretation_shifts_helper(
        manager=manager, start_time=start_time, end_time=end_time
    )

from datetime import datetime
from typing import Any

from continuity_state import PublicEvent, ScenePhase, SummaryBlock


def _append_continuity_fact(facts: list[str], seen: set[str], fact: str) -> None:
    cleaned = str(fact or "").strip()
    if not cleaned or cleaned in seen:
        return
    facts.append(cleaned)
    seen.add(cleaned)


def _primary_participant_name(event: PublicEvent) -> str:
    for participant in event.participants:
        name = str(participant or "").strip()
        if name:
            return name
    return "Someone"


def collect_continuity_facts(*, events: list[PublicEvent]) -> list[str]:
    facts: list[str] = []
    seen: set[str] = set()
    for event in events:
        summary = str(event.summary or "")
        summary_lower = summary.lower()
        subject_name = _primary_participant_name(event)

        for state_change in getattr(event, "state_changes", []):
            _append_continuity_fact(facts, seen, str(state_change or ""))

        if any(
            phrase in summary_lower
            for phrase in (
                "didn't lead anyone here",
                "did not lead anyone here",
                "didn't run straight here",
                "did not run straight here",
                "wouldn't know this building",
                "would not know this building",
                "wouldn't know this place",
                "would not know this place",
                "wouldn't know this apartment",
                "would not know this apartment",
            )
        ):
            _append_continuity_fact(
                facts,
                seen,
                f"{subject_name} denied leading the outside threat directly to the refuge.",
            )

        if any(
            phrase in summary_lower
            for phrase in (
                "doubled back",
                "lost them in the storm",
                "didn't run straight here",
                "did not run straight here",
            )
        ) or ("sewer" in summary_lower and "lost" in summary_lower):
            _append_continuity_fact(
                facts,
                seen,
                f"{subject_name} described evasive movement intended to break pursuit before reaching the refuge.",
            )

        if "lost" in summary_lower and any(
            token in summary_lower for token in ("hour", "little more", "minutes")
        ):
            _append_continuity_fact(
                facts,
                seen,
                f"{subject_name} provided a rough timeline for when the pursuit was last lost.",
            )

        if any(
            phrase in summary_lower
            for phrase in (
                "you're staying here tonight",
                "you are staying here tonight",
                "move tomorrow",
                "move you",
            )
        ):
            _append_continuity_fact(
                facts,
                seen,
                "A provisional safety plan was set for the current refuge with relocation to follow.",
            )

    return facts


def maybe_generate_summary_block(
    *, manager: Any, timestamp: datetime
) -> SummaryBlock | None:
    if (
        manager.turn_counter <= 0
        or manager.turn_counter % manager.summary_interval != 0
    ):
        return None

    summary_cutoff_index = max(
        0, len(manager.public_events) - manager.recent_event_window
    )
    if summary_cutoff_index <= manager.last_summarized_event_index:
        return None

    events_to_summarize = manager.public_events[
        manager.last_summarized_event_index : summary_cutoff_index
    ]
    if not events_to_summarize:
        return None

    summary_block = build_summary_block(
        manager=manager, events=events_to_summarize, generated_at=timestamp
    )
    manager.summary_blocks.append(summary_block)
    manager.summary_counter += 1
    manager.last_summarized_event_index = summary_cutoff_index
    return summary_block


def build_summary_block(
    *, manager: Any, events: list[PublicEvent], generated_at: datetime
) -> SummaryBlock:
    first_event = events[0]
    last_event = events[-1]
    start_time = first_event.timestamp
    end_time = last_event.timestamp
    turn_start = next(
        (event.turn_index for event in events if event.turn_index is not None),
        1,
    )
    turn_end = next(
        (
            event.turn_index
            for event in reversed(events)
            if event.turn_index is not None
        ),
        turn_start,
    )
    key_events = [event.summary for event in events[-5:]]
    participant_names = list(
        dict.fromkeys(
            participant
            for event in events
            for participant in event.participants
            if participant
        )
    )
    issue_counts: dict[str, int] = {}
    significance_counts = {"minor": 0, "major": 0, "pivotal": 0}
    impact_score = 0
    for event in events:
        significance_counts[event.significance] = (
            significance_counts.get(event.significance, 0) + 1
        )
        impact_score += {"minor": 1, "major": 2, "pivotal": 3}.get(
            event.significance,
            1,
        )
        for issue_id in event.related_issue_ids:
            issue_counts[issue_id] = issue_counts.get(issue_id, 0) + 1
    dominant_issue_ids = [
        issue_id
        for issue_id, _count in sorted(
            issue_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:3]
    ]

    return SummaryBlock(
        summary_id=f"summary_{turn_start}_{turn_end}",
        turn_range_start=turn_start,
        turn_range_end=turn_end,
        generated_at=generated_at,
        location=manager.scene_state.location if manager.scene_state else None,
        scene_phase=(
            manager.scene_state.phase.value
            if manager.scene_state is not None
            else ScenePhase.OPENING.value
        ),
        tension_level=(
            manager.scene_state.current_tension_level
            if manager.scene_state is not None
            else "low"
        ),
        continuity_facts=collect_continuity_facts(events=events),
        source_event_ids=[event.event_id for event in events],
        key_events=key_events,
        issue_updates=collect_issue_updates(
            manager=manager, start_time=start_time, end_time=end_time
        ),
        interpretation_shifts=collect_interpretation_shifts(
            manager=manager, start_time=start_time, end_time=end_time
        ),
        participant_names=participant_names,
        dominant_issue_ids=dominant_issue_ids,
        significance_counts=significance_counts,
        impact_score=impact_score,
    )


def collect_issue_updates(
    *, manager: Any, start_time: datetime, end_time: datetime
) -> list[dict[str, str]]:
    issue_updates: list[dict[str, str]] = []
    for issue in manager.issues.values():
        update_type = ""
        if start_time <= issue.created_at <= end_time:
            update_type = "introduced"
        elif issue.resolved_at and start_time <= issue.resolved_at <= end_time:
            update_type = "resolved"
        elif issue.last_updated and start_time <= issue.last_updated <= end_time:
            update_type = "updated"

        if not update_type:
            continue

        issue_updates.append(
            {
                "issue_id": issue.issue_id,
                "description": issue.description,
                "status": issue.status.value,
                "update_type": update_type,
                "status_reason": issue.status_reason,
                "pressure_kind": issue.pressure_kind,
                "blocked_what": issue.blocked_what,
                "required_next_step": issue.required_next_step,
            }
        )
    return issue_updates


def collect_interpretation_shifts(
    *, manager: Any, start_time: datetime, end_time: datetime
) -> list[dict[str, object]]:
    grouped: list[dict[str, object]] = []
    for character_name, items in manager.interpretations.items():
        recent_items = [
            item for item in items if start_time <= item.formed_at <= end_time
        ]
        if not recent_items:
            continue

        grouped.append(
            {
                "character_name": character_name,
                "subject_ids": [item.subject_id for item in recent_items[-2:]],
                "emotional_reactions": list(
                    dict.fromkeys(
                        item.emotional_reaction
                        for item in recent_items
                        if item.emotional_reaction
                    )
                )[:2],
                "interpretations": [item.interpretation for item in recent_items[-2:]],
            }
        )
    return grouped


def get_summary_blocks(*, manager: Any, limit: int) -> list[SummaryBlock]:
    if limit <= 0:
        return []
    return manager.summary_blocks[-limit:]

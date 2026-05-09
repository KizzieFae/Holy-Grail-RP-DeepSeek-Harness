"""Read-only issue / event / summary retrieval from a continuity manager store."""

from __future__ import annotations

from typing import Any, Optional

from continuity_state import IssueState, IssueStatus, PublicEvent, SummaryBlock


def get_active_issues(
    *,
    manager: Any,
    limit: int,
    participants: Optional[list[str]] = None,
    statuses: Optional[list[IssueStatus]] = None,
) -> list[IssueState]:
    participant_set = set(participants or [])
    allowed_statuses = set(statuses or [IssueStatus.ACTIVE, IssueStatus.ESCALATING])
    active_issue_ids = (
        manager.scene_state.active_issue_ids if manager.scene_state else []
    )
    issues = [
        manager.issues[issue_id]
        for issue_id in active_issue_ids
        if issue_id in manager.issues
    ]
    filtered: list[IssueState] = []
    for issue in issues:
        if allowed_statuses and issue.status not in allowed_statuses:
            continue
        if participant_set and not participant_set.intersection(issue.participants):
            continue
        filtered.append(issue)
    return filtered[-limit:] if limit > 0 else filtered


def retrieve_public_events(
    *,
    manager: Any,
    participants: Optional[list[str]] = None,
    issue_ids: Optional[list[str]] = None,
    location: Optional[str] = None,
    significance: Optional[list[str]] = None,
    limit: Optional[int] = None,
    known_by: Optional[str] = None,
    min_turn_index: Optional[int] = None,
) -> list[PublicEvent]:
    participant_set = set(participants or [])
    issue_id_set = set(issue_ids or [])
    significance_set = {str(item) for item in (significance or [])}
    filtered: list[PublicEvent] = []
    for event in manager.public_events:
        if known_by and event.knowledge_level_for(known_by) is None:
            continue
        if participant_set and not participant_set.intersection(event.participants):
            continue
        if issue_id_set and not issue_id_set.intersection(event.related_issue_ids):
            continue
        if location and event.location != location:
            continue
        if significance_set and event.significance not in significance_set:
            continue
        if min_turn_index is not None and (
            event.turn_index is None or event.turn_index < min_turn_index
        ):
            continue
        filtered.append(event)
    if limit is not None and limit > 0:
        return filtered[-limit:]
    return filtered


def retrieve_summary_blocks(
    *,
    manager: Any,
    participants: Optional[list[str]] = None,
    issue_ids: Optional[list[str]] = None,
    location: Optional[str] = None,
    limit: int,
    min_turn_index: Optional[int] = None,
) -> list[SummaryBlock]:
    participant_set = set(participants or [])
    issue_id_set = set(issue_ids or [])
    filtered: list[SummaryBlock] = []
    for summary in manager.summary_blocks:
        if location and summary.location != location:
            continue
        if min_turn_index is not None and summary.turn_range_end < min_turn_index:
            continue
        if issue_id_set and not any(
            update.get("issue_id") in issue_id_set for update in summary.issue_updates
        ):
            continue
        if participant_set and not participant_set.intersection(
            summary.participant_names
        ):
            continue
        filtered.append(summary)
    ranked = sorted(
        filtered,
        key=lambda item: (item.impact_score, item.turn_range_end),
        reverse=True,
    )
    return ranked[:limit] if limit > 0 else ranked


def get_resolved_issue_descriptions(*, manager: Any, limit: int) -> list[str]:
    resolved = [
        issue.description
        for issue in manager.issues.values()
        if issue.status == IssueStatus.RESOLVED
    ]
    return resolved[-limit:] if limit > 0 else resolved

"""Issue lifecycle helpers invoked through ContinuityManager (mechanical extraction)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from continuity_issue_helpers import (
    get_active_issues as get_active_issues_helper,
    maybe_create_issue,
    update_issues,
)
from continuity_summary_helpers import collect_issue_updates as collect_issue_updates_helper
from continuity_issue_manager_wiring import (
    ISSUE_STALL_TURN_THRESHOLD,
    MAX_ACTIVE_ISSUES,
    find_matching_issue_for_manager,
    issue_tokens_for_manager_stopwords,
    link_issue_interactions_callback,
    merge_issue_terms_positional,
)
from continuity_state import IssueStatus, PublicEvent


def acting_character_required_by_active_confrontation(
    manager: Any, acting_character: str
) -> bool:
    if not manager.scene_state:
        return False
    issues = get_active_issues_helper(
        manager=manager,
        limit=24,
        participants=[acting_character],
        statuses=[IssueStatus.ACTIVE, IssueStatus.ESCALATING],
    )
    for issue in issues:
        if acting_character not in issue.participants:
            continue
        if len(issue.participants) >= 2:
            return True
        blocked = getattr(issue, "blocked_characters", None) or []
        if acting_character in blocked:
            return True
        rn = (issue.required_next_step or "").lower()
        if any(
            needle in rn
            for needle in (
                "targeted character",
                "must exit",
                "challenge back",
                "submit",
                "respond",
            )
        ):
            return True
    return False


def collect_issue_updates_for_manager(
    manager: Any, start_time: datetime, end_time: datetime
) -> list[dict[str, str]]:
    return collect_issue_updates_helper(
        manager=manager, start_time=start_time, end_time=end_time
    )


def maybe_create_issue_for_manager(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    event: Optional[PublicEvent],
    timestamp: datetime,
    turn_consequences: dict[str, Any],
) -> None:
    maybe_create_issue(
        manager=manager,
        acting_character=acting_character,
        move=move,
        director_decision=director_decision,
        event=event,
        consequence_tags={
            str(item)
            for item in turn_consequences.get("tags", [])
            if str(item).strip()
        },
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
        timestamp=timestamp,
        max_active_issues=MAX_ACTIVE_ISSUES,
        turn_tokens_fn=manager._turn_tokens,
        find_matching_issue_fn=lambda p: find_matching_issue_for_manager(manager, p),
        merge_issue_terms_fn=merge_issue_terms_positional,
        link_issue_interactions_fn=link_issue_interactions_callback(manager),
    )


def update_issues_for_manager(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    event: Optional[PublicEvent],
    turn_consequences: dict[str, Any],
) -> None:
    update_issues(
        manager=manager,
        acting_character=acting_character,
        move=move,
        event=event,
        consequence_tags={
            str(item)
            for item in turn_consequences.get("tags", [])
            if str(item).strip()
        },
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
        issue_stall_turn_threshold=ISSUE_STALL_TURN_THRESHOLD,
        turn_tokens_fn=manager._turn_tokens,
        issue_tokens_fn=issue_tokens_for_manager_stopwords,
        merge_issue_terms_fn=merge_issue_terms_positional,
        link_issue_interactions_fn=link_issue_interactions_callback(manager),
    )

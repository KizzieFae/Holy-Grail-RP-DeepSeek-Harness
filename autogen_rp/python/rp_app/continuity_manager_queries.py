"""Retrieval, context, and knowledge-propagation surface for ContinuityManager."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from continuity_issue_helpers import (
    get_active_issues as get_active_issues_helper,
    get_resolved_issue_descriptions as get_resolved_issue_descriptions_helper,
    retrieve_public_events as retrieve_public_events_helper,
    retrieve_summary_blocks as retrieve_summary_blocks_helper,
)
from continuity_knowledge_helpers import (
    mentioned_participants as mentioned_participants_helper,
    propagate_knowledge_from_turn as propagate_knowledge_from_turn_helper,
    share_event_knowledge as share_event_knowledge_helper,
    update_interpretations as update_interpretations_helper,
)
from continuity_scene_helpers import (
    build_character_context,
    build_orchestration_context,
    build_snapshot,
)
from continuity_summary_helpers import get_summary_blocks as get_summary_blocks_helper

from continuity_state import (
    ContinuitySnapshot,
    IssueState,
    IssueStatus,
    PublicEvent,
    SummaryBlock,
)


def get_active_issues_for_manager(
    manager: Any,
    *,
    limit: int,
    participants: Optional[list[str]] = None,
    statuses: Optional[list[IssueStatus]] = None,
) -> list[IssueState]:
    return get_active_issues_helper(
        manager=manager,
        limit=limit,
        participants=participants,
        statuses=statuses,
    )


def retrieve_public_events_for_manager(
    manager: Any,
    *,
    participants: Optional[list[str]] = None,
    issue_ids: Optional[list[str]] = None,
    location: Optional[str] = None,
    significance: Optional[list[str]] = None,
    limit: Optional[int] = None,
    known_by: Optional[str] = None,
    min_turn_index: Optional[int] = None,
) -> list[PublicEvent]:
    return retrieve_public_events_helper(
        manager=manager,
        participants=participants,
        issue_ids=issue_ids,
        location=location,
        significance=significance,
        limit=limit,
        known_by=known_by,
        min_turn_index=min_turn_index,
    )


def retrieve_summary_blocks_for_manager(
    manager: Any,
    *,
    participants: Optional[list[str]] = None,
    issue_ids: Optional[list[str]] = None,
    location: Optional[str] = None,
    limit: int,
    min_turn_index: Optional[int] = None,
) -> list[SummaryBlock]:
    return retrieve_summary_blocks_helper(
        manager=manager,
        participants=participants,
        issue_ids=issue_ids,
        location=location,
        limit=limit,
        min_turn_index=min_turn_index,
    )


def get_resolved_issue_descriptions_for_manager(
    manager: Any, limit: int = 8
) -> list[str]:
    return get_resolved_issue_descriptions_helper(manager=manager, limit=limit)


def get_orchestration_context_for_manager(
    manager: Any,
    *,
    active_issue_limit: int,
    recent_event_limit: int,
    summary_limit: int,
) -> dict[str, Any]:
    return build_orchestration_context(
        manager=manager,
        active_issue_limit=active_issue_limit,
        recent_event_limit=recent_event_limit,
        summary_limit=summary_limit,
    )


def share_event_knowledge_for_manager(
    manager: Any,
    event_id: str,
    character_name: str,
    knowledge_type: str,
) -> None:
    share_event_knowledge_helper(
        manager=manager,
        event_id=event_id,
        character_name=character_name,
        knowledge_type=knowledge_type,
    )


def propagate_knowledge_from_turn_for_manager(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    other_characters: list[str],
    *,
    knowledge_share_min_overlap: int,
) -> None:
    propagate_knowledge_from_turn_helper(
        manager=manager,
        acting_character=acting_character,
        move=move,
        other_characters=other_characters,
        knowledge_share_min_overlap=knowledge_share_min_overlap,
        turn_tokens_fn=manager._turn_tokens,
        event_tokens_fn=manager._event_tokens,
        mentioned_participants_fn=manager._mentioned_participants,
        share_event_knowledge_fn=manager.share_event_knowledge,
    )


def get_summary_blocks_for_manager(manager: Any, *, limit: int) -> list[SummaryBlock]:
    return get_summary_blocks_helper(manager=manager, limit=limit)


def get_snapshot_for_manager(
    manager: Any,
    timestamp: Optional[datetime],
    normalize_timestamp_fn: Any,
) -> ContinuitySnapshot:
    return build_snapshot(
        manager=manager,
        timestamp=timestamp,
        normalize_timestamp_fn=normalize_timestamp_fn,
    )


def get_character_context_for_manager(
    manager: Any,
    character_name: str,
    *,
    max_interpretations: int,
    default_active_issue_limit: int,
    default_summary_prompt_limit: int,
) -> dict[str, Any]:
    return build_character_context(
        manager=manager,
        character_name=character_name,
        max_interpretations=max_interpretations,
        default_active_issue_limit=default_active_issue_limit,
        default_summary_prompt_limit=default_summary_prompt_limit,
    )


def update_interpretations_for_manager(
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    other_characters: list[str],
    timestamp: datetime,
) -> None:
    update_interpretations_helper(
        manager=manager,
        acting_character=acting_character,
        move=move,
        other_characters=other_characters,
        timestamp=timestamp,
    )


def mentioned_participants_for_text(text: str, participants: list[str]) -> list[str]:
    return mentioned_participants_helper(text=text, participants=participants)

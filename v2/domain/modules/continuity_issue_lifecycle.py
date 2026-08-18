"""Issue create/update lifecycle orchestration (continuity mutation authority)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from continuity_issue_matching import _matches_issue_signals
from continuity_issue_pressure import (
    ACCESS_CONSEQUENCE_TAGS,
    CONTROL_CONSEQUENCE_TAGS,
    INFORMATION_CONSEQUENCE_TAGS,
    PLAN_CONSEQUENCE_TAGS,
    PRESENCE_CONSEQUENCE_TAGS,
    _build_issue_profile_from_issue,
    _clean_text,
    _dedupe_strings,
    _default_escalation_signals,
    _default_resolution_signals,
)
from continuity_issue_transitions import (
    _build_status_reason,
    apply_mixed_transition_plateau_refresh,
)
from continuity_state import IssueState, IssueStatus, PublicEvent


def maybe_create_issue(
    *,
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    event: Optional[PublicEvent],
    consequence_tags: set[str],
    state_changes: list[str],
    actionable_implications: list[str],
    timestamp: datetime,
    max_active_issues: int,
    turn_tokens_fn,
    find_matching_issue_fn,
    merge_issue_terms_fn,
    link_issue_interactions_fn,
) -> None:
    if manager.scene_state is None:
        return

    import continuity_issue_helpers as _cih

    tension_shift = _clean_text(director_decision.get("tension_shift", "")).lower()
    pressure_profile = _cih._build_turn_pressure_profile(
        manager=manager,
        acting_character=acting_character,
        move=move,
        event=event,
        consequence_tags=consequence_tags,
        state_changes=state_changes,
        actionable_implications=actionable_implications,
    )
    if not pressure_profile.get("should_track"):
        return

    matched_terms = turn_tokens_fn(move)
    matching_issue = find_matching_issue_fn(pressure_profile)
    if matching_issue is not None:
        issue_profile = _build_issue_profile_from_issue(matching_issue)
        transition = "escalated" if tension_shift == "escalate" else "advanced"
        matching_issue.status = (
            IssueStatus.ESCALATING if transition == "escalated" else IssueStatus.ACTIVE
        )
        matching_issue.pressure_kind = matching_issue.pressure_kind or _clean_text(
            pressure_profile.get("pressure_kind", "")
        )
        matching_issue.blocked_what = matching_issue.blocked_what or _clean_text(
            pressure_profile.get("blocked_what", "")
        )
        matching_issue.blocked_characters = _dedupe_strings(
            matching_issue.blocked_characters
            + pressure_profile.get("blocked_characters", [])
        )
        matching_issue.last_change = _clean_text(
            pressure_profile.get("last_change", "")
        )
        matching_issue.required_next_step = (
            _clean_text(pressure_profile.get("required_next_step", ""))
            or matching_issue.required_next_step
        )
        matching_issue.status_reason = _build_status_reason(
            transition=transition,
            issue_profile=issue_profile,
            turn_profile=pressure_profile,
        )
        matching_issue.last_updated = timestamp
        matching_issue.last_turn_index = manager.turn_counter + 1
        merge_issue_terms_fn(matching_issue, matched_terms)
        if event is not None and matching_issue.issue_id not in event.related_issue_ids:
            event.related_issue_ids.append(matching_issue.issue_id)
        if event is not None and event.event_id not in matching_issue.related_event_ids:
            matching_issue.related_event_ids.append(event.event_id)
        link_issue_interactions_fn(matching_issue.issue_id)
        return

    active_issue_ids = [
        issue_id
        for issue_id in manager.scene_state.active_issue_ids
        if issue_id in manager.issues
        and manager.issues[issue_id].status
        in [IssueStatus.ACTIVE, IssueStatus.ESCALATING]
    ]
    if len(active_issue_ids) >= max_active_issues:
        return

    issue_id = f"issue_{timestamp.isoformat()}_{len(manager.issues) + 1}"
    new_issue = IssueState(
        issue_id=issue_id,
        description=_clean_text(pressure_profile.get("description", "")),
        participants=pressure_profile.get("participants", []) or [acting_character],
        status=(
            IssueStatus.ESCALATING
            if tension_shift == "escalate"
            else IssueStatus.ACTIVE
        ),
        created_at=timestamp,
        escalation_signals=_default_escalation_signals(
            _clean_text(pressure_profile.get("pressure_kind", "")),
            consequence_tags,
        ),
        resolution_signals=_default_resolution_signals(
            _clean_text(pressure_profile.get("pressure_kind", ""))
        ),
        last_updated=timestamp,
        last_turn_index=manager.turn_counter + 1,
        status_reason=_build_status_reason(
            transition="escalated" if tension_shift == "escalate" else "advanced",
            issue_profile=pressure_profile,
            turn_profile=pressure_profile,
        ),
        matched_terms=sorted(matched_terms),
        related_event_ids=[event.event_id] if event is not None else [],
        pressure_kind=_clean_text(pressure_profile.get("pressure_kind", "")),
        blocked_what=_clean_text(pressure_profile.get("blocked_what", "")),
        blocked_characters=pressure_profile.get("blocked_characters", [])
        or [acting_character],
        last_change=_clean_text(pressure_profile.get("last_change", "")),
        required_next_step=_clean_text(pressure_profile.get("required_next_step", "")),
    )
    manager.issues[issue_id] = new_issue
    manager.scene_state.active_issue_ids.append(issue_id)
    if event is not None:
        event.related_issue_ids.append(issue_id)
    link_issue_interactions_fn(issue_id)


def update_issues(
    *,
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    event: Optional[PublicEvent],
    consequence_tags: set[str],
    state_changes: list[str],
    actionable_implications: list[str],
    issue_stall_turn_threshold: int,
    turn_tokens_fn,
    issue_tokens_fn,
    merge_issue_terms_fn,
    link_issue_interactions_fn,
) -> None:
    if not manager.scene_state:
        return

    import continuity_issue_helpers as _cih

    updated_issue_ids: set[str] = set()
    current_turn_index = manager.turn_counter + 1
    matched_terms = turn_tokens_fn(move)
    timestamp = event.timestamp if event is not None else datetime.now(timezone.utc)
    turn_profile = _cih._build_turn_pressure_profile(
        manager=manager,
        acting_character=acting_character,
        move=move,
        event=event,
        consequence_tags=consequence_tags,
        state_changes=state_changes,
        actionable_implications=actionable_implications,
    )
    source_text = _clean_text(turn_profile.get("source_text", ""))

    for issue_id in manager.scene_state.active_issue_ids:
        issue = manager.issues.get(issue_id)
        if not issue or issue.status in [IssueStatus.RESOLVED, IssueStatus.DORMANT]:
            continue

        issue_profile = _build_issue_profile_from_issue(issue)
        match_score = _cih._pressure_match_score(
            turn_profile=turn_profile,
            issue_profile=issue_profile,
            issue_tokens_fn=issue_tokens_fn,
        )
        signal_match = _matches_issue_signals(
            issue, source_text, resolution=False
        ) or _matches_issue_signals(issue, source_text, resolution=True)
        if match_score >= 4 or signal_match:
            transition = _cih._determine_issue_transition(
                issue_profile=issue_profile,
                turn_profile=turn_profile,
                issue=issue,
                consequence_tags=consequence_tags,
                source_text=source_text,
            )
            was_escalating_this_turn = (
                issue.status == IssueStatus.ESCALATING
                and issue.last_turn_index == current_turn_index
            )
            if transition == "resolved":
                issue.status = IssueStatus.RESOLVED
                issue.resolved_at = timestamp
            elif transition == "escalated" or was_escalating_this_turn:
                issue.status = IssueStatus.ESCALATING
            else:
                issue.status = IssueStatus.ACTIVE
            issue.pressure_kind = issue.pressure_kind or _clean_text(
                turn_profile.get("pressure_kind", "")
            )
            issue.blocked_what = issue.blocked_what or _clean_text(
                turn_profile.get("blocked_what", "")
            )
            issue.blocked_characters = _dedupe_strings(
                issue.blocked_characters + turn_profile.get("blocked_characters", [])
            )
            issue.last_change = (
                _clean_text(turn_profile.get("last_change", "")) or issue.last_change
            )
            if transition in {"narrowed", "advanced"} and _clean_text(
                turn_profile.get("required_next_step", "")
            ):
                issue.required_next_step = _clean_text(
                    turn_profile.get("required_next_step", "")
                )
            issue.status_reason = _build_status_reason(
                transition=transition,
                issue_profile=issue_profile,
                turn_profile=turn_profile,
            )
            apply_mixed_transition_plateau_refresh(
                issue=issue,
                transition=transition,
                turn_profile=turn_profile,
                current_turn_index=current_turn_index,
            )
            issue.last_updated = timestamp
            issue.last_turn_index = current_turn_index
            merge_issue_terms_fn(issue, matched_terms)
            if event is not None and event.event_id not in issue.related_event_ids:
                issue.related_event_ids.append(event.event_id)
            updated_issue_ids.add(issue_id)
            link_issue_interactions_fn(issue_id)

        if issue.status not in [IssueStatus.RESOLVED, IssueStatus.DORMANT]:
            last_turn_index = issue.last_turn_index or current_turn_index
            if (
                issue_id not in updated_issue_ids
                and current_turn_index - last_turn_index >= issue_stall_turn_threshold
                and not consequence_tags.intersection(
                    PLAN_CONSEQUENCE_TAGS
                    | ACCESS_CONSEQUENCE_TAGS
                    | CONTROL_CONSEQUENCE_TAGS
                    | PRESENCE_CONSEQUENCE_TAGS
                    | INFORMATION_CONSEQUENCE_TAGS
                )
            ):
                issue.status = IssueStatus.STALLED
                issue.status_reason = "Recent turns did not materially change this pressure or force a next step."
                issue.last_updated = timestamp
                issue.last_turn_index = current_turn_index

    manager.scene_state.active_issue_ids = [
        issue_id
        for issue_id in manager.scene_state.active_issue_ids
        if issue_id in manager.issues
        and manager.issues[issue_id].status
        in [IssueStatus.ACTIVE, IssueStatus.ESCALATING]
    ]

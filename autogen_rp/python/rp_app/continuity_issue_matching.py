"""Issue graph edges, token overlap scoring, and signal substring checks."""

from __future__ import annotations

from typing import Any

from continuity_issue_pressure import (
    _build_issue_profile_from_issue,
    _clean_text,
)
from continuity_state import IssueState, IssueStatus


def merge_issue_terms(*, issue: IssueState, matched_terms: set[str]) -> None:
    merged = list(dict.fromkeys(issue.matched_terms + sorted(matched_terms)))
    issue.matched_terms = merged[-10:]


def link_issue_interactions(*, manager: Any, issue_id: str) -> None:
    issue = manager.issues.get(issue_id)
    if issue is None:
        return
    for other_id in manager.scene_state.active_issue_ids if manager.scene_state else []:
        if other_id == issue_id:
            continue
        other_issue = manager.issues.get(other_id)
        if other_issue is None:
            continue
        participant_overlap = set(issue.participants).intersection(
            other_issue.participants
        )
        token_overlap = set(issue.matched_terms).intersection(other_issue.matched_terms)
        same_pressure_kind = (
            bool(issue.pressure_kind)
            and issue.pressure_kind == other_issue.pressure_kind
        )
        if participant_overlap and (token_overlap or same_pressure_kind):
            if other_id not in issue.interaction_issue_ids:
                issue.interaction_issue_ids.append(other_id)
            if issue_id not in other_issue.interaction_issue_ids:
                other_issue.interaction_issue_ids.append(issue_id)


def find_matching_issue(
    *, manager: Any, pressure_profile: dict[str, Any], issue_tokens_fn
) -> IssueState | None:
    best_issue: IssueState | None = None
    best_score = 0
    for issue in manager.issues.values():
        if issue.status == IssueStatus.RESOLVED:
            continue
        issue_profile = _build_issue_profile_from_issue(issue)
        score = _pressure_match_score(
            turn_profile=pressure_profile,
            issue_profile=issue_profile,
            issue_tokens_fn=issue_tokens_fn,
        )
        if score > best_score:
            best_issue = issue
            best_score = score
    return best_issue if best_score >= 4 else None


def _pressure_match_score(
    *, turn_profile: dict[str, Any], issue_profile: dict[str, Any], issue_tokens_fn
) -> int:
    participant_overlap = set(turn_profile.get("participants", [])).intersection(
        issue_profile.get("participants", [])
    )
    if not participant_overlap:
        return 0

    score = 1
    if set(turn_profile.get("participants", [])) == set(
        issue_profile.get("participants", [])
    ):
        score += 1
    if turn_profile.get("pressure_kind") and turn_profile.get(
        "pressure_kind"
    ) == issue_profile.get("pressure_kind"):
        score += 3

    turn_blocked = issue_tokens_fn(_clean_text(turn_profile.get("blocked_what", "")))
    issue_blocked = issue_tokens_fn(_clean_text(issue_profile.get("blocked_what", "")))
    if turn_blocked and issue_blocked and turn_blocked.intersection(issue_blocked):
        score += 2

    turn_next = issue_tokens_fn(_clean_text(turn_profile.get("required_next_step", "")))
    issue_next = issue_tokens_fn(
        _clean_text(issue_profile.get("required_next_step", ""))
    )
    if turn_next and issue_next and turn_next.intersection(issue_next):
        score += 1

    turn_description = _clean_text(turn_profile.get("description", ""))
    issue_description = _clean_text(issue_profile.get("description", ""))
    if turn_description and issue_description:
        if (
            turn_description.lower() in issue_description.lower()
            or issue_description.lower() in turn_description.lower()
        ):
            score += 2
        overlap = issue_tokens_fn(turn_description).intersection(
            issue_tokens_fn(issue_description)
        )
        if len(overlap) >= 2:
            score += 1

    return score


def _matches_issue_signals(
    issue: IssueState, source_text: str, *, resolution: bool
) -> bool:
    signals = issue.resolution_signals if resolution else issue.escalation_signals
    lowered = source_text.lower()
    return any(
        _clean_text(signal).lower() in lowered
        for signal in signals
        if _clean_text(signal)
    )

import re
from datetime import datetime, timezone
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


def issue_tokens(*, text: str, stopwords: set[str]) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= 4 and token not in stopwords
    }


def turn_tokens(*, move: dict[str, Any], issue_tokens_fn) -> set[str]:
    from character_move_adapters import (
        is_canonical_v2_move,
        legacy_flat_action_text,
        legacy_flat_dialogue_text,
    )

    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if is_canonical_v2_move(move):
        a = legacy_flat_action_text(move)
        d = legacy_flat_dialogue_text(move)
    else:
        a = str(move.get("action", "") or "")
        d = str(move.get("dialogue", "") or "")
    text = " ".join(
        [
            a,
            d,
            str(motivation.get("goal", "") or ""),
            str(motivation.get("tactic", "") or ""),
        ]
    )
    return issue_tokens_fn(text)


def event_tokens(*, event: PublicEvent, issue_tokens_fn) -> set[str]:
    return issue_tokens_fn(event.summary)


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

    tension_shift = _clean_text(director_decision.get("tension_shift", "")).lower()
    pressure_profile = _build_turn_pressure_profile(
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


REQUIRED_NEXT_STEP_PLATEAU_FIRE_STREAK = 2

REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE = (
    "Someone must break the stalemate with a binding act: commit, refuse with consequence, "
    "or change the physical situation."
)

_PLATEAU_COUNTED_TRANSITIONS = frozenset({"advanced", "escalated"})


def _normalize_required_next_step_key(value: Any) -> str:
    return " ".join(_clean_text(value).lower().split())


def apply_mixed_transition_plateau_refresh(
    *,
    issue: IssueState,
    transition: str,
    turn_profile: dict[str, Any],
    current_turn_index: int,
) -> None:
    """Refresh ``required_next_step`` after repeated counted transitions with frozen obligation text.

    Counted transitions: ``advanced``, ``escalated``. Fires when streak ≥ threshold, normalized
    ``required_next_step`` unchanged across consecutive counted updates, and at least one
    ``advanced`` occurred in the current streak window.

    Does not alter status, ``last_change``, ``status_reason``, or consequence tags.
    """
    if transition not in _PLATEAU_COUNTED_TRANSITIONS:
        issue.required_next_step_plateau_streak = 0
        issue.required_next_step_plateau_has_advanced = False
        return

    norm = _normalize_required_next_step_key(issue.required_next_step)
    prev_t = issue.required_next_step_plateau_last_turn_index
    prev_norm = issue.required_next_step_plateau_last_norm

    consecutive = prev_t is not None and int(current_turn_index) == int(prev_t) + 1
    same_norm = bool(prev_norm) and norm == prev_norm

    if not consecutive or not same_norm:
        issue.required_next_step_plateau_streak = 1
        issue.required_next_step_plateau_last_norm = norm
        issue.required_next_step_plateau_last_turn_index = int(current_turn_index)
        issue.required_next_step_plateau_has_advanced = transition == "advanced"
    else:
        issue.required_next_step_plateau_streak = (
            int(issue.required_next_step_plateau_streak) + 1
        )
        issue.required_next_step_plateau_last_turn_index = int(current_turn_index)
        if transition == "advanced":
            issue.required_next_step_plateau_has_advanced = True

    if (
        issue.required_next_step_plateau_streak < REQUIRED_NEXT_STEP_PLATEAU_FIRE_STREAK
        or not issue.required_next_step_plateau_has_advanced
    ):
        return

    stale = issue.required_next_step
    fresh = _clean_text(turn_profile.get("required_next_step", ""))
    if fresh and _normalize_required_next_step_key(fresh) != _normalize_required_next_step_key(
        stale
    ):
        issue.required_next_step = fresh
    else:
        issue.required_next_step = REQUIRED_NEXT_STEP_PLATEAU_ESCALATION_TEMPLATE

    issue.required_next_step_plateau_streak = 0
    issue.required_next_step_plateau_has_advanced = False
    issue.required_next_step_plateau_last_norm = _normalize_required_next_step_key(
        issue.required_next_step
    )
    issue.required_next_step_plateau_last_turn_index = int(current_turn_index)


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

    updated_issue_ids: set[str] = set()
    current_turn_index = manager.turn_counter + 1
    matched_terms = turn_tokens_fn(move)
    timestamp = event.timestamp if event is not None else datetime.now(timezone.utc)
    turn_profile = _build_turn_pressure_profile(
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
        match_score = _pressure_match_score(
            turn_profile=turn_profile,
            issue_profile=issue_profile,
            issue_tokens_fn=issue_tokens_fn,
        )
        signal_match = _matches_issue_signals(
            issue, source_text, resolution=False
        ) or _matches_issue_signals(issue, source_text, resolution=True)
        if match_score >= 4 or signal_match:
            transition = _determine_issue_transition(
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


PRESSURE_KIND_CONTROL = "control_conflict"
PRESSURE_KIND_ACCESS = "access_conflict"
PRESSURE_KIND_PRESENCE = "presence_conflict"
PRESSURE_KIND_PLAN = "plan_execution"
PRESSURE_KIND_INFORMATION = "information_gap"
PRESSURE_KIND_SAFETY = "safety_risk"

CONTROL_CONSEQUENCE_TAGS = {
    "authority_asserted",
    "authority_challenged",
    "mediation_attempted",
    "interception",
}
ACCESS_CONSEQUENCE_TAGS = {"access_denied", "access_granted"}
PRESENCE_CONSEQUENCE_TAGS = {
    "arrival",
    "exit",
    "repositioning",
    "territorial_claim",
    "territorial_denial",
}
PLAN_CONSEQUENCE_TAGS = {
    "refusal",
    "agreement",
    "commitment",
    "decision_made",
    "plan_committed",
    "dependency_advanced",
}
INFORMATION_CONSEQUENCE_TAGS = {"revelation", "concealment"}
CONTESTED_PRESENCE_TAGS = {
    "territorial_claim",
    "territorial_denial",
    "authority_asserted",
    "authority_challenged",
    "access_denied",
    "escalation",
}

CONTROL_TEXT_MARKERS = (
    "control",
    "authority",
    "command",
    "order",
    "submit",
    "defy",
    "challenge",
    "accus",
    "dominan",
)
ACCESS_TEXT_MARKERS = (
    "access",
    "permission",
    "allow",
    "blocked",
    "denied",
    "entry",
    "gate",
)
PRESENCE_TEXT_MARKERS = (
    "stay",
    "remain",
    "leave",
    "enter",
    "arrival",
    "exit",
    "presence",
    "position",
    "space",
)
PLAN_TEXT_MARKERS = (
    "plan",
    "decision",
    "offer",
    "deal",
    "course",
    "agree",
    "accept",
    "refuse",
    "commit",
    "obligation",
    "next step",
)
INFORMATION_TEXT_MARKERS = (
    "truth",
    "answer",
    "explain",
    "reveal",
    "conceal",
    "confess",
    "clarify",
    "whether",
    "know",
)
SAFETY_TEXT_MARKERS = (
    "injur",
    "wound",
    "bleed",
    "safe",
    "safety",
    "stabil",
    "protective step",
    "exposure",
    "pain",
    "collapse",
    "responsive",
    "tracked",
    "danger",
    "threat",
)
PLAN_COMPLETION_TEXT_MARKERS = (
    "completed",
    "finished",
    "done",
    "settled",
    "carried out",
    "secured",
)
SAFETY_SETTLED_TEXT_MARKERS = (
    "stable",
    "stabilized",
    "responsive",
    "safe for now",
    "breathing steady",
    "bleeding stopped",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_strings(values: list[str]) -> list[str]:
    return [
        item for item in dict.fromkeys(_clean_text(value) for value in values) if item
    ]


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _issue_source_text(
    *,
    move: dict[str, Any],
    state_changes: list[str],
    actionable_implications: list[str],
    event: Optional[PublicEvent],
) -> str:
    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if not isinstance(motivation, dict):
        motivation = {}
    values = [
        _clean_text(move.get("action", "")),
        _clean_text(move.get("dialogue", "")),
        _clean_text(motivation.get("goal", "")),
        _clean_text(motivation.get("tactic", "")),
        *[_clean_text(item) for item in state_changes],
        *[_clean_text(item) for item in actionable_implications],
    ]
    if event is not None:
        values.append(_clean_text(event.summary))
    return " ".join(value for value in values if value)


def _extract_issue_participants(
    *, manager: Any, acting_character: str, move: dict[str, Any]
) -> list[str]:
    if manager.scene_state is None:
        return [acting_character]
    present = [
        _clean_text(item)
        for item in manager.scene_state.present_characters
        if _clean_text(item)
    ]
    if not present:
        return [acting_character]

    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if not isinstance(motivation, dict):
        motivation = {}
    combined = " ".join(
        [
            _clean_text(move.get("action", "")),
            _clean_text(move.get("dialogue", "")),
            _clean_text(motivation.get("goal", "")),
            _clean_text(motivation.get("tactic", "")),
        ]
    ).lower()

    participants = [acting_character]
    for name in present:
        if name == acting_character:
            continue
        if re.search(rf"\b{re.escape(name.lower())}\b", combined):
            participants.append(name)

    if len(participants) == 1:
        return present[:] if len(present) <= 3 else [acting_character]
    return _dedupe_strings(participants)


def _infer_pressure_kind(*, consequence_tags: set[str], source_text: str) -> str:
    tags = {str(item).strip().lower() for item in consequence_tags if _clean_text(item)}
    lowered = source_text.lower()

    if _contains_any(
        lowered, ("establish whether", "determine whether", "clarify whether")
    ):
        return PRESSURE_KIND_INFORMATION
    if tags.intersection(INFORMATION_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_INFORMATION
    if _contains_any(lowered, SAFETY_TEXT_MARKERS):
        return PRESSURE_KIND_SAFETY
    if tags.intersection(ACCESS_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_ACCESS
    if tags.intersection(CONTROL_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_CONTROL
    if tags.intersection(PRESENCE_CONSEQUENCE_TAGS) and (
        tags.intersection(CONTESTED_PRESENCE_TAGS)
        or _contains_any(lowered, CONTROL_TEXT_MARKERS + ACCESS_TEXT_MARKERS)
    ):
        return PRESSURE_KIND_PRESENCE
    if tags.intersection(PLAN_CONSEQUENCE_TAGS):
        return PRESSURE_KIND_PLAN
    if _contains_any(lowered, ACCESS_TEXT_MARKERS):
        return PRESSURE_KIND_ACCESS
    if _contains_any(lowered, CONTROL_TEXT_MARKERS):
        return PRESSURE_KIND_CONTROL
    if _contains_any(lowered, PRESENCE_TEXT_MARKERS) and _contains_any(
        lowered, CONTROL_TEXT_MARKERS + ACCESS_TEXT_MARKERS
    ):
        return PRESSURE_KIND_PRESENCE
    if _contains_any(lowered, PLAN_TEXT_MARKERS):
        return PRESSURE_KIND_PLAN
    if _contains_any(lowered, INFORMATION_TEXT_MARKERS):
        return PRESSURE_KIND_INFORMATION
    return ""


def _default_blocked_what(pressure_kind: str) -> str:
    if pressure_kind == PRESSURE_KIND_CONTROL:
        return "Clear control of the immediate interaction"
    if pressure_kind == PRESSURE_KIND_ACCESS:
        return "Access to the relevant person, place, or action"
    if pressure_kind == PRESSURE_KIND_PRESENCE:
        return "Stable presence or positioning in the scene"
    if pressure_kind == PRESSURE_KIND_PLAN:
        return "Progress on the current decision or obligation"
    if pressure_kind == PRESSURE_KIND_INFORMATION:
        return "Confidence about what is true and what can be done next"
    if pressure_kind == PRESSURE_KIND_SAFETY:
        return "Immediate safety and room to act without worsening danger"
    return "Unresolved scene pressure"


def _derive_blocked_what(
    *, pressure_kind: str, candidate_description: str, source_text: str
) -> str:
    if pressure_kind == PRESSURE_KIND_INFORMATION and candidate_description:
        return candidate_description.rstrip(".")
    if pressure_kind == PRESSURE_KIND_PLAN:
        lowered = source_text.lower()
        if "refus" in lowered or "reject" in lowered:
            return "The current proposed course of action"
        if any(token in lowered for token in ("agree", "accept", "commit")):
            return "Execution of the newly agreed course of action"
    return _default_blocked_what(pressure_kind)


def _default_required_next_step(pressure_kind: str) -> str:
    if pressure_kind == PRESSURE_KIND_CONTROL:
        return "The challenged party must respond, yield, or reassert control."
    if pressure_kind == PRESSURE_KIND_ACCESS:
        return "Someone must grant access, apply leverage, or choose another route."
    if pressure_kind == PRESSURE_KIND_PRESENCE:
        return "The cast must settle who can remain, move, or take space."
    if pressure_kind == PRESSURE_KIND_PLAN:
        return "Someone must decide the next move or carry the obligation forward."
    if pressure_kind == PRESSURE_KIND_INFORMATION:
        return "Someone must clarify the uncertainty or act on the new information."
    if pressure_kind == PRESSURE_KIND_SAFETY:
        return "The cast must reduce the immediate risk or choose the safest next step."
    return "A concrete next move is still required."


def _default_escalation_signals(
    pressure_kind: str, consequence_tags: set[str]
) -> list[str]:
    defaults = {
        PRESSURE_KIND_CONTROL: ["challenge", "defy", "command", "authority"],
        PRESSURE_KIND_ACCESS: ["deny", "block", "refuse access", "locked"],
        PRESSURE_KIND_PRESENCE: ["leave", "stay", "move", "territory"],
        PRESSURE_KIND_PLAN: ["refuse", "delay", "block", "demand"],
        PRESSURE_KIND_INFORMATION: ["conceal", "evade", "withhold", "unclear"],
        PRESSURE_KIND_SAFETY: ["danger", "risk", "worse", "threat"],
    }
    return sorted(
        {
            *[str(item).strip() for item in consequence_tags if _clean_text(item)],
            *defaults.get(pressure_kind, []),
            "pressure",
        }
    )


def _default_resolution_signals(pressure_kind: str) -> list[str]:
    defaults = {
        PRESSURE_KIND_CONTROL: ["yield", "agree", "settled"],
        PRESSURE_KIND_ACCESS: ["allow", "open", "granted"],
        PRESSURE_KIND_PRESENCE: ["settled", "left", "remained"],
        PRESSURE_KIND_PLAN: ["completed", "done", "carried out"],
        PRESSURE_KIND_INFORMATION: ["answer", "clarified", "revealed"],
        PRESSURE_KIND_SAFETY: ["stable", "safe for now", "secured"],
    }
    return defaults.get(pressure_kind, [])


def _build_pressure_description(*, blocked_what: str, required_next_step: str) -> str:
    description = _clean_text(blocked_what) or "Unresolved scene pressure"
    if description[-1:] not in ".!?":
        description += "."
    if required_next_step and required_next_step.lower() not in description.lower():
        description += f" Required next move: {required_next_step}"
    return description


def _build_turn_pressure_profile(
    *,
    manager: Any,
    acting_character: str,
    move: dict[str, Any],
    event: Optional[PublicEvent],
    consequence_tags: set[str],
    state_changes: list[str],
    actionable_implications: list[str],
) -> dict[str, Any]:
    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if not isinstance(motivation, dict):
        motivation = {}
    candidate_description = (
        next((item for item in state_changes if _clean_text(item)), "")
        or _clean_text(motivation.get("goal", ""))
        or _clean_text(move.get("dialogue", ""))[:160]
        or _clean_text(move.get("action", ""))[:160]
    )
    source_text = _issue_source_text(
        move=move,
        state_changes=state_changes,
        actionable_implications=actionable_implications,
        event=event,
    )
    pressure_kind = _infer_pressure_kind(
        consequence_tags=consequence_tags,
        source_text=source_text,
    )
    blocked_what = _derive_blocked_what(
        pressure_kind=pressure_kind,
        candidate_description=candidate_description,
        source_text=source_text,
    )
    required_next_step = next(
        (item for item in actionable_implications if _clean_text(item)), ""
    ) or _default_required_next_step(pressure_kind)
    last_change = (
        next((item for item in state_changes if _clean_text(item)), "")
        or _clean_text(event.summary if event is not None else "")
        or candidate_description
    )
    participants = _extract_issue_participants(
        manager=manager,
        acting_character=acting_character,
        move=move,
    )
    should_track = bool(
        pressure_kind
        and (
            candidate_description
            or state_changes
            or actionable_implications
            or consequence_tags
        )
    )
    return {
        "pressure_kind": pressure_kind,
        "blocked_what": blocked_what,
        "blocked_characters": participants[:],
        "last_change": last_change,
        "required_next_step": required_next_step,
        "description": _build_pressure_description(
            blocked_what=blocked_what,
            required_next_step=required_next_step,
        ),
        "participants": participants,
        "should_track": should_track,
        "source_text": source_text,
    }


def _build_issue_profile_from_issue(issue: IssueState) -> dict[str, Any]:
    source_text = " ".join(
        value
        for value in [
            _clean_text(issue.description),
            _clean_text(issue.status_reason),
            *[_clean_text(item) for item in issue.escalation_signals],
            *[_clean_text(item) for item in issue.resolution_signals],
        ]
        if value
    )
    pressure_kind = issue.pressure_kind or _infer_pressure_kind(
        consequence_tags=set(),
        source_text=source_text,
    )
    blocked_what = (
        _clean_text(issue.blocked_what)
        or _clean_text(issue.description)
        or _default_blocked_what(pressure_kind)
    )
    required_next_step = _clean_text(
        issue.required_next_step
    ) or _default_required_next_step(pressure_kind)
    return {
        "pressure_kind": pressure_kind,
        "blocked_what": blocked_what,
        "blocked_characters": issue.blocked_characters[:] or issue.participants[:],
        "last_change": _clean_text(issue.last_change)
        or _clean_text(issue.status_reason),
        "required_next_step": required_next_step,
        "description": _clean_text(issue.description)
        or _build_pressure_description(
            blocked_what=blocked_what,
            required_next_step=required_next_step,
        ),
        "participants": issue.participants[:],
    }


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


def _should_resolve_issue(
    *,
    issue_profile: dict[str, Any],
    turn_profile: dict[str, Any],
    issue: IssueState,
    consequence_tags: set[str],
    source_text: str,
) -> bool:
    if _matches_issue_signals(issue, source_text, resolution=True):
        return True

    pressure_kind = issue_profile.get("pressure_kind", "")
    tags = {str(item).strip().lower() for item in consequence_tags if _clean_text(item)}
    if pressure_kind == PRESSURE_KIND_ACCESS and "access_granted" in tags:
        return True
    if (
        pressure_kind == PRESSURE_KIND_INFORMATION
        and "revelation" in tags
        and "concealment" not in tags
        and _contains_any(source_text, ("answer", "clarif", "explain", "reveal"))
    ):
        return True
    if pressure_kind == PRESSURE_KIND_PLAN and _contains_any(
        source_text, PLAN_COMPLETION_TEXT_MARKERS
    ):
        return True
    if pressure_kind == PRESSURE_KIND_SAFETY and _contains_any(
        source_text, SAFETY_SETTLED_TEXT_MARKERS
    ):
        return True
    return False


def _determine_issue_transition(
    *,
    issue_profile: dict[str, Any],
    turn_profile: dict[str, Any],
    issue: IssueState,
    consequence_tags: set[str],
    source_text: str,
) -> str:
    if _should_resolve_issue(
        issue_profile=issue_profile,
        turn_profile=turn_profile,
        issue=issue,
        consequence_tags=consequence_tags,
        source_text=source_text,
    ):
        return "resolved"
    if _matches_issue_signals(issue, source_text, resolution=False):
        return "escalated"

    pressure_kind = issue_profile.get("pressure_kind", "")
    tags = {str(item).strip().lower() for item in consequence_tags if _clean_text(item)}
    if pressure_kind == PRESSURE_KIND_CONTROL and tags.intersection(
        CONTROL_CONSEQUENCE_TAGS
    ):
        return "escalated"
    if pressure_kind == PRESSURE_KIND_ACCESS and "access_denied" in tags:
        return "escalated"
    if pressure_kind == PRESSURE_KIND_PRESENCE and tags.intersection(
        CONTESTED_PRESENCE_TAGS
    ):
        return "escalated"
    if pressure_kind == PRESSURE_KIND_SAFETY and _contains_any(
        source_text, SAFETY_TEXT_MARKERS
    ):
        return "escalated"
    if pressure_kind == PRESSURE_KIND_PLAN and tags.intersection(
        {"agreement", "commitment"}
    ):
        return "narrowed"
    return "advanced"


def _build_status_reason(
    *, transition: str, issue_profile: dict[str, Any], turn_profile: dict[str, Any]
) -> str:
    pressure_kind = str(
        issue_profile.get("pressure_kind", "") or "scene pressure"
    ).replace("_", " ")
    last_change = (
        _clean_text(turn_profile.get("last_change", ""))
        or "This turn materially changed the pressure"
    )
    required_next_step = _clean_text(
        turn_profile.get("required_next_step", "")
        or issue_profile.get("required_next_step", "")
    )
    if transition == "resolved":
        return f"{last_change} resolved the {pressure_kind}; no immediate blocking step remains."
    if transition == "escalated":
        if required_next_step:
            return f"{last_change} escalated the {pressure_kind}; {required_next_step}"
        return f"{last_change} escalated the {pressure_kind}."
    if transition == "narrowed":
        if required_next_step:
            return f"{last_change} narrowed the {pressure_kind}; {required_next_step}"
        return f"{last_change} narrowed the {pressure_kind}."
    if required_next_step:
        return f"{last_change} advanced the {pressure_kind}; {required_next_step}"
    return f"{last_change} advanced the {pressure_kind}."

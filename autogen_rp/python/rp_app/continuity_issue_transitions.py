"""Issue transition determination and required-next-step plateau refresh."""

from __future__ import annotations

from typing import Any

from continuity_issue_matching import _matches_issue_signals
from continuity_issue_pressure import (
    _clean_text,
    _contains_any,
    CONTROL_CONSEQUENCE_TAGS,
    CONTESTED_PRESENCE_TAGS,
    INFORMATION_CONSEQUENCE_TAGS,
    PLAN_COMPLETION_TEXT_MARKERS,
    PRESSURE_KIND_ACCESS,
    PRESSURE_KIND_CONTROL,
    PRESSURE_KIND_INFORMATION,
    PRESSURE_KIND_PLAN,
    PRESSURE_KIND_PRESENCE,
    PRESSURE_KIND_SAFETY,
    SAFETY_SETTLED_TEXT_MARKERS,
    SAFETY_TEXT_MARKERS,
)
from continuity_state import IssueState

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

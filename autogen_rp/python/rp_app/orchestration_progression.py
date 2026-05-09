"""Progression bands, HIGH tie-break, Director override (Issue #164)."""

from __future__ import annotations

from typing import Any, Literal


def _is_actionable_issue_status(status: str) -> bool:
    status_clean = str(status or "").strip().lower()
    return status_clean in {"active", "escalating"}


def _get_actor_issue_statuses(
    *, actor: str, active_issues: list[dict[str, Any]]
) -> set[str]:
    statuses: set[str] = set()
    for issue in active_issues:
        participants = issue.get("participants", [])
        if not isinstance(participants, list) or actor not in participants:
            continue
        statuses.add(str(issue.get("status", "") or "").strip().lower())
    return statuses


def _actor_has_interaction_density(
    *, actor: str, active_issues: list[dict[str, Any]], available_actors: list[str]
) -> bool:
    available_set = set(available_actors)
    for issue in active_issues:
        status = str(issue.get("status", "") or "").strip().lower()
        if not _is_actionable_issue_status(status):
            continue
        participants = issue.get("participants", [])
        if not isinstance(participants, list) or actor not in participants:
            continue
        overlap = [name for name in participants if name in available_set]
        if len(overlap) >= 2:
            return True
    return False


def _find_last_move_for_actor(
    *, recent_structured_moves: list[dict[str, Any]], actor: str
) -> dict[str, Any] | None:
    for item in reversed(recent_structured_moves):
        if not isinstance(item, dict):
            continue
        if str(item.get("speaker", "") or "").strip() == actor:
            return item
    return None


def _extract_outcome_list(
    *, last_move: dict[str, Any] | None, field: str
) -> list[Any] | None:
    if last_move is None or field not in last_move:
        return None
    value = last_move.get(field)
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    return value


def _has_momentum_signal(
    *, last_move: dict[str, Any] | None
) -> bool | None:
    """Return True/False when outcome data is present; None when unknown.

    Required safeguard: if fields are missing, treat momentum as neutral.
    """

    consequences = _extract_outcome_list(last_move=last_move, field="consequences")
    issue_updates = _extract_outcome_list(last_move=last_move, field="issue_updates")
    presence_changes = _extract_outcome_list(last_move=last_move, field="presence_changes")
    if consequences is None and issue_updates is None and presence_changes is None:
        return None
    return bool(consequences or issue_updates or presence_changes)


def _has_weak_repetition_signal(
    *, last_move: dict[str, Any] | None
) -> bool | None:
    """Return True/False when outcome data is complete; None when unknown.

    Weak repetition signal requires all three fields present and empty.
    Missing fields must be treated as neutral.
    """

    consequences = _extract_outcome_list(last_move=last_move, field="consequences")
    issue_updates = _extract_outcome_list(last_move=last_move, field="issue_updates")
    presence_changes = _extract_outcome_list(last_move=last_move, field="presence_changes")
    if consequences is None or issue_updates is None or presence_changes is None:
        return None
    return not consequences and not issue_updates and not presence_changes


def assign_progression_band_for_actor(
    *,
    actor: str,
    available_actors: list[str],
    active_issues: list[dict[str, Any]],
    recent_structured_moves: list[dict[str, Any]],
) -> Literal["high", "med", "low"]:
    """Assign HIGH/MED/LOW using only approved structural signals.

    Momentum and weak repetition signals must be neutral when outcome fields are missing.
    """

    actor = str(actor or "").strip()
    if not actor:
        return "med"

    statuses = _get_actor_issue_statuses(actor=actor, active_issues=active_issues)
    in_escalating = "escalating" in statuses
    in_active = "active" in statuses
    in_actionable = in_escalating or in_active

    last_move = _find_last_move_for_actor(
        recent_structured_moves=recent_structured_moves,
        actor=actor,
    )
    momentum_signal = _has_momentum_signal(last_move=last_move)
    repetition_signal = _has_weak_repetition_signal(last_move=last_move)

    has_interaction_density = _actor_has_interaction_density(
        actor=actor,
        active_issues=active_issues,
        available_actors=available_actors,
    )

    has_momentum = bool(momentum_signal) and in_actionable

    if in_escalating or (in_active and has_interaction_density) or (in_active and has_momentum):
        return "high"

    if not in_actionable and repetition_signal is True:
        return "low"

    return "med"


def _escalating_issue_participants(active_issues: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for issue in active_issues:
        if not isinstance(issue, dict):
            continue
        if str(issue.get("status", "") or "").strip().lower() != "escalating":
            continue
        participants = issue.get("participants", [])
        if isinstance(participants, list):
            out.update(str(item) for item in participants if str(item).strip())
    return out


def _restrict_high_to_escalating_subset_if_any(
    *,
    high_actors: list[str],
    active_issues: list[dict[str, Any]],
) -> list[str]:
    """Option 1: if any HIGH participates in escalating issues, narrow to that subset."""
    escalating = _escalating_issue_participants(active_issues)
    restricted = [a for a in high_actors if a in escalating]
    return restricted if restricted else list(high_actors)


def _prev_spotlight_expel_proxy(
    *,
    spotlight_history: list[str],
    recent_structured_moves: list[dict[str, Any]],
) -> str | None:
    """Speaker to deprioritize for 'not previous speaker' tie-break (Stage A)."""
    if spotlight_history:
        s = str(spotlight_history[-1] or "").strip()
        return s or None
    if recent_structured_moves:
        last = recent_structured_moves[-1]
        if isinstance(last, dict):
            sp = str(last.get("speaker", "") or "").strip()
            return sp or None
    return None


def _last_spotlight_index(actor: str, spotlight_history: list[str]) -> int | None:
    for i in range(len(spotlight_history) - 1, -1, -1):
        if spotlight_history[i] == actor:
            return i
    return None


def _least_recent_spotlight_actor(
    candidates: list[str],
    *,
    spotlight_history: list[str],
    available_actors: list[str],
) -> str:
    """Prefer never spotlighted, then smallest last index in history, then list order."""

    def sort_key(name: str) -> tuple[int, int, int]:
        li = _last_spotlight_index(name, spotlight_history)
        try:
            av_idx = available_actors.index(name)
        except ValueError:
            av_idx = len(available_actors)
        if li is None:
            return (0, 0, av_idx)
        return (1, li, av_idx)

    return min(candidates, key=sort_key)


def _pick_high_progression_actor_once(
    *,
    candidate_high_list: list[str],
    director_selected_actor: str,
    spotlight_history: list[str],
    recent_structured_moves: list[dict[str, Any]],
    available_actors: list[str],
) -> str:
    """Single pass: director preference, expel proxy, least-recent spotlight, list order."""
    if not candidate_high_list:
        return ""

    if director_selected_actor in candidate_high_list:
        return director_selected_actor

    expel = _prev_spotlight_expel_proxy(
        spotlight_history=spotlight_history,
        recent_structured_moves=recent_structured_moves,
    )
    pool = candidate_high_list
    if expel:
        without = [a for a in candidate_high_list if a != expel]
        if without:
            pool = without

    return _least_recent_spotlight_actor(
        pool,
        spotlight_history=spotlight_history,
        available_actors=available_actors,
    )


def _pick_high_progression_actor(
    *,
    full_high_list: list[str],
    director_selected_actor: str,
    spotlight_history: list[str],
    recent_structured_moves: list[dict[str, Any]],
    available_actors: list[str],
    active_issues: list[dict[str, Any]],
) -> str:
    """Escalating subset first, then tie-break policy and narrow anti-loop guard."""
    working = _restrict_high_to_escalating_subset_if_any(
        high_actors=full_high_list,
        active_issues=active_issues,
    )
    chosen = _pick_high_progression_actor_once(
        candidate_high_list=working,
        director_selected_actor=director_selected_actor,
        spotlight_history=spotlight_history,
        recent_structured_moves=recent_structured_moves,
        available_actors=available_actors,
    )

    prev_spot = (
        str(spotlight_history[-1] or "").strip()
        if spotlight_history
        else ""
    )
    if (
        prev_spot
        and chosen == prev_spot
        and len(full_high_list) >= 2
    ):
        rerun_high = [a for a in full_high_list if a != prev_spot]
        if len(rerun_high) >= 1:
            working2 = _restrict_high_to_escalating_subset_if_any(
                high_actors=rerun_high,
                active_issues=active_issues,
            )
            if working2:
                chosen = _pick_high_progression_actor_once(
                    candidate_high_list=working2,
                    director_selected_actor=director_selected_actor,
                    spotlight_history=spotlight_history,
                    recent_structured_moves=recent_structured_moves,
                    available_actors=available_actors,
                )

    return chosen


def resolve_progression_override_actor(
    *,
    director_selected_actor: str,
    available_actors: list[str],
    active_issues: list[dict[str, Any]],
    recent_structured_moves: list[dict[str, Any]],
    spotlight_history: list[str] | None = None,
    progression_enforcement_gate: bool = False,
) -> str | None:
    """Apply band-based progression override for Director selection.

    When ``progression_enforcement_gate`` is False (default):
    - Override ONLY if Director pick is LOW, another actor is HIGH, and an
      actionable issue exists.

    When gate is True (beat-shift pending or high progression pressure):
    - Preserve the explicit MED branch, but return no override for MED picks.
    """

    director_selected_actor = str(director_selected_actor or "").strip()
    if not director_selected_actor or director_selected_actor not in available_actors:
        return None

    sh = [str(x or "").strip() for x in (spotlight_history or []) if str(x or "").strip()]

    unresolved_actionable_issue_exists = any(
        _is_actionable_issue_status(str(issue.get("status", "") or ""))
        for issue in active_issues
        if isinstance(issue, dict)
    )
    if not unresolved_actionable_issue_exists:
        return None

    bands: dict[str, Literal["high", "med", "low"]] = {}
    for actor in available_actors:
        bands[actor] = assign_progression_band_for_actor(
            actor=actor,
            available_actors=available_actors,
            active_issues=active_issues,
            recent_structured_moves=recent_structured_moves,
        )

    director_band = bands.get(director_selected_actor)
    high_actors = [actor for actor in available_actors if bands.get(actor) == "high"]
    if not high_actors:
        return None

    if director_band == "low":
        return _pick_high_progression_actor(
            full_high_list=high_actors,
            director_selected_actor=director_selected_actor,
            spotlight_history=sh,
            recent_structured_moves=recent_structured_moves,
            available_actors=available_actors,
            active_issues=active_issues,
        )

    if progression_enforcement_gate and director_band == "med":
        return None

    return None

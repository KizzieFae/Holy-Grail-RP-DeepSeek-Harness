"""Spotlight, fairness rotation, fallback chooser (Issue #164)."""

from __future__ import annotations

from typing import Any


def choose_fallback_actor(
    available_actors: list[str],
    forced_speaker: str | None,
    spotlight_history: list[str],
    *,
    prefer_continuing_spotlight: bool = False,
) -> str | None:
    if forced_speaker in available_actors:
        return str(forced_speaker)

    if not available_actors:
        return None

    if prefer_continuing_spotlight and spotlight_history:
        last = str(spotlight_history[-1] or "")
        if last in available_actors:
            return last

    last_actor = spotlight_history[-1] if spotlight_history else None
    for participant in available_actors:
        if participant != last_actor:
            return participant
    return available_actors[0]


def first_unheard_available_actor_this_round(
    *,
    participant_names: list[str],
    available_actors: list[str],
    actors_used_this_round: list[str],
) -> str | None:
    """First cast member in *participant_names* who may act but has not this round."""
    avail = {str(a) for a in available_actors if str(a or "").strip()}
    for name in participant_names:
        key = str(name or "").strip()
        if key in avail and actors_used_this_round.count(key) == 0:
            return key
    return None


def apply_participation_fairness_to_decision(
    decision: dict[str, Any],
    *,
    participant_names: list[str],
    available_actors: list[str],
    actors_used_this_round: list[str],
) -> tuple[bool, str | None]:
    """If the chosen actor already spoke this round while another available actor has not, rotate.

    Mutates *decision* **next_actor only** — operator-facing reason assembly is centralized
    in ``director_reason_projection.merge_participation_fairness_reason`` (GitHub #210 C-A).

    Returns ``(fairness_rotated, unheard_actor_key)`` — *unheard_actor_key* is ``None`` when no
    fairness rotation applies.
    """
    if bool(decision.get("end_round")):
        return False, None
    na = str(decision.get("next_actor") or "").strip()
    if not na or not available_actors:
        return False, None
    unheard = first_unheard_available_actor_this_round(
        participant_names=participant_names,
        available_actors=available_actors,
        actors_used_this_round=actors_used_this_round,
    )
    if not unheard or actors_used_this_round.count(na) == 0 or na == unheard:
        return False, None
    decision["next_actor"] = unheard
    return True, unheard

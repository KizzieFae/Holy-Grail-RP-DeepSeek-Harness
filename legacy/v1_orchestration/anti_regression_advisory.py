"""Anti-regression advisory: reduce immediate return to the same two-actor ping-pong after a break.

Advisory only; orchestration-level keys. Trigger (option A): ping_pong AND (post_break_window OR
low_player_agency). Does not OR in high stall_score (progression advisory owns that).
"""

from __future__ import annotations

import logging
from typing import Any

from progression_advisory import STALL_BEAT_SHIFT_THRESHOLD

logger = logging.getLogger("rp_app.anti_regression_advisory")

_CACHE_KEY = "_anti_regression_advisory_cache"
_TICKS_KEY = "_anti_regression_post_break_ticks"
_PREV_STALL_KEY = "_anti_regression_prev_stall_score"

POST_BREAK_WINDOW_TICKS = 3
PING_PONG_LEN = 4
STRUCTURED_MOVE_WINDOW_K = 8
PLAYER_SPEAK_THRESHOLD_M = 2
STALL_LOW_CROSS = 0.3
_MIN_MOVES_FOR_AGENCY = 4


def arm_post_break_window(orchestration_state: dict[str, Any]) -> None:
    """Start or extend post-break window (e.g. after beat-shift consumption)."""
    cur = int(orchestration_state.get(_TICKS_KEY) or 0)
    orchestration_state[_TICKS_KEY] = max(cur, POST_BREAK_WINDOW_TICKS)
    logger.info(
        "[anti_regression] post_break window armed ticks=%s",
        orchestration_state[_TICKS_KEY],
    )


def _maybe_arm_post_break_from_stall_cross(
    orchestration_state: dict[str, Any], current_stall: float
) -> None:
    prev = orchestration_state.get(_PREV_STALL_KEY)
    if not isinstance(prev, (int, float)):
        return
    p = float(prev)
    c = float(current_stall)
    if p >= STALL_BEAT_SHIFT_THRESHOLD and c < STALL_LOW_CROSS:
        cur = int(orchestration_state.get(_TICKS_KEY) or 0)
        orchestration_state[_TICKS_KEY] = max(cur, POST_BREAK_WINDOW_TICKS)
        logger.info(
            "[anti_regression] post_break window armed from stall cross %.4f -> %.4f",
            p,
            c,
        )


def detect_ping_pong_pair(
    director_decisions: list[dict[str, Any]],
) -> tuple[bool, str, str]:
    """True if last four next_actor values are strictly A, B, A, B with A != B."""
    if len(director_decisions) < PING_PONG_LEN:
        return False, "", ""
    tail = director_decisions[-PING_PONG_LEN:]
    actors: list[str] = []
    for d in tail:
        if not isinstance(d, dict):
            return False, "", ""
        actors.append(str(d.get("next_actor", "") or "").strip())
    if not all(actors):
        return False, "", ""
    a, b, c, d = actors
    if a == b or a != c or b != d:
        return False, "", ""
    return True, a, b


def player_speaker_labels(
    session_state: dict[str, Any], participant_names: list[str]
) -> set[str]:
    names = {str(n).strip() for n in participant_names if str(n).strip()}
    out: set[str] = set()
    for key in ("player_character", "user_name"):
        raw = session_state.get(key)
        if isinstance(raw, str) and raw.strip() and raw.strip() in names:
            out.add(raw.strip())
    return out


def low_player_agency(
    recent_structured_moves: list[dict[str, Any]],
    player_labels: set[str],
) -> bool:
    if not player_labels:
        return False
    tail = [
        m
        for m in recent_structured_moves[-STRUCTURED_MOVE_WINDOW_K:]
        if isinstance(m, dict)
    ]
    if len(tail) < _MIN_MOVES_FOR_AGENCY:
        return False
    count = 0
    for m in tail:
        sp = str(m.get("speaker", "") or "").strip()
        if sp in player_labels:
            count += 1
    return count < PLAYER_SPEAK_THRESHOLD_M


def build_anti_regression_director_prefix(
    *,
    actor_a: str,
    actor_b: str,
    player_labels: set[str],
    low_agency: bool,
) -> str:
    def h(x: str) -> str:
        return str(x or "").replace("_", " ").strip() or x

    ha, hb = h(actor_a), h(actor_b)
    if low_agency and player_labels:
        names = ", ".join(sorted(h(p) for p in player_labels))
        positive = (
            f"giving the player-controlled character ({names}) a meaningful beat "
            "(reaction, choice, or focal action) when eligible"
        )
    else:
        positive = (
            "a different focal actor or beat type (environment, procedure, or completing "
            "the last non-dialogue action) when available_next_actors allows"
        )
    return (
        "ANTI-REGRESSION (ADVISORY):\n"
        f"Recent selections alternate strictly between {ha} and {hb}. Do not immediately "
        f"resume that same two-actor ping-pong unless strongly justified.\n"
        f"Prefer instead {positive}.\n\n"
    )


def refresh_anti_regression_advisory_cache(
    *,
    orchestration_state: dict[str, Any],
    progression_advisory: dict[str, Any],
    session_state: dict[str, Any],
    participant_names: list[str],
) -> dict[str, Any]:
    """Arm post-break from stall cross, compute flags, optionally decrement ticks, update prev stall."""
    moves = orchestration_state.get("recent_structured_moves")
    if not isinstance(moves, list):
        moves = []
    decisions = orchestration_state.get("director_decisions")
    if not isinstance(decisions, list):
        decisions = []

    raw_stall = progression_advisory.get("stall_score")
    try:
        stall_score = float(raw_stall) if raw_stall is not None else 0.0
    except (TypeError, ValueError):
        stall_score = 0.0

    _maybe_arm_post_break_from_stall_cross(orchestration_state, stall_score)

    ticks_before = int(orchestration_state.get(_TICKS_KEY) or 0)
    post_break_active = ticks_before > 0

    ping_ok, pa, pb = detect_ping_pong_pair(decisions)
    plabels = player_speaker_labels(session_state, list(participant_names))
    agency_low = low_player_agency(moves, plabels)

    trigger = ping_ok and (post_break_active or agency_low)
    prefix = ""
    if trigger:
        prefix = build_anti_regression_director_prefix(
            actor_a=pa,
            actor_b=pb,
            player_labels=plabels,
            low_agency=agency_low,
        )
        logger.info(
            "[anti_regression] director advisory active post_break=%s low_agency=%s pair=%s/%s",
            post_break_active,
            agency_low,
            pa,
            pb,
        )

    if ticks_before > 0:
        orchestration_state[_TICKS_KEY] = ticks_before - 1

    orchestration_state[_PREV_STALL_KEY] = stall_score

    blob: dict[str, Any] = {
        "active": bool(prefix),
        "ping_pong_detected": ping_ok,
        "post_break_window_active": post_break_active,
        "low_player_agency": agency_low,
        "ping_pong_actors": [pa, pb] if ping_ok else [],
        "ticks_after_decrement": int(orchestration_state.get(_TICKS_KEY) or 0),
    }
    orchestration_state[_CACHE_KEY] = blob
    return {"advisory_blob": blob, "prompt_prefix": prefix}


def sync_anti_regression_advisory_for_prompts(
    *,
    orchestration_state: dict[str, Any],
    progression_advisory: dict[str, Any],
    session_state: dict[str, Any],
    participant_names: list[str],
) -> dict[str, Any]:
    if not isinstance(progression_advisory, dict):
        progression_advisory = {}
    return refresh_anti_regression_advisory_cache(
        orchestration_state=orchestration_state,
        progression_advisory=progression_advisory,
        session_state=session_state if isinstance(session_state, dict) else {},
        participant_names=list(participant_names or []),
    )


def get_cached_anti_regression_advisory(
    orchestration_state: dict[str, Any],
) -> dict[str, Any] | None:
    raw = orchestration_state.get(_CACHE_KEY)
    return raw if isinstance(raw, dict) else None

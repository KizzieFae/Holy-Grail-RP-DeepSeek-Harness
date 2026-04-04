"""Low-pressure Director turn selection guidance (payload + prompt prefix only).

Does not modify progression, fairness, or continuation behavior.
"""

from __future__ import annotations

from typing import Any

from perception_audibility import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    normalize_move_audibility,
)

LOW_PRESSURE_REGIME_ID = "low_pressure_v1"

SELECTION_PRIORITIES: list[str] = [
    "If responder_hint.confidence is high, strongly prefer suggested_actor.",
    "Otherwise prefer a less-heard-available actor; avoid same as last spotlight when tied.",
    "If the same actor has spoken many times in a row, prefer switching unless fiction requires continuation (say so in reason).",
]


def consecutive_trailing_same_speaker(spotlight_history: list[str]) -> int:
    if not spotlight_history:
        return 0
    last = spotlight_history[-1]
    n = 0
    for name in reversed(spotlight_history):
        if name == last:
            n += 1
        else:
            break
    return n


def all_available_have_spoken_this_cycle(
    *,
    available_actors: list[str],
    actors_used_this_round: list[str],
) -> bool:
    avail = [str(a or "").strip() for a in available_actors if str(a or "").strip()]
    if not avail:
        return False
    for name in avail:
        if actors_used_this_round.count(name) < 1:
            return False
    return True


def low_pressure_turn_guidance_active(
    *,
    beat_shift_active: bool,
    progression_pressure: str | None,
    available_actors: list[str],
    continuation_override_actor: str | None,
    anti_regression_director_hints_active: bool,
) -> bool:
    if beat_shift_active:
        return False
    if str(progression_pressure or "").strip().lower() == "high":
        return False
    if len(available_actors) < 2:
        return False
    co = str(continuation_override_actor or "").strip()
    if co:
        return False
    if anti_regression_director_hints_active:
        return False
    return True


def compute_responder_hint(
    *,
    last_structured_move: dict[str, Any] | None,
    available_actors: list[str],
    present_characters: list[str],
) -> dict[str, Any]:
    """Return high-confidence hint or {\"confidence\": \"none\"}."""
    if not last_structured_move or not isinstance(last_structured_move, dict):
        return {"confidence": "none"}

    speaker = str(last_structured_move.get("speaker", "") or "").strip()
    if not speaker:
        return {"confidence": "none"}

    avail_set = {str(a or "").strip() for a in available_actors if str(a or "").strip()}
    if not avail_set:
        return {"confidence": "none"}

    present = [
        str(p or "").strip()
        for p in (present_characters or [])
        if str(p or "").strip()
    ]
    if not present:
        present = list(avail_set)

    norm = normalize_move_audibility(dict(last_structured_move), speaker, present)
    aud = str(norm.get("audibility", "") or "").strip().lower()
    raw_audience = norm.get("audience", [])
    if not isinstance(raw_audience, list):
        return {"confidence": "none"}

    audience = [str(x or "").strip() for x in raw_audience if str(x or "").strip()]
    audience = [x for x in audience if x in avail_set]

    if aud not in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE):
        return {"confidence": "none"}
    if len(audience) != 1:
        return {"confidence": "none"}

    target = audience[0]
    if target not in avail_set:
        return {"confidence": "none"}

    return {
        "confidence": "high",
        "suggested_actor": target,
        "reason": "directed_audience_single",
        "source_move_index": -1,
    }


def build_low_pressure_turn_selection_payload(
    *,
    spotlight_recent: list[str],
    response_cycle_counts: dict[str, int],
    actors_used_this_round: list[str],
    available_actors: list[str],
) -> dict[str, Any]:
    return {
        "active": True,
        "regime": LOW_PRESSURE_REGIME_ID,
        "airtime": {
            "spotlight_recent": list(spotlight_recent),
            "consecutive_same_speaker": consecutive_trailing_same_speaker(
                list(spotlight_recent)
            ),
            "response_cycle_counts": dict(response_cycle_counts),
            "all_present_have_spoken_this_cycle": all_available_have_spoken_this_cycle(
                available_actors=available_actors,
                actors_used_this_round=actors_used_this_round,
            ),
        },
        "selection_priorities": list(SELECTION_PRIORITIES),
    }


def build_low_pressure_director_prompt_prefix() -> str:
    return (
        "[low_pressure_turn_selection] The JSON payload may include "
        "low_pressure_turn_selection and responder_hint.\n"
        "- If responder_hint.confidence is \"high\", you SHOULD set next_actor to "
        "responder_hint.suggested_actor unless you give a clear, in-fiction reason "
        "in reason for choosing a different available actor (e.g. they cannot "
        "plausibly respond this beat).\n"
        "- Otherwise prefer available actors with lower response_cycle_acting_counts; "
        "when counts tie, avoid repeating the last spotlight speaker when the beat "
        "allows a natural handoff.\n"
        "- If consecutive_same_speaker is high, prefer giving the floor to another "
        "available actor unless the fiction clearly requires the same voice to "
        "continue (say so in reason).\n\n"
    )


def build_director_selection_metrics(
    *,
    low_pressure_regime: bool,
    consecutive_spotlight_same: int,
    all_available_have_spoken: bool,
    responder_hint: dict[str, Any],
    director_pick: str,
    spotlight_last_before_pick: str | None,
    end_round: bool,
) -> dict[str, Any]:
    rh_conf = str(responder_hint.get("confidence", "none") or "none")
    suggested = (
        str(responder_hint.get("suggested_actor", "") or "").strip()
        if rh_conf == "high"
        else None
    )

    repeat_after = (
        bool(all_available_have_spoken)
        and bool(director_pick)
        and spotlight_last_before_pick is not None
        and director_pick == spotlight_last_before_pick
    )

    compliance: bool | None
    if end_round:
        compliance = None
    elif rh_conf == "high" and suggested:
        compliance = director_pick == suggested
    else:
        compliance = None

    out: dict[str, Any] = {
        "low_pressure_regime": low_pressure_regime,
        "consecutive_spotlight_same": consecutive_spotlight_same,
        "all_available_have_spoken": all_available_have_spoken,
        "responder_hint_confidence": rh_conf,
        "responder_hint_suggested": suggested,
        "director_pick": director_pick,
        "repeat_after_all_heard": repeat_after,
    }
    if compliance is not None:
        out["responder_hint_compliance"] = compliance
    return out

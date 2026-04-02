"""Pending beat-shift flag: detect steering / plateau signals, consume after one character turn."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("rp_app.beat_shift")

_HIGH_TENSION = frozenset({"high", "extreme"})


def default_pending_beat_shift() -> dict[str, Any]:
    return {"active": False, "reason": "", "source_turn_id": None}


def ensure_beat_shift_fields(orchestration_state: dict[str, Any]) -> None:
    pbs = orchestration_state.get("pending_beat_shift")
    if not isinstance(pbs, dict):
        orchestration_state["pending_beat_shift"] = default_pending_beat_shift()
    else:
        pbs.setdefault("active", False)
        pbs.setdefault("reason", "")
        pbs.setdefault("source_turn_id", None)
    orchestration_state.setdefault("beat_shift_scene_snapshots", [])


def _normalize_word_token(raw: str) -> str:
    return re.sub(r"[^\w]+", "", (raw or "").lower())


def user_message_suggests_beat_shift(trigger_text: str) -> tuple[bool, str]:
    s = str(trigger_text or "").strip()
    if not s:
        return False, ""
    tokens = [t for t in re.split(r"\s+", s) if t]
    if len(tokens) <= 6:
        return True, "short_user_message"
    words = [_normalize_word_token(t) for t in tokens]
    words = [w for w in words if len(w) >= 2]
    counts: dict[str, int] = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    if any(c >= 2 for c in counts.values()):
        return True, "repeated_words_user_message"
    return False, ""


def plateau_snapshots_suggest_beat_shift(
    snapshots: list[dict[str, Any]],
) -> tuple[bool, str]:
    if len(snapshots) < 2:
        return False, ""
    a, b = snapshots[-2], snapshots[-1]
    p1 = str(a.get("phase", "") or "").strip()
    p2 = str(b.get("phase", "") or "").strip()
    t1 = str(a.get("tension", "") or "").strip().lower()
    t2 = str(b.get("tension", "") or "").strip().lower()
    if not p1 or p1 != p2:
        return False, ""
    if t1 not in _HIGH_TENSION or t2 not in _HIGH_TENSION:
        return False, ""
    return True, "plateau_same_phase_high_tension"


def maybe_activate_pending_beat_shift(
    orchestration_state: dict[str, Any],
    *,
    trigger_text: str,
    source_turn_id: str | None,
    active_issues: list[dict[str, Any]] | None = None,
    recent_structured_moves: list[dict[str, Any]] | None = None,
) -> None:
    ensure_beat_shift_fields(orchestration_state)
    snaps = orchestration_state.get("beat_shift_scene_snapshots")
    if not isinstance(snaps, list):
        snaps = []
        orchestration_state["beat_shift_scene_snapshots"] = snaps

    hit, reason = user_message_suggests_beat_shift(trigger_text)
    if not hit:
        from progression_advisory import (  # noqa: PLC0415 — avoid import cycle
            STALL_BEAT_SHIFT_THRESHOLD,
            compute_stall_score,
        )

        scene_state = orchestration_state.get("scene_state")
        if not isinstance(scene_state, dict):
            scene_state = {}
        moves = recent_structured_moves
        if moves is None:
            rm = orchestration_state.get("recent_structured_moves")
            moves = rm if isinstance(rm, list) else []
        issues = active_issues if isinstance(active_issues, list) else []

        stall_score, stall_components = compute_stall_score(
            scene_state=scene_state,
            recent_structured_moves=moves,
            active_issues=issues,
            beat_shift_snapshots=snaps,
        )
        if stall_score >= STALL_BEAT_SHIFT_THRESHOLD:
            hit, reason = True, "progression_stall"
            logger.info(
                "[beat_shift] progression_stall activates beat_shift "
                "stall_score=%s components=%s source_turn_id=%s",
                round(stall_score, 4),
                stall_components,
                source_turn_id,
            )

    if not hit:
        return

    pbs = orchestration_state["pending_beat_shift"]
    pbs["active"] = True
    pbs["reason"] = reason
    pbs["source_turn_id"] = source_turn_id
    logger.info(
        "[beat_shift] set active reason=%s source_turn_id=%s",
        reason,
        source_turn_id,
    )


def consume_pending_beat_shift_if_active(orchestration_state: dict[str, Any]) -> bool:
    """Clear active beat-shift after a character turn. Returns True if it was active."""
    ensure_beat_shift_fields(orchestration_state)
    pbs = orchestration_state["pending_beat_shift"]
    if not pbs.get("active"):
        return False
    prev_reason = str(pbs.get("reason", "") or "")
    prev_id = pbs.get("source_turn_id")
    pbs["active"] = False
    pbs["reason"] = ""
    pbs["source_turn_id"] = None
    logger.info(
        "[beat_shift] consumed and cleared (was reason=%s source_turn_id=%s)",
        prev_reason,
        prev_id,
    )
    return True


def append_scene_snapshot_after_turn(orchestration_state: dict[str, Any]) -> None:
    ensure_beat_shift_fields(orchestration_state)
    ss = orchestration_state.setdefault("scene_state", {})
    phase = str(ss.get("scene_phase", "") or "").strip()
    tension = str(ss.get("current_tension_level", "") or "").strip()
    snaps = orchestration_state.setdefault("beat_shift_scene_snapshots", [])
    snaps.append({"phase": phase, "tension": tension})
    orchestration_state["beat_shift_scene_snapshots"] = snaps[-2:]


def is_pending_beat_shift_active(orchestration_state: dict[str, Any]) -> bool:
    pbs = orchestration_state.get("pending_beat_shift")
    return isinstance(pbs, dict) and bool(pbs.get("active"))


def build_character_beat_shift_suffix(*, trigger_text: str) -> str:
    """Soft Phase-3 instructions appended to the character system prompt.

    ``trigger_text`` must already be the **per-character, perception-filtered**
    player line (see ``player_text_for_character_viewer``). Callers must not pass
    the raw global user trigger here.
    """
    lines = [
        "",
        "BEAT SHIFT (ACTIVE):",
        "The next beat must include a concrete change in the scene state—not only reframing or escalating the same conflict through metaphor alone.",
        "Lean toward at least one of: a clear physical action; an irreversible or high-stakes decision; an interruption that alters what happens next; new information others can react to; or an explicit commitment that moves the situation forward.",
        "If the latest player input is very short or reads as OOC or emphatic steering, you may give a brief in-world translation of that pressure, or embody it as direct physical or interpersonal follow-through—either way, make what changes in the scene observable.",
    ]
    base = "\n".join(lines)
    t = str(trigger_text or "").strip()
    if not t:
        return base
    if len(t) <= 200:
        return f'{base}\n\nLATEST PLAYER INPUT: "{t}"'
    return f'{base}\n\nLATEST PLAYER INPUT (truncated): "{t[:200]}..."'


def build_narrator_beat_shift_suffix() -> str:
    """Soft Phase-3 instructions appended to the narrator render prompt."""
    return (
        "\n\nBEAT SHIFT (ACTIVE): The narration should make at least one concrete change in scene state "
        "clear to the reader (what is now different in action, knowledge, commitment, or situation)—not only "
        "richer metaphor or restated tension. Ground the beat in observable action and consequence when the "
        "supplied action and dialogue allow."
    )


def build_director_beat_shift_prompt_prefix() -> str:
    """Phase-4 director selection: prepended to the JSON payload prompt (not serialized in payload)."""
    return (
        "BEAT SHIFT (ACTIVE) — DIRECTOR SELECTION:\n"
        "- Prefer whoever can most directly execute a concrete physical or narrative shift in response to the latest trigger "
        "(including short, emphatic, or OOC-style steering).\n"
        "- Prefer whoever the trigger most directly addresses or implicates when the text supports that choice.\n"
        "- You may choose someone who already acted earlier this response cycle if they are clearly the right person to realize the shift; "
        "do not treat strict alternation or 'unused this round' as more important than advancing the beat.\n"
        "- Still choose only from available_next_actors and respect presence/eligibility implied there.\n\n"
    )

"""Infer short-horizon exit/re-entry from the Traveler's trigger text (offstage routing)."""

import re
from typing import Any, Callable

_REENTRY_SIGNAL = re.compile(
    r"\b(?:"
    r"came\s+back|come\s+back|coming\s+back|returns?|returned|returning|"
    r"re-?entered|re-?enter|back\s+in|back\s+inside|walked\s+back|"
    r"showed\s+up\s+again"
    r")\b",
    re.IGNORECASE,
)

_EXIT_SIGNAL = re.compile(
    r"\b(?:"
    r"left\s+again|left\s+the|leaves?\s+the|leaving\s+the|"
    r"walked\s+out|stormed\s+out|headed\s+out|went\s+to\s+the|"
    r"exited|exiting|exit(?:ed|ing)?\s+the|"
    r"out\s+of\s+the\s+(?:room|dorm|suite|scene)|"
    r"off\s+to\s+the|in\s+the\s+garage|across\s+the\s+street|"
    r"not\s+here|isn'?t\s+here|is\s+gone|has\s+left"
    r")\b",
    re.IGNORECASE,
)


def _character_mentioned_in_trigger(
    trigger_lower: str,
    internal_name: str,
    display_name: str,
) -> bool:
    disp = (display_name or "").strip()
    if len(disp) >= 2 and disp.lower() in trigger_lower:
        return True
    parts = [p for p in internal_name.replace("_", " ").split() if len(p) >= 3]
    for part in parts:
        if re.search(rf"\b{re.escape(part.lower())}\b", trigger_lower):
            return True
    return False


def apply_user_trigger_to_offstage(
    *,
    scene_state: Any,
    trigger_text: str,
    participant_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> None:
    """Update ``offstage_characters`` from the Traveler's message (best-effort heuristics)."""
    if scene_state is None:
        return
    raw = (trigger_text or "").strip()
    if not raw:
        return
    t = raw.lower()
    present = set(getattr(scene_state, "present_characters", []) or [])
    off = list(getattr(scene_state, "offstage_characters", []) or [])

    for name in participant_names:
        if name not in present:
            continue
        disp = str(get_character_display_name_fn(name) or "")
        if not _character_mentioned_in_trigger(t, name, disp):
            continue
        if _REENTRY_SIGNAL.search(t):
            off = [n for n in off if n != name]
        elif _EXIT_SIGNAL.search(t):
            if name not in off:
                off.append(name)

    scene_state.offstage_characters = off


def apply_user_trigger_to_offstage_on_scratch(
    *,
    scratch: Any,
    trigger_text: str,
    participant_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> None:
    """Update scratch ``offstage_characters`` from trigger text (same heuristics as on scene_state)."""
    raw = (trigger_text or "").strip()
    if not raw:
        return
    t = raw.lower()
    present = set(getattr(scratch, "present_characters", []) or [])
    off = list(getattr(scratch, "offstage_characters", []) or [])

    for name in participant_names:
        if name not in present:
            continue
        disp = str(get_character_display_name_fn(name) or "")
        if not _character_mentioned_in_trigger(t, name, disp):
            continue
        if _REENTRY_SIGNAL.search(t):
            off = [n for n in off if n != name]
        elif _EXIT_SIGNAL.search(t):
            if name not in off:
                off.append(name)

    scratch.offstage_characters = off


def release_pending_forced_speaker_from_offstage(
    *,
    scene_state: Any,
    pending_forced_speaker: str | None,
    participant_names: list[str],
) -> None:
    """Direct address implies they are back in play for this cycle."""
    if scene_state is None or not pending_forced_speaker:
        return
    if pending_forced_speaker not in participant_names:
        return
    off = list(getattr(scene_state, "offstage_characters", []) or [])
    if pending_forced_speaker in off:
        scene_state.offstage_characters = [n for n in off if n != pending_forced_speaker]


def release_pending_forced_speaker_on_scratch(
    *,
    scratch: Any,
    pending_forced_speaker: str | None,
    participant_names: list[str],
) -> None:
    """Remove pending forced speaker from scratch ``offstage_characters`` when applicable."""
    if scratch is None or not pending_forced_speaker:
        return
    if pending_forced_speaker not in participant_names:
        return
    off = list(getattr(scratch, "offstage_characters", []) or [])
    if pending_forced_speaker in off:
        scratch.offstage_characters = [n for n in off if n != pending_forced_speaker]

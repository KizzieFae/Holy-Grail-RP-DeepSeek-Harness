"""Perception-safe formatting for observable transcript lines (v1 / v2)."""

from __future__ import annotations

from typing import Any, Callable

from perception_audibility_constants import AUDIBILITY_PUBLIC, REDACTED_SPEECH_STUB
from perception_audibility_visibility import speech_beat_viewer_may_perceive


def _canonical_viewer_for_present(
    viewer_character_name: str,
    present_characters: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> str:
    """Align viewer id with the ``present_characters`` labels used in audiences."""
    v = str(viewer_character_name or "").strip()
    present = [str(p).strip() for p in present_characters if str(p or "").strip()]
    if v in present:
        return v
    vd = get_character_display_name_fn(v).strip()
    for p in present:
        if get_character_display_name_fn(p).strip() == vd:
            return p
    return v


def format_observable_beat_text(
    *,
    speaker_label: str,
    move: dict[str, Any],
    acting_character: str,
) -> str:
    """Perception-safe line when full narrator prose must not be shown (v1-shaped move)."""
    action = str(move.get("action", "") or "").strip()
    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if not action:
        if aud == AUDIBILITY_PUBLIC:
            return f"{speaker_label}: [nonverbal beat]"
        return f"{speaker_label}: [private or directed speech — audible action only; dialogue omitted]"
    if aud == AUDIBILITY_PUBLIC:
        return f"{speaker_label}: {action}"
    return f"{speaker_label}: {action} (private or directed speech; exact words omitted for this recipient)"


def format_observable_v2_turn_for_viewer(
    *,
    speaker_label: str,
    move_norm: dict[str, Any],
    acting_character: str,
    viewer_character_name: str,
    present_characters: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> str:
    """Structured-transcript stub line for a v2 move when ``rendered`` must not leak."""
    vc = _canonical_viewer_for_present(
        viewer_character_name, present_characters, get_character_display_name_fn
    )
    parts: list[str] = []
    beats = move_norm.get("beats")
    if not isinstance(beats, list):
        return f"{speaker_label}: [beat]"
    for b in beats:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "action":
            a = str(b.get("action", "") or "").strip()
            if a:
                parts.append(a)
        elif b.get("type") == "speech":
            if speech_beat_viewer_may_perceive(
                b, acting_character=acting_character, viewer_character=vc
            ):
                d = str(b.get("dialogue", "") or "").strip()
                if d:
                    parts.append(d)
            else:
                parts.append(REDACTED_SPEECH_STUB)
    if not parts:
        return f"{speaker_label}: [beat]"
    return f"{speaker_label}: " + " ".join(parts)

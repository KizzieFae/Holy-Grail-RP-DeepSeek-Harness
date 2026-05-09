"""Boolean visibility: who may perceive structured dialogue / narrator content."""

from __future__ import annotations

from typing import Any

from character_move_adapters import is_canonical_v2_move

from perception_audibility_constants import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    AUDIBILITY_PUBLIC,
)
from perception_audibility_normalize import normalize_move_audibility


def speech_beat_viewer_may_perceive(
    beat: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str,
) -> bool:
    """Whether ``viewer_character`` may receive verbatim ``dialogue`` for this speech beat."""
    aud = str(beat.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return True
    if viewer_character == acting_character:
        return True
    # Directed / private: visibility-equivalent for #138.
    audience = beat.get("audience")
    if not isinstance(audience, list):
        return False
    return viewer_character in [str(a).strip() for a in audience if str(a).strip()]


def viewer_may_perceive_dialogue(
    move: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str,
) -> bool:
    """Whether ``viewer_character`` may receive structured dialogue for this move (any beat)."""
    if is_canonical_v2_move(move):
        beats = move.get("beats")
        if not isinstance(beats, list):
            return True
        speech_any = False
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            speech_any = True
            if speech_beat_viewer_may_perceive(
                b, acting_character=acting_character, viewer_character=viewer_character
            ):
                return True
        return not speech_any

    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return True
    if viewer_character == acting_character:
        return True
    if aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE):
        audience = move.get("audience")
        if not isinstance(audience, list):
            return False
        return viewer_character in [str(a).strip() for a in audience if str(a).strip()]
    return False


def use_full_narrator_content_for_recipient(
    move: dict[str, Any],
    *,
    acting_character: str,
    viewer_character: str | None,
    present_characters: list[str] | None = None,
) -> bool:
    """Whether to include full ``rendered`` prose (vs observable-only stub).

    ``viewer_character`` ``None`` => Director / orchestration transcript: **always**
    full prose (canonical visibility for orchestration; Issue #138).

    For v2 moves, all speech beats must be perceivable by the viewer; optional
    ``present_characters`` is used when normalizing beats (defaults to
    ``[acting_character, viewer_character]`` when the viewer is a character).
    """
    if viewer_character is None:
        return True
    present = present_characters
    if present is None:
        present = list(dict.fromkeys([acting_character, viewer_character]))
    move_norm = normalize_move_audibility(dict(move), acting_character, present)
    if is_canonical_v2_move(move_norm):
        beats = move_norm.get("beats")
        if not isinstance(beats, list):
            return True
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            if not speech_beat_viewer_may_perceive(
                b,
                acting_character=acting_character,
                viewer_character=viewer_character,
            ):
                return False
        return True

    aud = str(move_norm.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return True
    if viewer_character == acting_character:
        return True
    if aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE):
        audience = move_norm.get("audience")
        if not isinstance(audience, list):
            return False
        names = [str(a).strip() for a in audience if str(a).strip()]
        return viewer_character in names
    return False

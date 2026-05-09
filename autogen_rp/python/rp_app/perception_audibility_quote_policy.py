"""Policy for whether interpretations may quote dialogue (observer-scoped)."""

from __future__ import annotations

from typing import Any

from character_move_adapters import is_canonical_v2_move

from perception_audibility_visibility import (
    speech_beat_viewer_may_perceive,
    viewer_may_perceive_dialogue,
)


def observer_may_quote_dialogue_in_interpretation(
    move: dict[str, Any],
    *,
    acting_character: str,
    observer_character: str,
) -> bool:
    """Whether interpretations may include quoted dialogue for this observer."""
    if is_canonical_v2_move(move):
        beats = move.get("beats")
        if not isinstance(beats, list):
            return True
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            if speech_beat_viewer_may_perceive(
                b,
                acting_character=acting_character,
                viewer_character=observer_character,
            ):
                return True
        return False
    return viewer_may_perceive_dialogue(
        move, acting_character=acting_character, viewer_character=observer_character
    )

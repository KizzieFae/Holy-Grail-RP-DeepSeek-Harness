"""Narrow prompt context for characters who are offstage (not in the shared immediate space)."""

from typing import Any, Callable


def filter_dialogue_for_offstage_character(
    recent_dialogue: list[dict[str, Any]],
    *,
    char_name: str,
    get_character_display_name_fn: Callable[[str], str],
) -> list[dict[str, Any]]:
    """Keep Traveler/user lines and this character's own assistant lines only."""
    my_label = str(get_character_display_name_fn(char_name) or "").strip()
    out: list[dict[str, Any]] = []
    for msg in recent_dialogue:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "") or "").strip().lower()
        if role == "user":
            out.append(msg)
            continue
        speaker = str(msg.get("speaker", "") or "").strip()
        if my_label and speaker == my_label:
            out.append(msg)
    return out


def filter_structured_moves_for_offstage_character(
    recent_moves: list[dict[str, Any]],
    char_name: str,
) -> list[dict[str, Any]]:
    """Keep only this character's own structured beats."""
    return [
        item
        for item in recent_moves
        if isinstance(item, dict)
        and str(item.get("speaker", "") or "").strip() == char_name
    ]

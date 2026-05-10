"""Dialogue-history construction from Streamlit session character roster (Issue #174)."""

from collections.abc import Callable, Mapping
from typing import Any

from perception_audibility import build_recent_dialogue_history_for_viewer


def build_recent_dialogue_history_from_session(
    chat_history: list[dict[str, Any]],
    *,
    session_state: Mapping[str, Any],
    limit: int,
    viewer_character_name: str | None,
    get_character_display_name_fn: Callable[[str], str],
) -> list[dict[str, str]]:
    names = [
        str(a.name)
        for a in session_state.get("characters", [])
        if getattr(a, "name", None)
    ]
    return build_recent_dialogue_history_for_viewer(
        chat_history=chat_history,
        viewer_character_name=viewer_character_name,
        character_names=names,
        get_character_display_name_fn=get_character_display_name_fn,
        limit=limit,
    )

"""Player / user line projection for character-visible prompts."""

from __future__ import annotations

from typing import Any, Callable

from perception_audibility_constants import REDACTED_PLAYER_TEXT_CONTENT
from perception_audibility_formatting import _canonical_viewer_for_present
from perception_audibility_normalize import normalize_move_audibility
from perception_audibility_visibility import viewer_may_perceive_dialogue


def player_text_for_character_viewer(
    *,
    raw_text: str,
    viewer_character_name: str,
    present_characters: list[str],
    user_display_name: str,
    get_character_display_name_fn: Callable[[str], str] | None = None,
) -> str:
    """Return player/user ``raw_text`` or a redacted placeholder for this viewer.

    Models the line as structured ``dialogue`` on a synthetic move from
    ``user_display_name``, then applies :func:`normalize_move_audibility` and
    :func:`viewer_may_perceive_dialogue` — same rules as character moves.

    **MVP:** If audibility is ambiguous (no whisper / directed markers), the line
    is treated as **public** so all present characters receive the full string.
    This preserves pre-fix default exposure and avoids over-redaction; it is not
    declared final policy.

    Director / orchestration transcript paths pass ``viewer_character_name=None``
    to :func:`build_recent_dialogue_history_for_viewer` and receive unfiltered
    user lines.
    """
    text = str(raw_text or "")
    if not str(text).strip():
        return text

    display_fn = get_character_display_name_fn or (lambda x: str(x))
    acting = str(user_display_name or "").strip() or "Traveler"
    present = [str(p).strip() for p in present_characters if str(p or "").strip()]

    synthetic: dict[str, Any] = {
        "action": "",
        "dialogue": text,
        "audibility": "",
        "audience": [],
    }
    norm = normalize_move_audibility(synthetic, acting, present)
    viewer = _canonical_viewer_for_present(
        viewer_character_name, present, display_fn
    )
    if viewer_may_perceive_dialogue(
        norm, acting_character=acting, viewer_character=viewer
    ):
        return text
    return REDACTED_PLAYER_TEXT_CONTENT

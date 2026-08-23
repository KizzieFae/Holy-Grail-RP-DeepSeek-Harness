"""Assemble recent chat history with per-viewer perception filtering."""

from __future__ import annotations

from typing import Any, Callable

# Bounded recent conversation window for character manifest transcript projection.
# Numerically aligned with perception validation tail windows; not imported from
# response-validation modules (Host packaging must not depend on validation code).
RECENT_SCENE_TRANSCRIPT_WINDOW = 16

from character_move_adapters import is_canonical_v2_move

from perception_audibility_formatting import (
    format_observable_beat_text,
    format_observable_v2_turn_for_viewer,
)
from perception_audibility_normalize import normalize_move_audibility
from perception_audibility_player import player_text_for_character_viewer
from perception_audibility_visibility import use_full_narrator_content_for_recipient


def resolve_message_actor(
    message: dict[str, Any],
    *,
    character_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
) -> str | None:
    """Resolve internal character id for an assistant chat message."""
    raw = message.get("actor")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    speaker_label = str(message.get("speaker", "") or "").strip()
    if not speaker_label:
        return None
    for name in character_names:
        if get_character_display_name_fn(name).strip() == speaker_label:
            return name
    return None


def build_recent_dialogue_history_for_viewer(
    *,
    chat_history: list[dict[str, Any]],
    viewer_character_name: str | None,
    character_names: list[str],
    get_character_display_name_fn: Callable[[str], str],
    limit: int,
) -> list[dict[str, str]]:
    """Assemble recent history; filter narrator content using structured ``move`` only.

    ``viewer_character_name`` ``None`` => Director / orchestration: full **rendered**
    lines and unredacted structured semantics for transcript assembly (Issue #138).
    """
    history: list[dict[str, str]] = []
    present = [str(n).strip() for n in character_names if str(n or "").strip()]
    for message in chat_history[-limit:]:
        if message.get("role") == "system":
            continue
        role = str(message.get("role", "assistant") or "assistant")
        if role == "user":
            speaker = str(message.get("speaker", "Traveler") or "Traveler")
            content = str(message.get("content", "") or "")
            if viewer_character_name is None:
                safe_content = content
            else:
                safe_content = player_text_for_character_viewer(
                    raw_text=content,
                    viewer_character_name=viewer_character_name,
                    present_characters=present,
                    user_display_name=speaker,
                    get_character_display_name_fn=get_character_display_name_fn,
                )
            history.append(
                {
                    "role": role,
                    "speaker": speaker,
                    "content": safe_content,
                }
            )
            continue

        speaker_label = str(message.get("speaker", "Unknown") or "Unknown")
        move = message.get("move")
        if not isinstance(move, dict):
            move = {}
        actor = resolve_message_actor(
            message,
            character_names=character_names,
            get_character_display_name_fn=get_character_display_name_fn,
        )
        content = str(message.get("content", "") or "")

        if actor is None:
            history.append({"role": role, "speaker": speaker_label, "content": content})
            continue

        move_norm = normalize_move_audibility(dict(move), actor, present)
        if use_full_narrator_content_for_recipient(
            move_norm,
            acting_character=actor,
            viewer_character=viewer_character_name,
            present_characters=present,
        ):
            pass
        elif is_canonical_v2_move(move_norm) and viewer_character_name is not None:
            content = format_observable_v2_turn_for_viewer(
                speaker_label=speaker_label,
                move_norm=move_norm,
                acting_character=actor,
                viewer_character_name=viewer_character_name,
                present_characters=present,
                get_character_display_name_fn=get_character_display_name_fn,
            )
        else:
            content = format_observable_beat_text(
                speaker_label=speaker_label,
                move=move_norm,
                acting_character=actor,
            )

        history.append({"role": role, "speaker": speaker_label, "content": content})

    return history

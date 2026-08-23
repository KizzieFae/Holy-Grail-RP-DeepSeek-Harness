"""Project durable rp_history into character manifest transcript/trigger content."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from memory_layer.writes import resolve_present_characters  # noqa: E402
from perception_audibility_constants import REDACTED_PLAYER_TEXT_CONTENT  # noqa: E402
from perception_audibility_history import (  # noqa: E402
    RECENT_SCENE_TRANSCRIPT_WINDOW,
    build_recent_dialogue_history_for_viewer,
)
from perception_audibility_player import player_text_for_character_viewer  # noqa: E402

from .session_history import (  # noqa: E402
    substantive_user_entry_for_trigger,
    project_history_to_character_context_chat,
)
from .session_state import LiveSession  # noqa: E402


def _character_display_name(character_id: str) -> str:
    return character_id


def _latest_user_history_entry(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    return substantive_user_entry_for_trigger(history)


def _format_transcript_content(recent_dialogue: list[dict[str, str]]) -> str:
    return (
        "RECENT SCENE TRANSCRIPT (PERCEPTION-FILTERED FOR THIS CHARACTER):\n"
        + json.dumps(recent_dialogue, ensure_ascii=False, indent=2)
    )


def _format_trigger_content(trigger_text: str) -> str:
    return f"TRIGGER FOR THIS BEAT:\n{trigger_text}"


def project_character_conversation_for_manifest(
    fixture: LiveSession,
    *,
    character_id: str,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """Return transcript content, trigger content, and shared provenance for manifest assembly."""
    history = fixture.rp_history
    provenance: dict[str, Any] = {
        "character_id": character_id,
        "projection_kind": "rp_history_conversation",
        "transcript_window": RECENT_SCENE_TRANSCRIPT_WINDOW,
        "transcript_message_count": 0,
    }
    if not history:
        return None, None, provenance

    cast = list(fixture.cast)
    present = resolve_present_characters(
        continuity_manager=fixture.manager,
        char_names=cast,
    )
    transcript_chat = project_history_to_character_context_chat(
        history,
        character_id=character_id,
        character_names=cast,
        present_characters=present,
        get_character_display_name_fn=_character_display_name,
    )
    recent_dialogue = build_recent_dialogue_history_for_viewer(
        chat_history=transcript_chat,
        viewer_character_name=character_id,
        character_names=cast,
        get_character_display_name_fn=_character_display_name,
        limit=RECENT_SCENE_TRANSCRIPT_WINDOW,
    )
    provenance["transcript_message_count"] = len(recent_dialogue)

    transcript_content = (
        _format_transcript_content(recent_dialogue) if recent_dialogue else None
    )

    trigger_content: str | None = None
    latest_user = _latest_user_history_entry(history)
    if latest_user is not None and character_id in present:
        raw_content = str(latest_user.get("content") or "")
        metadata = latest_user.get("metadata") if isinstance(latest_user.get("metadata"), dict) else {}
        speaker = str(latest_user.get("actor_id") or metadata.get("speaker") or "Player")
        if raw_content.strip():
            perceived = player_text_for_character_viewer(
                raw_text=raw_content,
                viewer_character_name=character_id,
                present_characters=present,
                user_display_name=speaker,
                get_character_display_name_fn=_character_display_name,
            )
            if perceived and str(perceived).strip():
                trigger_content = _format_trigger_content(str(perceived))
                entry_id = latest_user.get("entry_id")
                if entry_id:
                    provenance["trigger_entry_id"] = str(entry_id)
                if perceived == REDACTED_PLAYER_TEXT_CONTENT:
                    provenance["trigger_redacted"] = True

    return transcript_content, trigger_content, provenance

"""Session-local memory write policy for the V2 Domain Host."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from app_memory_summary import (  # noqa: E402
    build_memory_fact_summary,
    summarize_user_message,
)
from character_move_adapters import (  # noqa: E402
    root_or_flat_action_text,
    root_or_flat_dialogue_text,
)
from character_state_manager import CharacterStateManager  # noqa: E402
from character_state_model import CharacterState  # noqa: E402
from memory_layer.writes import (  # noqa: E402
    commit_character_turn_memory,
    commit_user_message_memory,
    resolve_present_characters,
)
from perception_audibility_constants import REDACTED_PLAYER_TEXT_CONTENT  # noqa: E402
from perception_audibility_player import player_text_for_character_viewer  # noqa: E402

from .session_state import LiveSession  # noqa: E402


def snapshot_character_states(
    fixture: LiveSession,
) -> dict[str, CharacterState]:
    return {
        name: CharacterState.from_dict(state.to_dict())
        for name, state in fixture.character_states.items()
    }


def restore_character_states(
    fixture: LiveSession, snapshot: dict[str, CharacterState]
) -> None:
    fixture.character_states = {
        name: CharacterState.from_dict(state.to_dict())
        for name, state in snapshot.items()
    }


def _manager_for_session(fixture: LiveSession) -> CharacterStateManager:
    manager = CharacterStateManager()
    for name, state in fixture.character_states.items():
        manager.register_character(name, state)
    return manager


def _memory_move_view(move: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": root_or_flat_action_text(move),
        "dialogue": root_or_flat_dialogue_text(move),
        "motivation": move.get("motivation", {}),
        "beats": move.get("beats"),
        "audibility": move.get("audibility", ""),
        "audience": move.get("audience", []),
    }


def _memory_fact_summary(acting_character: str, move: dict[str, Any]) -> str:
    return build_memory_fact_summary(acting_character, _memory_move_view(move))


def apply_character_turn_memory(
    fixture: LiveSession,
    *,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
) -> None:
    """Write session-local memory after an authoritative character commit."""
    manager = _manager_for_session(fixture)
    move_view = _memory_move_view(move)
    motivation = move_view.get("motivation", {})

    manager.update_character_move(
        acting_character,
        str(move_view.get("action", "") or ""),
        str(move_view.get("dialogue", "") or ""),
        motivation if isinstance(motivation, dict) else {},
    )

    present = resolve_present_characters(
        continuity_manager=fixture.manager,
        char_names=list(fixture.cast),
    )
    commit_character_turn_memory(
        state_manager=manager,
        character_names=list(fixture.cast),
        acting_character=acting_character,
        move=move_view,
        director_decision=dict(director_decision),
        present_characters=present,
        build_memory_fact_summary_fn=_memory_fact_summary,
        display_name_for_key=None,
    )


def apply_user_turn_memory(
    fixture: LiveSession,
    *,
    user_name: str,
    content: str,
) -> None:
    """Remember user interaction only for present characters who can perceive the line."""
    present = resolve_present_characters(
        continuity_manager=fixture.manager,
        char_names=list(fixture.cast),
    )
    if not present:
        return

    for character_name in present:
        perceived = player_text_for_character_viewer(
            raw_text=content,
            viewer_character_name=character_name,
            present_characters=present,
            user_display_name=user_name,
        )
        if not str(perceived or "").strip():
            continue
        if perceived == REDACTED_PLAYER_TEXT_CONTENT:
            continue
        summary = summarize_user_message(user_name, perceived)
        state = fixture.character_states.get(character_name)
        if state is not None:
            state.remember_user_interaction(user_name, summary)


def apply_user_turn_memory_legacy_all_cast(
    fixture: LiveSession,
    *,
    user_name: str,
    content: str,
) -> None:
    """Test-only helper mirroring legacy V1 all-cast behavior."""
    manager = _manager_for_session(fixture)
    commit_user_message_memory(
        state_manager=manager,
        character_names=list(fixture.cast),
        user_name=user_name,
        user_input=content,
        summarize_user_message_fn=summarize_user_message,
    )

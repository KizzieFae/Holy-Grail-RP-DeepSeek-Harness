"""Public memory-layer entry points (writes only in Phase A)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from memory_layer.writes import (
    commit_character_turn_memory as _commit_character_turn_memory,
    commit_user_message_memory as _commit_user_message_memory,
    resolve_present_characters,
)


def commit_character_turn_memory(
    *,
    state_manager: Any | None,
    character_names: list[str],
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    continuity_manager: Any | None,
    build_memory_fact_summary_fn: Callable[[str, dict[str, Any]], str],
    display_name_for_key: Callable[[str], str] | None = None,
) -> None:
    present_characters = resolve_present_characters(
        continuity_manager=continuity_manager, char_names=character_names
    )
    _commit_character_turn_memory(
        state_manager=state_manager,
        character_names=character_names,
        acting_character=acting_character,
        move=move,
        director_decision=director_decision,
        present_characters=present_characters,
        build_memory_fact_summary_fn=build_memory_fact_summary_fn,
        display_name_for_key=display_name_for_key,
    )


def commit_user_message_memory(
    *,
    state_manager: Any | None,
    character_names: list[str],
    user_name: str,
    user_input: str,
    summarize_user_message_fn: Callable[[str, str], str],
) -> None:
    _commit_user_message_memory(
        state_manager=state_manager,
        character_names=character_names,
        user_name=user_name,
        user_input=user_input,
        summarize_user_message_fn=summarize_user_message_fn,
    )


__all__ = [
    "commit_character_turn_memory",
    "commit_user_message_memory",
    "resolve_present_characters",
]

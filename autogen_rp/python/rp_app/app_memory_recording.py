from collections.abc import Callable
from typing import Any

from memory_layer.facade import (
    commit_character_turn_memory,
    commit_user_message_memory,
)


def record_user_memories(
    *, st_module: Any, user_name: str, user_input: str, summarize_user_message_fn
) -> None:
    state_manager = st_module.session_state.get("character_state_manager")
    character_names = [
        str(getattr(c, "name", "") or "").strip()
        for c in st_module.session_state.get("characters", [])
        if str(getattr(c, "name", "") or "").strip()
    ]
    commit_user_message_memory(
        state_manager=state_manager,
        character_names=character_names,
        user_name=user_name,
        user_input=user_input,
        summarize_user_message_fn=summarize_user_message_fn,
    )


def record_character_memories(
    *,
    st_module: Any,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    build_memory_fact_summary_fn,
    character_names: list[str],
    continuity_manager: Any | None = None,
    display_name_for_key: Callable[[str], str] | None = None,
) -> None:
    state_manager = st_module.session_state.get("character_state_manager")
    cm = (
        continuity_manager
        if continuity_manager is not None
        else st_module.session_state.get("continuity_manager")
    )
    commit_character_turn_memory(
        state_manager=state_manager,
        character_names=list(character_names),
        acting_character=acting_character,
        move=move,
        director_decision=director_decision,
        continuity_manager=cm,
        build_memory_fact_summary_fn=build_memory_fact_summary_fn,
        display_name_for_key=display_name_for_key,
    )

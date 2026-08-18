from app_memory_basics import (
    get_player_control_mode,
    has_player_character_conflict,
    resolve_bot_reply_limit,
)
from app_memory_cross_session import (
    apply_cross_session_memories as _apply_cross_session_memories_impl,
    load_cross_session_memories,
)
from app_memory_recording import (
    record_character_memories as _record_character_memories_impl,
)
from app_memory_recording import record_user_memories as _record_user_memories_impl
from app_memory_summary import (
    build_memory_buckets,
    build_memory_fact_summary,
    extract_user_preferences,
    summarize_user_message,
)
from app_message_processing import process_user_message


def apply_cross_session_memories(
    char_states: dict,
    cross_session_memories: dict,
    user_name: str,
    *,
    st_module=None,
) -> None:
    _apply_cross_session_memories_impl(
        char_states,
        cross_session_memories,
        user_name,
        st_module=st_module,
    )


def record_user_memories(*, st_module, user_name: str, user_input: str) -> None:
    _record_user_memories_impl(
        st_module=st_module,
        user_name=user_name,
        user_input=user_input,
        summarize_user_message_fn=summarize_user_message,
    )


def record_character_memories(
    *,
    st_module,
    acting_character: str,
    move: dict,
    director_decision: dict,
    build_memory_fact_summary_fn,
    character_names: list[str] | None = None,
    continuity_manager=None,
    display_name_for_key=None,
) -> None:
    names = (
        character_names
        if character_names is not None
        else [
            str(getattr(c, "name", "") or "").strip()
            for c in st_module.session_state.get("characters", [])
            if str(getattr(c, "name", "") or "").strip()
        ]
    )
    _record_character_memories_impl(
        st_module=st_module,
        acting_character=acting_character,
        move=move,
        director_decision=director_decision,
        build_memory_fact_summary_fn=build_memory_fact_summary_fn,
        character_names=names,
        continuity_manager=continuity_manager,
        display_name_for_key=display_name_for_key,
    )


__all__ = [
    "apply_cross_session_memories",
    "build_memory_buckets",
    "build_memory_fact_summary",
    "extract_user_preferences",
    "get_player_control_mode",
    "has_player_character_conflict",
    "load_cross_session_memories",
    "process_user_message",
    "record_character_memories",
    "record_user_memories",
    "resolve_bot_reply_limit",
    "summarize_user_message",
]

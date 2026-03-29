"""Streamlit UI for RP app.

Multi-character roleplay interface with session management.
"""

from typing import Any, Sequence

import streamlit as st
import app_memory_helpers as memory_helpers
import app_state_helpers as state_helpers
import app_turn_helpers as turn_helpers
from audit_logger import get_audit_logger
from app_bootstrap import run_app_startup as run_app_startup_impl
from character_loader import CharacterLoader, make_agent_identifier
from orchestration_helpers import (
    append_turn_to_orchestration_state,
    build_recent_scene_context as build_recent_scene_context_impl,
    choose_fallback_actor as choose_fallback_actor_impl,
    ensure_orchestration_state,
    sync_orchestration_state_from_continuity as sync_orchestration_state_from_continuity_impl,
)
from prompt_builders import (
    build_character_turn_prompt as build_character_turn_prompt_text,
    build_director_selection_prompt,
    build_narrator_render_prompt,
    build_scene_role_prompt_context,
)
from character_state import CharacterState, CharacterStateManager
from continuity_manager import ContinuityManager
from model_client import (
    create_deepseek_client,
    create_director_agent,
    create_narrator_agent,
)
from response_validation import (
    build_attempted_post_details,
    detect_character_drift,
    detect_forced_speaker,
    get_available_actors,
    get_must_remain_characters,
    parse_director_decision,
    parse_character_move,
    validate_bot_response,
    validate_turn_selection_decision,
)
from semantic_validation import (
    assess_narrator_render_semantics,
    assess_presence_violation_semantics,
    assess_turn_selection_decision_semantics,
    reconcile_turn_selection_issues,
    should_override_presence_rejection,
)
from scene_lifecycle import (
    close_active_scene_if_needed as close_active_scene_if_needed_impl,
    end_scene as end_scene_impl,
    get_scene_status as get_scene_status_impl,
    recreate_team_from_state as recreate_team_from_state_impl,
    skip_turn as skip_turn_impl,
    start_scene as start_scene_impl,
)
from scene_opener import OpenerManager, resolve_opening_text, resolve_scene_opener
from cross_session_memory_policy import compact_report_for_audit
from summary_audit_helpers import (
    build_summary_block_audit_metadata,
    get_character_scene_audit_context,
    get_scene_audit_logging_kwargs,
    serialize_canon_anchors_for_prompt,
    serialize_events_for_prompt,
    serialize_summary_blocks_for_prompt,
)
from scene_template import (
    SceneTemplateManager,
    normalize_role_assignments,
    validate_role_assignments,
)
from session_lifecycle import (
    load_existing_session as load_existing_session_impl,
    save_current_session as save_current_session_impl,
)
from session_manager import SessionManager
from turn_runner import run_character_turns as run_character_turns_impl
from ui_rendering import (
    render_chat as render_chat_impl,
    render_sidebar as render_sidebar_impl,
)

PROMPT_DIALOGUE_HISTORY_LIMIT = 6
PROMPT_STRUCTURED_MOVE_LIMIT = 4
DIRECTOR_SPOTLIGHT_HISTORY_LIMIT = 6
ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT = 12
ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT = 8
ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT = 8
ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT = 8
ORCHESTRATION_TENSION_HISTORY_LIMIT = 8


def get_scene_audit_logging_kwargs_for_audit(scene_state: Any | None) -> dict[str, Any]:
    base = get_scene_audit_logging_kwargs(scene_state)
    report = st.session_state.get("cross_session_injection_report")
    if isinstance(report, dict):
        base = dict(base)
        base["cross_session_injection_report"] = compact_report_for_audit(report)
    return base


def get_model_client() -> Any:
    return st.session_state.get("model_client")


def create_selector_func(participant_names: list[str]):
    return turn_helpers.create_selector_func(
        st_module=st,
        participant_names=participant_names,
        detect_forced_speaker_fn=detect_forced_speaker,
        get_character_display_name_fn=get_character_display_name,
    )


def log_turn_failure(
    round_number: int,
    turn_number: int,
    bot_name: str,
    bot_type: str,
    stage: str,
    reason: str,
    input_messages: list[dict[str, Any]] | None = None,
    raw_response: str = "",
    parsed_output: dict[str, Any] | None = None,
    context_snapshot: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    turn_helpers.log_turn_failure(
        st_module=st,
        round_number=round_number,
        turn_number=turn_number,
        bot_name=bot_name,
        bot_type=bot_type,
        stage=stage,
        reason=reason,
        input_messages=input_messages,
        raw_response=raw_response,
        parsed_output=parsed_output,
        context_snapshot=context_snapshot,
        metadata=metadata,
        is_audit_enabled_fn=is_audit_enabled,
        get_audit_logger_fn=get_audit_logger,
        get_audit_context_fn=get_audit_context,
        build_attempted_post_details_fn=build_attempted_post_details,
        get_continuity_manager_fn=get_continuity_manager,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_for_audit,
        get_character_scene_audit_context_fn=get_character_scene_audit_context,
    )


# ============================================================================
# Narrator-Mediated Architecture - Character Move Processing
# ============================================================================


def get_player_control_mode(player_character: str | None) -> str:
    return memory_helpers.get_player_control_mode(player_character)


def has_player_character_conflict(
    selected_chars: list[str], player_character: str | None
) -> bool:
    return memory_helpers.has_player_character_conflict(
        selected_chars, player_character
    )


def resolve_bot_reply_limit(active_bot_count: int, configured_limit: int | None) -> int:
    return memory_helpers.resolve_bot_reply_limit(active_bot_count, configured_limit)


def get_current_bot_reply_limit(active_bot_count: int) -> int:
    return state_helpers.get_current_bot_reply_limit(
        st_module=st,
        active_bot_count=active_bot_count,
        get_bot_reply_limit_widget_key_fn=get_bot_reply_limit_widget_key,
        resolve_bot_reply_limit_fn=resolve_bot_reply_limit,
    )


def get_bot_reply_limit_widget_key() -> str:
    return state_helpers.get_bot_reply_limit_widget_key(st_module=st)


def init_session_state() -> None:
    state_helpers.init_session_state(st_module=st)


def is_audit_enabled() -> bool:
    return state_helpers.is_audit_enabled(st_module=st)


def refresh_audit_summary_report() -> None:
    state_helpers.refresh_audit_summary_report(
        st_module=st,
        is_audit_enabled_fn=is_audit_enabled,
        get_audit_logger_fn=get_audit_logger,
        get_audit_context_fn=get_audit_context,
    )


def get_orchestration_state() -> dict[str, Any]:
    return state_helpers.get_orchestration_state(
        st_module=st,
        ensure_orchestration_state_fn=ensure_orchestration_state,
    )


def apply_scene_setup_to_scene_state(
    scene_state: Any,
    scene_setup: dict[str, Any] | None,
) -> None:
    state_helpers.apply_scene_setup_to_scene_state(
        scene_state=scene_state,
        scene_setup=scene_setup,
        get_must_remain_characters_fn=get_must_remain_characters,
    )


def enforce_must_remain_presence() -> None:
    state_helpers.enforce_must_remain_presence(
        st_module=st,
        get_continuity_manager_fn=get_continuity_manager,
        get_must_remain_characters_fn=get_must_remain_characters,
        get_orchestration_state_fn=get_orchestration_state,
    )


def resolve_scene_template_setup(
    selected_chars: list[str],
    character_names_by_file: dict[str, str],
) -> tuple[dict[str, Any] | None, str]:
    return state_helpers.resolve_scene_template_setup(
        st_module=st,
        selected_chars=selected_chars,
        character_names_by_file=character_names_by_file,
        scene_template_manager_cls=SceneTemplateManager,
        normalize_role_assignments_fn=normalize_role_assignments,
        validate_role_assignments_fn=validate_role_assignments,
    )


def build_recent_dialogue_history(
    chat_history: list[dict[str, Any]], limit: int = PROMPT_DIALOGUE_HISTORY_LIMIT
) -> list[dict[str, str]]:
    return turn_helpers.build_recent_dialogue_history(
        chat_history=chat_history,
        get_character_display_name_fn=get_character_display_name,
        limit=limit,
    )


def get_audit_context() -> tuple[str, int, int, int]:
    return state_helpers.get_audit_context(
        st_module=st,
        is_audit_enabled_fn=is_audit_enabled,
        get_audit_logger_fn=get_audit_logger,
    )


def start_audit_round() -> int:
    return state_helpers.start_audit_round(st_module=st)


def set_audit_turn(turn_number: int) -> int:
    return state_helpers.set_audit_turn(st_module=st, turn_number=turn_number)


def reset_state_for_new_scene() -> None:
    state_helpers.reset_state_for_new_scene(
        st_module=st,
        get_audit_logger_fn=get_audit_logger,
        is_audit_enabled_fn=is_audit_enabled,
    )


async def shutdown_runtime_resources() -> None:
    await state_helpers.shutdown_runtime_resources(
        st_module=st,
        reset_agents_fn=reset_agents,
    )


async def reset_agents(agents: Sequence[Any], reset_token=None) -> None:
    await state_helpers.reset_agents(agents, reset_token)


def get_available_characters() -> list[str]:
    return state_helpers.get_available_characters(character_loader_cls=CharacterLoader)


def resolve_character_file(loader: CharacterLoader, identifier: str) -> str | None:
    return state_helpers.resolve_character_file(
        loader=loader,
        identifier=identifier,
        make_agent_identifier_fn=make_agent_identifier,
    )


def get_character_display_name(identifier: str) -> str:
    return state_helpers.get_character_display_name(
        st_module=st,
        identifier=identifier,
        character_state_cls=CharacterState,
        character_loader_cls=CharacterLoader,
        resolve_character_file_fn=resolve_character_file,
    )


def get_character_display_names(identifiers: list[str]) -> list[str]:
    return state_helpers.get_character_display_names(
        identifiers=identifiers,
        get_character_display_name_fn=get_character_display_name,
    )


def rebuild_character_agents(model_client) -> list[Any]:
    return state_helpers.rebuild_character_agents(
        st_module=st,
        model_client=model_client,
        character_loader_cls=CharacterLoader,
        resolve_character_file_fn=resolve_character_file,
    )


def get_continuity_manager() -> ContinuityManager | None:
    return state_helpers.get_continuity_manager(
        st_module=st,
        continuity_manager_cls=ContinuityManager,
    )


def sync_orchestration_state_from_continuity() -> None:
    state_helpers.sync_orchestration_state_from_continuity(
        st_module=st,
        get_continuity_manager_fn=get_continuity_manager,
        get_orchestration_state_fn=get_orchestration_state,
        sync_orchestration_state_from_continuity_impl_fn=sync_orchestration_state_from_continuity_impl,
        enforce_must_remain_presence_fn=enforce_must_remain_presence,
    )


def restore_or_initialize_continuity_manager(
    continuity_state: dict[str, Any] | None,
    character_names: list[str],
    opening_description: str = "",
    scene_setup: dict[str, Any] | None = None,
) -> ContinuityManager:
    return state_helpers.restore_or_initialize_continuity_manager(
        st_module=st,
        continuity_state=continuity_state,
        character_names=character_names,
        opening_description=opening_description,
        scene_setup=scene_setup,
        continuity_manager_cls=ContinuityManager,
        build_initial_scene_issues_fn=state_helpers.build_initial_scene_issues,
        apply_scene_setup_to_scene_state_fn=apply_scene_setup_to_scene_state,
        sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity,
    )


def choose_fallback_actor(
    available_actors: list[str],
    forced_speaker: str | None,
    *,
    prefer_continuing_spotlight: bool = False,
) -> str | None:
    return turn_helpers.choose_fallback_actor(
        available_actors=available_actors,
        forced_speaker=forced_speaker,
        spotlight_history=get_orchestration_state().get("spotlight_history", []),
        choose_fallback_actor_impl_fn=choose_fallback_actor_impl,
        prefer_continuing_spotlight=prefer_continuing_spotlight,
    )


async def choose_next_actor(
    director,
    participant_names: list[str],
    trigger_text: str,
    cancellation_token,
    round_number: int,
    turn_number: int,
    available_actors: list[str] | None = None,
    continuation_override_actor: str | None = None,
) -> dict[str, Any]:
    return await turn_helpers.choose_next_actor(
        st_module=st,
        director=director,
        get_model_client_fn=get_model_client,
        participant_names=participant_names,
        trigger_text=trigger_text,
        cancellation_token=cancellation_token,
        round_number=round_number,
        turn_number=turn_number,
        available_actors=available_actors,
        continuation_override_actor=continuation_override_actor,
        enforce_must_remain_presence_fn=enforce_must_remain_presence,
        get_orchestration_state_fn=get_orchestration_state,
        get_continuity_manager_fn=get_continuity_manager,
        build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
        serialize_summary_blocks_for_prompt_fn=serialize_summary_blocks_for_prompt,
        build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata,
        serialize_events_for_prompt_fn=serialize_events_for_prompt,
        serialize_canon_anchors_for_prompt_fn=serialize_canon_anchors_for_prompt,
        build_director_selection_prompt_fn=build_director_selection_prompt,
        parse_director_decision_fn=parse_director_decision,
        choose_fallback_actor_fn=choose_fallback_actor,
        validate_turn_selection_decision_fn=validate_turn_selection_decision,
        assess_turn_selection_decision_semantics_fn=assess_turn_selection_decision_semantics,
        reconcile_turn_selection_issues_fn=reconcile_turn_selection_issues,
        is_audit_enabled_fn=is_audit_enabled,
        get_audit_logger_fn=get_audit_logger,
        get_audit_context_fn=get_audit_context,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_for_audit,
        refresh_audit_summary_report_fn=refresh_audit_summary_report,
        build_recent_dialogue_history_fn=build_recent_dialogue_history,
        prompt_dialogue_history_limit=PROMPT_DIALOGUE_HISTORY_LIMIT,
        director_spotlight_history_limit=DIRECTOR_SPOTLIGHT_HISTORY_LIMIT,
    )


def build_character_turn_prompt(
    char_name: str,
    user_name: str,
    trigger_text: str,
    director_decision: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    return turn_helpers.build_character_turn_prompt(
        st_module=st,
        char_name=char_name,
        user_name=user_name,
        trigger_text=trigger_text,
        director_decision=director_decision,
        enforce_must_remain_presence_fn=enforce_must_remain_presence,
        get_orchestration_state_fn=get_orchestration_state,
        get_continuity_manager_fn=get_continuity_manager,
        build_recent_dialogue_history_fn=build_recent_dialogue_history,
        serialize_events_for_prompt_fn=serialize_events_for_prompt,
        serialize_canon_anchors_for_prompt_fn=serialize_canon_anchors_for_prompt,
        serialize_summary_blocks_for_prompt_fn=serialize_summary_blocks_for_prompt,
        build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata,
        build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
        build_character_turn_prompt_text_fn=build_character_turn_prompt_text,
        prompt_structured_move_limit=PROMPT_STRUCTURED_MOVE_LIMIT,
        get_character_display_name_fn=get_character_display_name,
    )


def fallback_render_move(
    char_name: str, move: dict[str, Any], director_decision: dict[str, Any]
) -> str:
    return turn_helpers.fallback_render_move(char_name, move, director_decision)


async def render_character_move(
    narrator,
    char_name: str,
    move: dict[str, Any],
    scene_context: str,
    director_decision: dict[str, Any],
    cancellation_token,
    beat_shift_narrator_suffix: str = "",
) -> tuple[str, str, str]:
    return await turn_helpers.render_character_move(
        narrator=narrator,
        char_name=char_name,
        move=move,
        scene_context=scene_context,
        director_decision=director_decision,
        cancellation_token=cancellation_token,
        build_narrator_render_prompt_fn=build_narrator_render_prompt,
        fallback_render_move_fn=fallback_render_move,
        beat_shift_narrator_suffix=beat_shift_narrator_suffix,
    )


def build_recent_scene_context(
    chat_history: list[dict[str, Any]],
    orchestration_state: dict[str, Any],
    limit: int = 6,
) -> tuple[str, dict[str, Any]]:
    return turn_helpers.build_recent_scene_context(
        chat_history=chat_history,
        orchestration_state=orchestration_state,
        get_continuity_manager_fn=get_continuity_manager,
        build_recent_dialogue_history_fn=build_recent_dialogue_history,
        build_recent_scene_context_impl_fn=build_recent_scene_context_impl,
        limit=limit,
    )


def build_memory_fact_summary(
    acting_character: str,
    move: dict[str, Any],
) -> str:
    return memory_helpers.build_memory_fact_summary(acting_character, move)


def summarize_user_message(user_name: str, user_input: str) -> str:
    return memory_helpers.summarize_user_message(user_name, user_input)


def extract_user_preferences(
    chat_history: list[dict[str, Any]], user_name: str
) -> list[str]:
    return memory_helpers.extract_user_preferences(chat_history, user_name)


def build_memory_buckets(
    summary: str,
    continuity_manager: ContinuityManager | None,
    chat_history: list[dict[str, Any]],
    user_name: str,
) -> dict[str, Any]:
    return memory_helpers.build_memory_buckets(
        summary=summary,
        continuity_manager=continuity_manager,
        chat_history=chat_history,
        user_name=user_name,
    )


def load_cross_session_memories(
    character_names: list[str], user_name: str
) -> dict[str, Any]:
    return memory_helpers.load_cross_session_memories(
        st_module=st,
        character_names=character_names,
        user_name=user_name,
        session_manager_cls=SessionManager,
    )


def apply_cross_session_memories(
    char_states: dict[str, CharacterState],
    cross_session_memories: dict[str, Any],
    user_name: str,
) -> None:
    memory_helpers.apply_cross_session_memories(
        char_states,
        cross_session_memories,
        user_name,
        st_module=st,
    )


def record_user_memories(user_name: str, user_input: str) -> None:
    memory_helpers.record_user_memories(
        st_module=st,
        user_name=user_name,
        user_input=user_input,
    )


def record_character_memories(
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
) -> None:
    memory_helpers.record_character_memories(
        st_module=st,
        acting_character=acting_character,
        move=move,
        director_decision=director_decision,
        build_memory_fact_summary_fn=build_memory_fact_summary,
    )


async def start_scene(selected_chars: list[str]) -> bool:
    return await start_scene_impl(
        st_module=st,
        selected_chars=selected_chars,
        has_player_character_conflict_fn=has_player_character_conflict,
        close_active_scene_if_needed_fn=close_active_scene_if_needed,
        shutdown_runtime_resources_fn=shutdown_runtime_resources,
        reset_state_for_new_scene_fn=reset_state_for_new_scene,
        create_deepseek_client_fn=create_deepseek_client,
        character_loader_cls=CharacterLoader,
        resolve_scene_template_setup_fn=resolve_scene_template_setup,
        resolve_bot_reply_limit_fn=resolve_bot_reply_limit,
        get_character_display_names_fn=get_character_display_names,
        restore_or_initialize_continuity_manager_fn=restore_or_initialize_continuity_manager,
        character_state_manager_cls=CharacterStateManager,
        load_cross_session_memories_fn=load_cross_session_memories,
        apply_cross_session_memories_fn=apply_cross_session_memories,
        get_continuity_manager_fn=get_continuity_manager,
        create_narrator_agent_fn=create_narrator_agent,
        create_director_agent_fn=create_director_agent,
        session_manager_cls=SessionManager,
        opener_manager_cls=OpenerManager,
        resolve_scene_opener_fn=resolve_scene_opener,
        resolve_opening_text_fn=resolve_opening_text,
        is_audit_enabled_fn=is_audit_enabled,
        get_audit_logger_fn=get_audit_logger,
        get_audit_context_fn=get_audit_context,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_for_audit,
        refresh_audit_summary_report_fn=refresh_audit_summary_report,
        run_character_turns_fn=run_character_turns,
        save_current_session_fn=save_current_session,
        apply_scene_setup_to_scene_state_fn=apply_scene_setup_to_scene_state,
        sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity,
        get_orchestration_state_fn=get_orchestration_state,
        build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
    )


async def run_character_turns(
    char_agents: list[Any],
    narrator,
    director,
    trigger_text: str,
    user_name: str,
    max_turns: int | None = None,
) -> None:
    """Run character turns with Director selection and Narrator rendering."""
    await run_character_turns_impl(
        st_module=st,
        char_agents=char_agents,
        narrator=narrator,
        director=director,
        trigger_text=trigger_text,
        user_name=user_name,
        max_turns=max_turns,
        get_orchestration_state_fn=get_orchestration_state,
        start_audit_round_fn=start_audit_round,
        resolve_bot_reply_limit_fn=resolve_bot_reply_limit,
        get_current_bot_reply_limit_fn=get_current_bot_reply_limit,
        get_available_actors_fn=get_available_actors,
        set_audit_turn_fn=set_audit_turn,
        choose_next_actor_fn=choose_next_actor,
        log_turn_failure_fn=log_turn_failure,
        build_character_turn_prompt_fn=build_character_turn_prompt,
        parse_character_move_fn=parse_character_move,
        is_audit_enabled_fn=is_audit_enabled,
        get_audit_logger_fn=get_audit_logger,
        get_audit_context_fn=get_audit_context,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_for_audit,
        get_character_scene_audit_context_fn=get_character_scene_audit_context,
        get_continuity_manager_fn=get_continuity_manager,
        get_model_client_fn=get_model_client,
        validate_bot_response_fn=validate_bot_response,
        assess_presence_violation_semantics_fn=assess_presence_violation_semantics,
        should_override_presence_rejection_fn=should_override_presence_rejection,
        build_recent_scene_context_fn=build_recent_scene_context,
        render_character_move_fn=render_character_move,
        fallback_render_move_fn=fallback_render_move,
        assess_narrator_render_semantics_fn=assess_narrator_render_semantics,
        record_character_memories_fn=record_character_memories,
        sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity,
        refresh_audit_summary_report_fn=refresh_audit_summary_report,
        reset_agents_fn=reset_agents,
        get_character_display_name_fn=get_character_display_name,
        append_turn_to_orchestration_state_fn=append_turn_to_orchestration_state,
        spotlight_history_limit=ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT,
        structured_move_history_limit=ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT,
        director_decision_history_limit=ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT,
        environment_history_limit=ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT,
        tension_history_limit=ORCHESTRATION_TENSION_HISTORY_LIMIT,
    )


async def process_user_message(user_input: str) -> None:
    await memory_helpers.process_user_message(
        st_module=st,
        user_input=user_input,
        recreate_team_from_state_fn=recreate_team_from_state,
        detect_forced_speaker_fn=detect_forced_speaker,
        get_character_display_name_fn=get_character_display_name,
        record_user_memories_fn=record_user_memories,
        run_character_turns_fn=run_character_turns,
        save_current_session_fn=save_current_session,
    )


async def recreate_team_from_state():
    return await recreate_team_from_state_impl(
        st_module=st,
        rebuild_character_agents_fn=rebuild_character_agents,
        get_orchestration_state_fn=get_orchestration_state,
        get_continuity_manager_fn=get_continuity_manager,
        restore_or_initialize_continuity_manager_fn=restore_or_initialize_continuity_manager,
        create_narrator_agent_fn=create_narrator_agent,
        create_director_agent_fn=create_director_agent,
    )


def get_scene_status(scene_status: str | None = None) -> str:
    return get_scene_status_impl(
        scene_status=scene_status,
        scene_ended=bool(st.session_state.get("scene_ended")),
        scene_started=bool(st.session_state.get("scene_started")),
    )


async def save_current_session(
    scene_status: str | None = None,
    scene_closed_reason: str | None = None,
) -> None:
    await save_current_session_impl(
        st_module=st,
        scene_status=scene_status,
        scene_closed_reason=scene_closed_reason,
        sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity,
        get_continuity_manager_fn=get_continuity_manager,
        is_audit_enabled_fn=is_audit_enabled,
        get_current_bot_reply_limit_fn=get_current_bot_reply_limit,
        session_manager_cls=SessionManager,
        build_memory_buckets_fn=build_memory_buckets,
        get_player_control_mode_fn=get_player_control_mode,
        get_scene_status_fn=get_scene_status,
    )


async def close_active_scene_if_needed(reason: str) -> None:
    await close_active_scene_if_needed_impl(
        st_module=st,
        reason=reason,
        save_current_session_fn=save_current_session,
    )


async def skip_turn() -> None:
    await skip_turn_impl(
        st_module=st,
        recreate_team_from_state_fn=recreate_team_from_state,
        run_character_turns_fn=run_character_turns,
        save_current_session_fn=save_current_session,
    )


async def end_scene() -> None:
    await end_scene_impl(
        st_module=st,
        save_current_session_fn=save_current_session,
        shutdown_runtime_resources_fn=shutdown_runtime_resources,
    )


def render_chat() -> None:
    render_chat_impl(
        st_module=st,
        process_user_message_fn=process_user_message,
        get_character_display_name_fn=get_character_display_name,
    )


async def load_existing_session(session_id: str) -> None:
    await load_existing_session_impl(
        st_module=st,
        session_id=session_id,
        close_active_scene_if_needed_fn=close_active_scene_if_needed,
        shutdown_runtime_resources_fn=shutdown_runtime_resources,
        session_manager_cls=SessionManager,
        character_loader_cls=CharacterLoader,
        create_deepseek_client_fn=create_deepseek_client,
        character_state_from_dict_fn=CharacterState.from_dict,
        make_agent_identifier_fn=make_agent_identifier,
        resolve_character_file_fn=resolve_character_file,
        load_cross_session_memories_fn=load_cross_session_memories,
        apply_cross_session_memories_fn=apply_cross_session_memories,
        character_state_manager_cls=CharacterStateManager,
        restore_or_initialize_continuity_manager_fn=restore_or_initialize_continuity_manager,
        get_continuity_manager_fn=get_continuity_manager,
        resolve_bot_reply_limit_fn=resolve_bot_reply_limit,
        has_player_character_conflict_fn=has_player_character_conflict,
    )


def render_sidebar() -> None:
    """Render the sidebar with character selection and session management."""
    render_sidebar_impl(
        st_module=st,
        session_manager_cls=SessionManager,
        get_available_characters_fn=get_available_characters,
        character_loader_cls=CharacterLoader,
        has_player_character_conflict_fn=has_player_character_conflict,
        resolve_bot_reply_limit_fn=resolve_bot_reply_limit,
        scene_template_manager_cls=SceneTemplateManager,
        opener_manager_cls=OpenerManager,
        resolve_character_file_fn=resolve_character_file,
        start_scene_fn=start_scene,
        skip_turn_fn=skip_turn,
        end_scene_fn=end_scene,
    )


def run_app_startup() -> None:
    run_app_startup_impl(
        st_module=st,
        session_manager_cls=SessionManager,
        load_existing_session_fn=load_existing_session,
    )


def main() -> None:
    """Main entry point for the RP app."""
    st.set_page_config(
        page_title="RP App",
        page_icon="🎭",
        layout="wide",
    )

    init_session_state()
    run_app_startup()

    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()

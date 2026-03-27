from typing import Any, Awaitable, Callable

from turn_runner_audit import refresh_audit_summary_report_if_enabled
from turn_runner_turn import execute_character_turn
from turn_runner_updates import apply_successful_turn_updates
from orchestration_helpers import resolve_continuation_override_actor


async def run_character_turns(
    *,
    st_module: Any,
    char_agents: list[Any],
    narrator: Any,
    director: Any,
    trigger_text: str,
    user_name: str,
    max_turns: int | None,
    get_orchestration_state_fn: Callable[[], dict[str, Any]],
    start_audit_round_fn: Callable[[], int],
    resolve_bot_reply_limit_fn: Callable[[int, int | None], int],
    get_current_bot_reply_limit_fn: Callable[[int], int],
    get_available_actors_fn: Callable[
        [list[str], list[str], list[str] | None], list[str]
    ],
    set_audit_turn_fn: Callable[[int], int],
    choose_next_actor_fn: Callable[..., Awaitable[dict[str, Any]]],
    log_turn_failure_fn: Callable[..., None],
    build_character_turn_prompt_fn: Callable[
        [str, str, str, dict[str, Any]], tuple[str, dict[str, Any]]
    ],
    parse_character_move_fn: Callable[[str], tuple[dict[str, Any] | None, str]],
    is_audit_enabled_fn: Callable[[], bool],
    get_audit_logger_fn: Callable[[], Any],
    get_audit_context_fn: Callable[[], tuple[str, int, int, int]],
    get_scene_audit_logging_kwargs_fn: Callable[[Any | None], dict[str, Any]],
    get_character_scene_audit_context_fn: Callable[
        [str, dict[str, Any] | None], dict[str, str]
    ],
    get_continuity_manager_fn: Callable[[], Any],
    get_model_client_fn: Callable[[], Any],
    validate_bot_response_fn: Callable[..., tuple[bool, str]],
    assess_presence_violation_semantics_fn: Callable[
        ..., Awaitable[dict[str, Any] | None]
    ],
    should_override_presence_rejection_fn: Callable[[str, dict[str, Any] | None], bool],
    build_recent_scene_context_fn: Callable[
        [list[dict[str, Any]], dict[str, Any]], tuple[str, dict[str, Any]]
    ],
    render_character_move_fn: Callable[..., Awaitable[tuple[str, str, str]]],
    fallback_render_move_fn: Callable[[str, dict[str, Any], dict[str, Any]], str],
    assess_narrator_render_semantics_fn: Callable[
        ..., Awaitable[dict[str, Any] | None]
    ],
    record_character_memories_fn: Callable[[str, dict[str, Any], dict[str, Any]], None],
    sync_orchestration_state_from_continuity_fn: Callable[[], None],
    refresh_audit_summary_report_fn: Callable[[], None],
    reset_agents_fn: Callable[..., Awaitable[None]],
    get_character_display_name_fn: Callable[[str], str],
    append_turn_to_orchestration_state_fn: Callable[..., dict[str, Any]],
    spotlight_history_limit: int,
    structured_move_history_limit: int,
    director_decision_history_limit: int,
    environment_history_limit: int,
    tension_history_limit: int,
) -> None:
    from autogen_core import CancellationToken

    char_names = [agent.name for agent in char_agents]
    agent_lookup = {agent.name: agent for agent in char_agents}
    state_manager = st_module.session_state.get("character_state_manager")
    cancellation_token = CancellationToken()
    orchestration_state = get_orchestration_state_fn()
    round_number = start_audit_round_fn()
    turn_limit = resolve_bot_reply_limit_fn(
        len(char_agents),
        (
            max_turns
            if max_turns is not None
            else get_current_bot_reply_limit_fn(len(char_agents))
        ),
    )
    actors_used_this_round: list[str] = []

    actors_failed_this_round: list[str] = []
    successful_turns = 0
    attempt_count = 0
    max_attempts = max(len(char_names), 1) * max(turn_limit, 1)

    try:
        with st_module.spinner("Characters are responding..."):
            while successful_turns < turn_limit and attempt_count < max_attempts:
                attempt_count += 1
                continuity_manager = get_continuity_manager_fn()
                eligible_participants: list[str] | None = None
                continuity_scene_state = getattr(
                    continuity_manager, "scene_state", None
                )
                if continuity_scene_state is not None:
                    eligible_participants = [
                        name
                        for name in getattr(
                            continuity_scene_state, "present_characters", []
                        )
                        if name in char_names
                    ]
                elif isinstance(
                    orchestration_state.get("scene_state", {}), dict
                ) and isinstance(
                    orchestration_state.get("scene_state", {}).get(
                        "present_characters"
                    ),
                    list,
                ):
                    eligible_participants = [
                        name
                        for name in orchestration_state.get("scene_state", {}).get(
                            "present_characters", []
                        )
                        if name in char_names
                    ]
                available_actors = get_available_actors_fn(
                    char_names,
                    actors_used_this_round + actors_failed_this_round,
                    eligible_participants,
                )
                continuation_override_actor = resolve_continuation_override_actor(
                    orchestration_state=orchestration_state,
                    continuity_manager=continuity_manager,
                    eligible_participants=eligible_participants,
                    actors_used_this_round=actors_used_this_round,
                )
                if not available_actors:
                    break

                turn_number = set_audit_turn_fn(successful_turns + 1)

                decision = await choose_next_actor_fn(
                    director=director,
                    participant_names=char_names,
                    trigger_text=trigger_text,
                    cancellation_token=cancellation_token,
                    round_number=round_number,
                    turn_number=turn_number,
                    available_actors=available_actors,
                    continuation_override_actor=continuation_override_actor,
                )
                next_actor = str(decision.get("next_actor", "") or "")

                if bool(decision.get("end_round")):
                    break

                if not next_actor:
                    log_turn_failure_fn(
                        round_number=round_number,
                        turn_number=turn_number,
                        bot_name="director",
                        bot_type="director",
                        stage="selection",
                        reason="Director did not return a valid next_actor",
                        parsed_output=decision,
                        context_snapshot={
                            "available_actors": available_actors,
                            "character_names": char_names,
                        },
                    )
                    break

                agent = agent_lookup.get(next_actor)

                if agent is None:
                    actors_failed_this_round.append(next_actor)
                    log_turn_failure_fn(
                        round_number=round_number,
                        turn_number=turn_number,
                        bot_name=next_actor,
                        bot_type="character",
                        stage="selection",
                        reason="Director selected an actor that could not be resolved to a live agent",
                        parsed_output=decision,
                        context_snapshot={
                            "available_actors": available_actors,
                            "character_names": char_names,
                        },
                    )
                    continue

                turn_result = await execute_character_turn(
                    st_module=st_module,
                    agent=agent,
                    narrator=narrator,
                    next_actor=next_actor,
                    char_names=char_names,
                    decision=decision,
                    trigger_text=trigger_text,
                    user_name=user_name,
                    cancellation_token=cancellation_token,
                    round_number=round_number,
                    turn_number=turn_number,
                    orchestration_state=orchestration_state,
                    actors_failed_this_round=actors_failed_this_round,
                    state_manager=state_manager,
                    build_character_turn_prompt_fn=build_character_turn_prompt_fn,
                    parse_character_move_fn=parse_character_move_fn,
                    get_continuity_manager_fn=get_continuity_manager_fn,
                    is_audit_enabled_fn=is_audit_enabled_fn,
                    get_audit_logger_fn=get_audit_logger_fn,
                    get_audit_context_fn=get_audit_context_fn,
                    get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
                    get_character_scene_audit_context_fn=get_character_scene_audit_context_fn,
                    validate_bot_response_fn=validate_bot_response_fn,
                    get_model_client_fn=get_model_client_fn,
                    assess_presence_violation_semantics_fn=assess_presence_violation_semantics_fn,
                    should_override_presence_rejection_fn=should_override_presence_rejection_fn,
                    build_recent_scene_context_fn=build_recent_scene_context_fn,
                    render_character_move_fn=render_character_move_fn,
                    fallback_render_move_fn=fallback_render_move_fn,
                    assess_narrator_render_semantics_fn=assess_narrator_render_semantics_fn,
                    log_turn_failure_fn=log_turn_failure_fn,
                    get_character_display_name_fn=get_character_display_name_fn,
                )
                if turn_result is None:
                    continue

                move = turn_result["move"]
                rendered = str(turn_result["rendered"])
                narrator_raw = str(turn_result["narrator_raw"])
                narrator_prompt = str(turn_result["narrator_prompt"])
                narrator_summary_block_audit = turn_result[
                    "narrator_summary_block_audit"
                ]
                narrator_semantic_assessment = turn_result.get(
                    "narrator_semantic_assessment"
                )

                actors_used_this_round.append(next_actor)
                successful_turns += 1

                orchestration_state = apply_successful_turn_updates(
                    st_module=st_module,
                    next_actor=next_actor,
                    char_names=char_names,
                    move=move,
                    decision=decision,
                    rendered=rendered,
                    narrator_raw=narrator_raw,
                    narrator_prompt=narrator_prompt,
                    narrator_summary_block_audit=narrator_summary_block_audit,
                    narrator_semantic_assessment=narrator_semantic_assessment,
                    round_number=round_number,
                    turn_number=turn_number,
                    state_manager=state_manager,
                    record_character_memories_fn=record_character_memories_fn,
                    sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity_fn,
                    is_audit_enabled_fn=is_audit_enabled_fn,
                    get_audit_logger_fn=get_audit_logger_fn,
                    get_audit_context_fn=get_audit_context_fn,
                    get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
                    get_character_scene_audit_context_fn=get_character_scene_audit_context_fn,
                    append_turn_to_orchestration_state_fn=append_turn_to_orchestration_state_fn,
                    orchestration_state=orchestration_state,
                    spotlight_history_limit=spotlight_history_limit,
                    structured_move_history_limit=structured_move_history_limit,
                    director_decision_history_limit=director_decision_history_limit,
                    environment_history_limit=environment_history_limit,
                    tension_history_limit=tension_history_limit,
                )

        refresh_audit_summary_report_if_enabled(
            is_audit_enabled_fn=is_audit_enabled_fn,
            refresh_audit_summary_report_fn=refresh_audit_summary_report_fn,
        )
    finally:
        await reset_agents_fn([narrator, director], cancellation_token)

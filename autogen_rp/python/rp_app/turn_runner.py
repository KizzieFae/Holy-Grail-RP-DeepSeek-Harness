from collections.abc import Callable
from typing import Any, Awaitable

from beat_shift_state import maybe_activate_pending_beat_shift
from turn_runner_audit import refresh_audit_summary_report_if_enabled
from turn_runner_turn import execute_character_turn
from turn_runner_updates import apply_successful_turn_updates
from orchestration_helpers import resolve_continuation_override_actor
from response_validation_selection import eligible_agent_keys_for_present_characters


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
        [list[str], list[str], list[str] | None, list[str] | None], list[str]
    ],
    set_audit_turn_fn: Callable[[int], int],
    choose_next_actor_fn: Callable[..., Awaitable[dict[str, Any]]],
    log_turn_failure_fn: Callable[..., None],
    build_character_turn_prompt_fn: Callable[
        [str, str, str, dict[str, Any]], tuple[str, dict[str, Any]]
    ],
    parse_character_move_fn: Callable[[str], tuple[dict[str, Any] | None, str]],
    is_audit_enabled_fn: Callable[[], bool],
    is_llm_audit_enabled_fn: Callable[[], bool],
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
    render_character_move_fn: Callable[..., Awaitable[tuple[str, str, str, bool]]],
    fallback_render_move_fn: Callable[[str, dict[str, Any], dict[str, Any]], str],
    assess_narrator_render_semantics_fn: Callable[
        ..., Awaitable[dict[str, Any] | None]
    ],
    record_character_memories_fn: Callable[..., None],
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
    ignore_director_end_round: bool = False,
    get_effective_user_trigger: Callable[[int], str] | None = None,
) -> None:
    from autogen_core import CancellationToken

    from user_presence_signals import (
        apply_user_trigger_to_offstage,
        release_pending_forced_speaker_from_offstage,
    )

    resolve_effective_user_trigger: Callable[[int], str]
    if get_effective_user_trigger is not None:
        resolve_effective_user_trigger = get_effective_user_trigger
    else:

        def resolve_effective_user_trigger(n: int) -> str:  # noqa: ARG001
            return trigger_text

    char_names = [agent.name for agent in char_agents]
    agent_lookup = {agent.name: agent for agent in char_agents}
    state_manager = st_module.session_state.get("character_state_manager")
    cancellation_token = CancellationToken()
    orchestration_state = get_orchestration_state_fn()
    round_number = start_audit_round_fn()
    active_issue_dicts: list[dict[str, Any]] = []
    cm_pre = get_continuity_manager_fn()
    if cm_pre is not None:
        for iss in cm_pre.get_active_issues(limit=24):
            if hasattr(iss, "to_dict"):
                active_issue_dicts.append(iss.to_dict())
    recent_moves_for_stall = orchestration_state.get("recent_structured_moves")
    if not isinstance(recent_moves_for_stall, list):
        recent_moves_for_stall = []
    maybe_activate_pending_beat_shift(
        orchestration_state,
        trigger_text=resolve_effective_user_trigger(1),
        source_turn_id=f"user_round_{round_number}",
        active_issues=active_issue_dicts,
        recent_structured_moves=list(recent_moves_for_stall),
    )
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

    continuity_pre = get_continuity_manager_fn()
    if continuity_pre is not None and continuity_pre.scene_state is not None:
        apply_user_trigger_to_offstage(
            scene_state=continuity_pre.scene_state,
            trigger_text=resolve_effective_user_trigger(1),
            participant_names=char_names,
            get_character_display_name_fn=get_character_display_name_fn,
        )
        release_pending_forced_speaker_from_offstage(
            scene_state=continuity_pre.scene_state,
            pending_forced_speaker=st_module.session_state.get(
                "pending_forced_speaker"
            ),
            participant_names=char_names,
        )

    try:
        with st_module.spinner("Characters are responding..."):
            while successful_turns < turn_limit and attempt_count < max_attempts:
                attempt_count += 1
                if st_module.session_state.get("issue29_long_run_harness"):
                    au = actors_used_this_round
                    st_module.session_state["issue29_actors_used_this_round_tail"] = (
                        str(au[-1]) if au else None
                    )
                continuity_manager = get_continuity_manager_fn()
                eligible_participants: list[str] = []
                continuity_scene_state = getattr(
                    continuity_manager, "scene_state", None
                )
                if continuity_scene_state is not None:
                    eligible_participants = eligible_agent_keys_for_present_characters(
                        list(
                            getattr(
                                continuity_scene_state, "present_characters", []
                            )
                            or []
                        ),
                        char_names,
                        display_name_for_key=get_character_display_name_fn,
                    )
                elif isinstance(
                    orchestration_state.get("scene_state", {}), dict
                ) and isinstance(
                    orchestration_state.get("scene_state", {}).get(
                        "present_characters"
                    ),
                    list,
                ):
                    eligible_participants = eligible_agent_keys_for_present_characters(
                        list(
                            orchestration_state.get("scene_state", {}).get(
                                "present_characters", []
                            )
                            or []
                        ),
                        char_names,
                        display_name_for_key=get_character_display_name_fn,
                    )
                offstage_list: list[str] = []
                if continuity_scene_state is not None:
                    offstage_list = list(
                        getattr(continuity_scene_state, "offstage_characters", [])
                        or []
                    )
                available_actors = get_available_actors_fn(
                    char_names,
                    actors_used_this_round + actors_failed_this_round,
                    eligible_participants,
                    offstage_list,
                )
                continuation_override_actor = resolve_continuation_override_actor(
                    orchestration_state=orchestration_state,
                    continuity_manager=continuity_manager,
                    eligible_participants=eligible_participants,
                    actors_used_this_round=actors_used_this_round,
                    offstage_characters=offstage_list,
                )
                if not available_actors:
                    break

                turn_number = set_audit_turn_fn(successful_turns + 1)
                effective_user_trigger = resolve_effective_user_trigger(turn_number)

                decision = await choose_next_actor_fn(
                    director=director,
                    participant_names=char_names,
                    trigger_text=effective_user_trigger,
                    cancellation_token=cancellation_token,
                    round_number=round_number,
                    turn_number=turn_number,
                    available_actors=available_actors,
                    continuation_override_actor=continuation_override_actor,
                    actors_used_this_round=list(actors_used_this_round),
                )
                if not isinstance(decision, dict):
                    decision = {}
                else:
                    decision = dict(decision)

                # Headless Issue #29 harness: Director may end_round early while investigation
                # still requires N character turns. When enabled, clear end_round and pick a
                # fallback actor if needed (production / Streamlit default: unchanged).
                if ignore_director_end_round and bool(decision.get("end_round")):
                    decision["end_round"] = False
                    if not str(decision.get("next_actor", "") or "").strip() and available_actors:
                        decision["next_actor"] = available_actors[0]

                if st_module.session_state.get("issue29_long_run_harness"):
                    na_pre = str(decision.get("next_actor", "") or "").strip()
                    if (
                        not na_pre
                        and available_actors
                        and not bool(decision.get("end_round"))
                    ):
                        decision["next_actor"] = available_actors[0]

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
                        effective_user_trigger=effective_user_trigger,
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
                        effective_user_trigger=effective_user_trigger,
                    )
                    continue

                turn_result = await execute_character_turn(
                    st_module=st_module,
                    agent=agent,
                    narrator=narrator,
                    next_actor=next_actor,
                    char_names=char_names,
                    decision=decision,
                    trigger_text=effective_user_trigger,
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
                    is_llm_audit_enabled_fn=is_llm_audit_enabled_fn,
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
                    sync_orchestration_state_from_continuity_fn=sync_orchestration_state_from_continuity_fn,
                    effective_user_trigger=effective_user_trigger,
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
                narrator_output_audit_v1 = turn_result["narrator_output_audit_v1"]
                narrator_validation_audit_v1 = turn_result["narrator_validation_audit_v1"]
                prose_dialogue_audit_v1 = turn_result["prose_dialogue_audit_v1"]
                audit_v2_narrator = turn_result.get("audit_v2_narrator")
                skip_continuity_process_turn = bool(
                    turn_result.get("continuity_applied_in_execute", False)
                )

                actors_used_this_round.append(next_actor)
                successful_turns += 1
                if st_module.session_state.get("issue29_long_run_harness"):
                    st_module.session_state["issue29_last_successful_actor"] = (
                        str(next_actor or "").strip() or None
                    )

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
                    narrator_output_audit_v1=narrator_output_audit_v1,
                    narrator_validation_audit_v1=narrator_validation_audit_v1,
                    prose_dialogue_audit_v1=prose_dialogue_audit_v1,
                    audit_v2_narrator=audit_v2_narrator
                    if isinstance(audit_v2_narrator, dict)
                    else None,
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
                    effective_user_trigger=effective_user_trigger,
                    skip_continuity_process_turn=skip_continuity_process_turn,
                )

        refresh_audit_summary_report_if_enabled(
            is_audit_enabled_fn=is_audit_enabled_fn,
            refresh_audit_summary_report_fn=refresh_audit_summary_report_fn,
        )
    finally:
        await reset_agents_fn([narrator, director], cancellation_token)

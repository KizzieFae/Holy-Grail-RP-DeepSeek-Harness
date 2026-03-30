from typing import Any

from autogen_agentchat.messages import TextMessage

from beat_shift_state import build_narrator_beat_shift_suffix, is_pending_beat_shift_active
from anti_regression_advisory import get_cached_anti_regression_advisory
from progression_advisory import get_cached_progression_advisory
from progression_pressure import get_cached_progression_pressure
from turn_runner_audit import log_character_turn_audit


async def execute_character_turn(
    *,
    st_module: Any,
    agent: Any,
    narrator: Any,
    next_actor: str,
    char_names: list[str],
    decision: dict[str, Any],
    trigger_text: str,
    user_name: str,
    cancellation_token: Any,
    round_number: int,
    turn_number: int,
    orchestration_state: dict[str, Any],
    actors_failed_this_round: list[str],
    state_manager: Any,
    build_character_turn_prompt_fn,
    parse_character_move_fn,
    get_continuity_manager_fn,
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    get_scene_audit_logging_kwargs_fn,
    get_character_scene_audit_context_fn,
    validate_bot_response_fn,
    get_model_client_fn,
    assess_presence_violation_semantics_fn,
    should_override_presence_rejection_fn,
    build_recent_scene_context_fn,
    render_character_move_fn,
    fallback_render_move_fn,
    assess_narrator_render_semantics_fn,
    log_turn_failure_fn,
    get_character_display_name_fn,
) -> dict[str, Any] | None:
    task_prompt, character_summary_block_audit = build_character_turn_prompt_fn(
        next_actor,
        user_name,
        trigger_text,
        decision,
    )
    continuity_manager = get_continuity_manager_fn()
    scene_state = (
        continuity_manager.scene_state.to_dict()
        if continuity_manager is not None and continuity_manager.scene_state is not None
        else orchestration_state.get("scene_state", {})
    )

    move: dict[str, Any] | None = None
    rendered_move_result: dict[str, Any] | None = None
    semantic_presence_assessment = None
    rejection_reason = ""
    duplicate_retry_triggered = False
    duplicate_retry_reason = ""

    for attempt_index in range(2):
        attempt_prompt = task_prompt
        if attempt_index == 1:
            attempt_prompt = (
                f"{task_prompt}\n\nIMPORTANT: Your previous attempt was rejected as a duplicate. "
                "Write a materially different action/dialogue. Do not repeat previous dialogue verbatim."
            )

        task = TextMessage(content=attempt_prompt, source="system")

        try:
            char_result = await agent.on_messages([task], cancellation_token)
            char_raw_response = char_result.chat_message.content
        except Exception as exc:
            actors_failed_this_round.append(next_actor)
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="generation",
                reason=str(exc),
                input_messages=[{"role": "system", "content": attempt_prompt}],
                parsed_output=decision,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={"summary_blocks": character_summary_block_audit},
            )
            return None

        move, error = parse_character_move_fn(char_raw_response)
        if error or move is None:
            actors_failed_this_round.append(next_actor)
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="parse",
                reason=error or "Character move could not be parsed",
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=decision,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={"summary_blocks": character_summary_block_audit},
            )
            return None

        move_text = f"{move.get('action', '')} {move.get('dialogue', '')}".strip()
        is_valid, rejection_reason = validate_bot_response_fn(
            move_text,
            next_actor,
            user_name,
            st_module.session_state["chat_history"],
            state_manager.get_state(next_actor) if state_manager else None,
            move,
            (
                continuity_manager.get_relevant_canon_anchors(next_actor)
                if continuity_manager is not None
                else None
            ),
            scene_state,
        )
        semantic_presence_assessment = None

        if not is_valid and rejection_reason.startswith("[SCENE_PRESENCE]"):
            semantic_presence_assessment = await assess_presence_violation_semantics_fn(
                model_client=get_model_client_fn(),
                speaker=next_actor,
                content=move_text,
                move=move,
                scene_state=scene_state,
                rejection_reason=rejection_reason,
                cancellation_token=cancellation_token,
            )
            if should_override_presence_rejection_fn(
                rejection_reason, semantic_presence_assessment
            ):
                is_valid = True
                rejection_reason = ""
                st_module.session_state["selector_decisions"].append(
                    f"Semantic validation kept {next_actor}'s turn after presence review."
                )

        if (
            not is_valid
            and rejection_reason.startswith("[DUPLICATE]")
            and attempt_index == 0
        ):
            duplicate_retry_triggered = True
            duplicate_retry_reason = rejection_reason
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation_duplicate_retry",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={
                    "summary_blocks": character_summary_block_audit,
                    "semantic_presence_assessment": semantic_presence_assessment or {},
                },
            )
            st_module.session_state["selector_decisions"].append(
                f"Retrying {next_actor} after duplicate-output rejection."
            )
            continue

        if not is_valid:
            actors_failed_this_round.append(next_actor)
            log_turn_failure_fn(
                round_number=round_number,
                turn_number=turn_number,
                bot_name=next_actor,
                bot_type="character",
                stage="validation",
                reason=rejection_reason,
                input_messages=[{"role": "system", "content": attempt_prompt}],
                raw_response=char_raw_response,
                parsed_output=move,
                context_snapshot={
                    "director_decision": decision,
                    "character_names": char_names,
                    "attempt_index": attempt_index,
                },
                metadata={
                    "summary_blocks": character_summary_block_audit,
                    "semantic_presence_assessment": semantic_presence_assessment or {},
                },
            )
            return None

        turn_execution_metadata = {
            "attempt_index": attempt_index,
            "duplicate_retry_triggered": duplicate_retry_triggered,
            "duplicate_retry_reason": duplicate_retry_reason,
            "duplicate_retry_outcome": (
                "success_after_retry"
                if duplicate_retry_triggered and attempt_index == 1
                else "no_retry"
            ),
        }

        log_character_turn_audit(
            next_actor=next_actor,
            move=move,
            task_prompt=attempt_prompt,
            char_raw_response=char_raw_response,
            decision=decision,
            char_names=char_names,
            continuity_manager=continuity_manager,
            round_number=round_number,
            turn_number=turn_number,
            character_summary_block_audit=character_summary_block_audit,
            turn_execution_metadata=turn_execution_metadata,
            progression_advisory=get_cached_progression_advisory(orchestration_state),
            progression_pressure=get_cached_progression_pressure(orchestration_state),
            anti_regression_advisory=get_cached_anti_regression_advisory(
                orchestration_state
            ),
            is_audit_enabled_fn=is_audit_enabled_fn,
            get_audit_logger_fn=get_audit_logger_fn,
            get_audit_context_fn=get_audit_context_fn,
            get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
            get_character_scene_audit_context_fn=get_character_scene_audit_context_fn,
        )

        rendered_move_result = {
            "move": move,
            "char_raw_response": char_raw_response,
        }
        break

    if rendered_move_result is None or move is None:
        return None

    scene_context, narrator_summary_block_audit = build_recent_scene_context_fn(
        st_module.session_state["chat_history"],
        orchestration_state,
    )

    beat_shift_narrator_suffix = ""
    if is_pending_beat_shift_active(orchestration_state):
        beat_shift_narrator_suffix = build_narrator_beat_shift_suffix()

    try:
        rendered, narrator_raw, narrator_prompt = await render_character_move_fn(
            narrator,
            next_actor,
            move,
            scene_context,
            decision,
            cancellation_token,
            beat_shift_narrator_suffix=beat_shift_narrator_suffix,
        )
    except Exception as exc:
        actors_failed_this_round.append(next_actor)
        log_turn_failure_fn(
            round_number=round_number,
            turn_number=turn_number,
            bot_name="Narrator",
            bot_type="narrator",
            stage="render",
            reason=str(exc),
            input_messages=[{"role": "system", "content": scene_context}],
            parsed_output={
                "character": next_actor,
                "move": move,
                "director_decision": decision,
            },
            context_snapshot={
                "character": next_actor,
                "action": move.get("action", ""),
                "has_dialogue": bool(move.get("dialogue")),
            },
            metadata={"summary_blocks": narrator_summary_block_audit},
        )
        return None

    narrator_semantic_assessment = await assess_narrator_render_semantics_fn(
        model_client=get_model_client_fn(),
        char_name=next_actor,
        move=move,
        director_decision=decision,
        rendered=rendered,
        scene_context=scene_context,
        cancellation_token=cancellation_token,
    )
    if narrator_semantic_assessment is not None and narrator_semantic_assessment.get(
        "should_use_fallback"
    ):
        rendered = fallback_render_move_fn(next_actor, move, decision)
        st_module.session_state["selector_decisions"].append(
            f"Narrator fallback render used for {next_actor} after semantic review."
        )

    try:
        st_module.session_state["chat_history"].append(
            {
                "role": "assistant",
                "content": rendered,
                "speaker": get_character_display_name_fn(next_actor),
                "move": move,
                "director_decision": decision,
            }
        )
    except Exception as exc:
        actors_failed_this_round.append(next_actor)
        log_turn_failure_fn(
            round_number=round_number,
            turn_number=turn_number,
            bot_name=next_actor,
            bot_type="character",
            stage="chat_append",
            reason=str(exc),
            parsed_output=move,
            context_snapshot={
                "director_decision": decision,
                "rendered": rendered,
            },
        )
        return None

    return {
        "move": move,
        "rendered": rendered,
        "narrator_raw": narrator_raw,
        "narrator_prompt": narrator_prompt,
        "narrator_summary_block_audit": narrator_summary_block_audit,
        "narrator_semantic_assessment": narrator_semantic_assessment,
    }

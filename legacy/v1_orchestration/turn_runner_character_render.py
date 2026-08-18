"""Character-turn render phase: narrator prep, render, semantic review, audits, chat append, rollbacks."""

from typing import Any

from beat_shift_state import build_narrator_beat_shift_suffix, is_pending_beat_shift_active
from continuity_manager import ContinuityManager
from narrator_audits_v1 import (
    build_narrator_output_audit_v1,
    build_narrator_validation_audit_v1,
    build_prose_dialogue_audit_v1,
    prior_assistant_rendered_content,
)
from perception_audibility import (
    filter_structured_move_for_viewer,
    normalize_move_audibility,
    redact_structured_move_for_orchestration,
)
from audit_v2_pipeline import build_audit_v2_narrator_prose_bundle
from turn_runner_character_attempt import CharacterAttemptOutcome


def _narrate_move_for_character_turn(
    move: dict[str, Any],
    *,
    next_actor: str,
    char_names: list[str],
    st_module: Any,
) -> dict[str, Any]:
    """Select structured view for narrator: canonical if no in-scene player POV; else per-recipient (Issue #139)."""
    present = [str(c).strip() for c in char_names if str(c or "").strip()]
    move_norm = normalize_move_audibility(dict(move), next_actor, present)
    player = st_module.session_state.get("player_character")
    if isinstance(player, str) and player.strip() and player.strip() in char_names:
        return filter_structured_move_for_viewer(
            {**move_norm, "speaker": next_actor},
            viewer_character_name=player.strip(),
            present_characters=present,
        )
    return redact_structured_move_for_orchestration(
        move_norm, present_characters=present
    )


async def execute_character_turn_render_phase(
    *,
    st_module: Any,
    narrator: Any,
    next_actor: str,
    char_names: list[str],
    decision: dict[str, Any],
    orchestration_state: dict[str, Any],
    actors_failed_this_round: list[str],
    cancellation_token: Any,
    round_number: int,
    turn_number: int,
    build_recent_scene_context_fn,
    render_character_move_fn,
    fallback_render_move_fn,
    assess_narrator_render_semantics_fn,
    log_turn_failure_fn,
    get_character_display_name_fn,
    get_model_client_fn,
    sync_orchestration_state_from_continuity_fn,
    is_audit_enabled_fn,
    is_llm_audit_enabled_fn,
    effective_user_trigger: str,
    outcome: CharacterAttemptOutcome,
) -> dict[str, Any] | None:
    move = outcome.move
    continuity_applied_in_execute = outcome.continuity_applied_in_execute
    continuity_transaction_snapshot = outcome.continuity_transaction_snapshot
    turn_execution_metadata = outcome.turn_execution_metadata

    narrate_move = _narrate_move_for_character_turn(
        move, next_actor=next_actor, char_names=char_names, st_module=st_module
    )

    scene_context, narrator_summary_block_audit = build_recent_scene_context_fn(
        st_module.session_state["chat_history"],
        orchestration_state,
    )

    beat_shift_narrator_suffix = ""
    if is_pending_beat_shift_active(orchestration_state):
        beat_shift_narrator_suffix = build_narrator_beat_shift_suffix()

    try:
        (
            rendered,
            narrator_raw,
            narrator_prompt,
            deterministic_dialogue_fallback_applied,
        ) = await render_character_move_fn(
            narrator,
            next_actor,
            narrate_move,
            scene_context,
            decision,
            cancellation_token,
            beat_shift_narrator_suffix=beat_shift_narrator_suffix,
        )
        rendered_after_render_call = rendered
    except Exception as exc:
        if continuity_applied_in_execute and continuity_transaction_snapshot is not None:
            st_module.session_state["continuity_manager"] = ContinuityManager.from_dict(
                continuity_transaction_snapshot
            )
            sync_orchestration_state_from_continuity_fn()
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
            effective_user_trigger=effective_user_trigger,
        )
        return None

    narrator_semantic_assessment = await assess_narrator_render_semantics_fn(
        model_client=get_model_client_fn(),
        char_name=next_actor,
        move=narrate_move,
        director_decision=decision,
        rendered=rendered,
        scene_context=scene_context,
        cancellation_token=cancellation_token,
    )
    if narrator_semantic_assessment is None:
        use_narrator_semantic_fallback = False
        semantic_fallback_llm_requested = False
        semantic_fallback_deterministic_critical = False
    else:
        a = narrator_semantic_assessment
        parse_error_nonempty = (str(a.get("parse_error", "") or "").strip() != "")
        valid = bool(a.get("valid", True))
        dialogue_preserved = bool(a.get("dialogue_preserved", True))
        stayed_in_scope = bool(a.get("stayed_in_scope", True))
        deterministic_critical = (
            parse_error_nonempty
            or (not valid)
            or (not dialogue_preserved)
            or (not stayed_in_scope)
        )
        llm_wants_fallback = a.get("should_use_fallback") is True
        use_narrator_semantic_fallback = deterministic_critical or llm_wants_fallback
        semantic_fallback_llm_requested = llm_wants_fallback
        semantic_fallback_deterministic_critical = deterministic_critical

    if use_narrator_semantic_fallback:
        rendered = fallback_render_move_fn(next_actor, narrate_move, decision)
        st_module.session_state["selector_decisions"].append(
            f"Narrator fallback render used for {next_actor} after semantic review."
        )

    rendered_final = rendered
    acting_display = get_character_display_name_fn(next_actor)
    prior_rendered = prior_assistant_rendered_content(
        st_module.session_state["chat_history"]
    )
    narrator_output_audit_v1 = build_narrator_output_audit_v1(
        next_actor=next_actor,
        move=narrate_move,
        decision=decision,
        rendered_final=rendered_final,
        char_names=char_names,
        acting_display_name=acting_display,
    )
    narrator_validation_audit_v1 = build_narrator_validation_audit_v1(
        narrator_raw=narrator_raw,
        rendered_after_render_call=rendered_after_render_call,
        rendered_final=rendered_final,
        deterministic_dialogue_fallback_applied=deterministic_dialogue_fallback_applied,
        narrator_semantic_assessment=narrator_semantic_assessment,
        semantic_fallback_effective=use_narrator_semantic_fallback,
        semantic_fallback_llm_requested=semantic_fallback_llm_requested,
        semantic_fallback_deterministic_critical=semantic_fallback_deterministic_critical,
    )
    prose_dialogue_audit_v1 = build_prose_dialogue_audit_v1(
        next_actor=next_actor,
        move=narrate_move,
        rendered_final=rendered_final,
        prior_assistant_content=prior_rendered,
        acting_display_name=acting_display,
    )

    audit_v2_narrator_metadata: dict[str, Any] | None = None
    if is_audit_enabled_fn():
        nar_v2_bundle = await build_audit_v2_narrator_prose_bundle(
            next_actor=next_actor,
            move=dict(narrate_move),
            decision=decision,
            rendered_final=rendered_final,
            char_names=list(char_names),
            acting_display_name=acting_display,
            prior_assistant_content=prior_rendered,
            llm_audit_enabled=is_llm_audit_enabled_fn(),
            model_client=get_model_client_fn(),
            cancellation_token=cancellation_token,
        )
        audit_v2_narrator_metadata = {
            "schema_version": 1,
            "narrator_output": nar_v2_bundle["narrator_output"],
            "prose_dialogue": nar_v2_bundle["prose_dialogue"],
        }

    try:
        st_module.session_state["chat_history"].append(
            {
                "role": "assistant",
                "content": rendered,
                "speaker": get_character_display_name_fn(next_actor),
                "actor": next_actor,
                "move": move,
                "director_decision": decision,
            }
        )
    except Exception as exc:
        if continuity_applied_in_execute and continuity_transaction_snapshot is not None:
            st_module.session_state["continuity_manager"] = ContinuityManager.from_dict(
                continuity_transaction_snapshot
            )
            sync_orchestration_state_from_continuity_fn()
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
            effective_user_trigger=effective_user_trigger,
        )
        return None

    return {
        "move": move,
        "rendered": rendered,
        "narrator_raw": narrator_raw,
        "narrator_prompt": narrator_prompt,
        "narrator_summary_block_audit": narrator_summary_block_audit,
        "narrator_semantic_assessment": narrator_semantic_assessment,
        "continuity_applied_in_execute": continuity_applied_in_execute,
        "narrator_output_audit_v1": narrator_output_audit_v1,
        "narrator_validation_audit_v1": narrator_validation_audit_v1,
        "prose_dialogue_audit_v1": prose_dialogue_audit_v1,
        "audit_v2_narrator": audit_v2_narrator_metadata,
        "turn_execution_metadata": turn_execution_metadata,
    }

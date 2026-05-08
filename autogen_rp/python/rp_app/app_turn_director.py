from collections.abc import Callable
from typing import Any

from autogen_agentchat.messages import TextMessage

from semantic_validation import substitute_agent_keys_with_display_names

from arch_quality_variants import arch_quality_variant
from beat_shift_state import is_pending_beat_shift_active
from director_prompt_payload import (
    DirectorPromptAssembly,
    _compute_action_responsibility_hint,
    _compute_responder_obligation_hint,
    build_director_prompt_payload,
    split_actionable_and_stalled_issues,
)
from director_selection_postprocess import finalize_director_selection_after_llm
from progression_advisory import sync_progression_advisory_for_prompts
from progression_enforcement import progression_delta_required
from selection_attribution import record_selection_attribution_event

__all__ = [
    "choose_next_actor",
    "split_actionable_and_stalled_issues",
    "_compute_responder_obligation_hint",
    "_compute_action_responsibility_hint",
]


async def choose_next_actor(
    *,
    st_module: Any,
    director,
    get_model_client_fn,
    participant_names: list[str],
    trigger_text: str,
    cancellation_token,
    round_number: int,
    turn_number: int,
    available_actors: list[str],
    continuation_override_actor: str | None,
    actors_used_this_round: list[str] | None = None,
    enforce_must_remain_presence_fn,
    get_orchestration_state_fn,
    get_continuity_manager_fn,
    build_scene_role_prompt_context_fn,
    serialize_summary_blocks_for_prompt_fn,
    build_summary_block_audit_metadata_fn,
    serialize_events_for_prompt_fn,
    serialize_canon_anchors_for_prompt_fn,
    build_director_selection_prompt_fn,
    parse_director_decision_fn,
    choose_fallback_actor_fn,
    validate_turn_selection_decision_fn,
    assess_turn_selection_decision_semantics_fn,
    reconcile_turn_selection_issues_fn,
    get_character_display_name_fn: Callable[[str], str],
    is_audit_enabled_fn,
    get_audit_logger_fn,
    get_audit_context_fn,
    get_scene_audit_logging_kwargs_fn,
    refresh_audit_summary_report_fn,
    build_recent_dialogue_history_fn,
    prompt_dialogue_history_limit: int,
    director_spotlight_history_limit: int,
):
    enforce_must_remain_presence_fn()

    def actor_label_for_selector(actor_key: str) -> str:
        if not (actor_key or "").strip():
            return actor_key
        label = str(get_character_display_name_fn(actor_key) or "").strip()
        return label if label else actor_key

    def normalize_reason_for_human_logs(reason: str) -> str:
        return substitute_agent_keys_with_display_names(
            str(reason or ""),
            participant_names,
            get_character_display_name_fn,
        )

    if available_actors is None:
        raise ValueError(
            "choose_next_actor requires available_actors: pass the filtered list "
            "from get_available_actors (never None)."
        )

    if not available_actors:
        orch = get_orchestration_state_fn()
        record_selection_attribution_event(
            st_module,
            {
                "round_number": round_number,
                "turn_number": turn_number,
                "available_actors": [],
                "pending_forced_speaker": st_module.session_state.get(
                    "pending_forced_speaker"
                ),
                "forced_speaker_consumed": bool(
                    st_module.session_state.get("forced_speaker_consumed", False)
                ),
                "continuation_override_actor": continuation_override_actor,
                "arch_quality_variant": arch_quality_variant(st_module),
                "hard_route": True,
                "hard_route_source": "no_available_actors",
                "final_next_actor": "",
                "attribution_chain": [],
                "beat_shift_pending": is_pending_beat_shift_active(orch),
            },
        )
        return {
            "next_actor": "",
            "environment_event": "",
            "tension_shift": "",
            "reason": "No available actors remaining in this response cycle.",
        }

    used_this_round = (
        list(actors_used_this_round)
        if isinstance(actors_used_this_round, list)
        else []
    )
    p1_continuation_applied = False
    continuation_override_skipped_c2 = False

    forced_speaker = st_module.session_state.get("pending_forced_speaker")
    if forced_speaker in available_actors and not st_module.session_state.get(
        "forced_speaker_consumed", False
    ):
        st_module.session_state["forced_speaker_consumed"] = True
        orchestration_state_early = get_orchestration_state_fn()
        cm_early = get_continuity_manager_fn()
        pa_early = sync_progression_advisory_for_prompts(
            orchestration_state=orchestration_state_early,
            continuity_manager=cm_early,
        )
        decision = {
            "next_actor": forced_speaker,
            "environment_event": "",
            "tension_shift": "",
            "reason": "Forced by direct address routing.",
        }
        record_selection_attribution_event(
            st_module,
            {
                "round_number": round_number,
                "turn_number": turn_number,
                "available_actors": list(available_actors),
                "pending_forced_speaker": forced_speaker,
                "forced_speaker_consumed": True,
                "continuation_override_actor": continuation_override_actor,
                "arch_quality_variant": arch_quality_variant(st_module),
                "hard_route": True,
                "hard_route_source": "forced_speaker",
                "final_next_actor": forced_speaker,
                "attribution_chain": ["forced_speaker"],
                "beat_shift_pending": is_pending_beat_shift_active(
                    orchestration_state_early
                ),
                "stall_score": pa_early.get("stall_score"),
                "progression_pressure": pa_early.get("progression_pressure"),
                "layer_flags": {
                    "semantic_validation_ran": False,
                    "progression_enforcement_gate": False,
                },
            },
        )
        st_module.session_state["selector_decisions"].append(
            f"Director override to addressed character: {actor_label_for_selector(forced_speaker)}"
        )
        return decision

    if continuation_override_actor in available_actors:
        orchestration_state_early = get_orchestration_state_fn()
        sh_raw = orchestration_state_early.get("spotlight_history", []) or []
        if not isinstance(sh_raw, list):
            sh_raw = []
        spotlight_tail = [
            str(x or "").strip() for x in sh_raw if str(x or "").strip()
        ]
        last_spot = spotlight_tail[-1] if spotlight_tail else ""
        co = str(continuation_override_actor or "").strip()
        if last_spot and co and last_spot == co:
            continuation_override_skipped_c2 = True
        else:
            cm_early = get_continuity_manager_fn()
            pa_early = sync_progression_advisory_for_prompts(
                orchestration_state=orchestration_state_early,
                continuity_manager=cm_early,
            )
            decision = {
                "next_actor": continuation_override_actor,
                "environment_event": "",
                "tension_shift": "",
                "reason": "Forced by continuation override.",
            }
            p1_continuation_applied = True
            record_selection_attribution_event(
                st_module,
                {
                    "round_number": round_number,
                    "turn_number": turn_number,
                    "available_actors": list(available_actors),
                    "pending_forced_speaker": st_module.session_state.get(
                        "pending_forced_speaker"
                    ),
                    "forced_speaker_consumed": bool(
                        st_module.session_state.get("forced_speaker_consumed", False)
                    ),
                    "continuation_override_actor": continuation_override_actor,
                    "arch_quality_variant": arch_quality_variant(st_module),
                    "hard_route": True,
                    "hard_route_source": "continuation_override",
                    "final_next_actor": continuation_override_actor,
                    "attribution_chain": ["continuation_override"],
                    "beat_shift_pending": is_pending_beat_shift_active(
                        orchestration_state_early
                    ),
                    "stall_score": pa_early.get("stall_score"),
                    "progression_pressure": pa_early.get("progression_pressure"),
                    "layer_flags": {
                        "semantic_validation_ran": False,
                        "progression_enforcement_gate": False,
                    },
                },
            )
            st_module.session_state["selector_decisions"].append(
                f"Director override to continuation owner: {actor_label_for_selector(continuation_override_actor)}"
            )
            return decision

    orchestration_state = get_orchestration_state_fn()
    continuity_manager = get_continuity_manager_fn()

    assembly: DirectorPromptAssembly = build_director_prompt_payload(
        st_module=st_module,
        orchestration_state=orchestration_state,
        continuity_manager=continuity_manager,
        participant_names=participant_names,
        trigger_text=trigger_text,
        available_actors=available_actors,
        used_this_round=used_this_round,
        continuation_override_actor=continuation_override_actor,
        build_scene_role_prompt_context_fn=build_scene_role_prompt_context_fn,
        serialize_summary_blocks_for_prompt_fn=serialize_summary_blocks_for_prompt_fn,
        build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata_fn,
        serialize_events_for_prompt_fn=serialize_events_for_prompt_fn,
        serialize_canon_anchors_for_prompt_fn=serialize_canon_anchors_for_prompt_fn,
        build_recent_dialogue_history_fn=build_recent_dialogue_history_fn,
        prompt_dialogue_history_limit=prompt_dialogue_history_limit,
        director_spotlight_history_limit=director_spotlight_history_limit,
    )

    prompt = build_director_selection_prompt_fn(assembly.director_payload)
    chat_history = st_module.session_state.get("chat_history", [])
    recent_dialogue_history = build_recent_dialogue_history_fn(
        chat_history,
        limit=prompt_dialogue_history_limit,
        viewer_character_name=None,
    )

    task = TextMessage(content=prompt, source="system")
    result = await director.on_messages([task], cancellation_token)
    raw_response = result.chat_message.content
    decision, error = parse_director_decision_fn(
        raw_response, participant_names, available_actors
    )

    if error or decision is None:
        fallback_actor = choose_fallback_actor_fn(
            available_actors,
            forced_speaker,
            prefer_continuing_spotlight=assembly.beat_shift_active,
        )
        decision = {
            "next_actor": fallback_actor or "",
            "environment_event": "",
            "tension_shift": "",
            "reason": f"Fallback selection after director parse failure: {error}",
            "source": "fallback",
        }

    return await finalize_director_selection_after_llm(
        assembly=assembly,
        st_module=st_module,
        decision=decision,
        error=error,
        raw_response=raw_response,
        prompt=prompt,
        forced_speaker=forced_speaker,
        continuation_override_actor=continuation_override_actor,
        p1_continuation_applied=p1_continuation_applied,
        continuation_override_skipped_c2=continuation_override_skipped_c2,
        used_this_round=used_this_round,
        participant_names=participant_names,
        available_actors=available_actors,
        trigger_text=trigger_text,
        round_number=round_number,
        turn_number=turn_number,
        recent_dialogue_history=recent_dialogue_history,
        cancellation_token=cancellation_token,
        director_spotlight_history_limit=director_spotlight_history_limit,
        progression_delta_required_fn=progression_delta_required,
        normalize_reason_for_human_logs=normalize_reason_for_human_logs,
        actor_label_for_selector=actor_label_for_selector,
        get_model_client_fn=get_model_client_fn,
        validate_turn_selection_decision_fn=validate_turn_selection_decision_fn,
        assess_turn_selection_decision_semantics_fn=assess_turn_selection_decision_semantics_fn,
        reconcile_turn_selection_issues_fn=reconcile_turn_selection_issues_fn,
        get_character_display_name_fn=get_character_display_name_fn,
        is_audit_enabled_fn=is_audit_enabled_fn,
        get_audit_logger_fn=get_audit_logger_fn,
        get_audit_context_fn=get_audit_context_fn,
        get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_fn,
        refresh_audit_summary_report_fn=refresh_audit_summary_report_fn,
    )

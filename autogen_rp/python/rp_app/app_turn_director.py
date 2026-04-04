import logging
from collections.abc import Callable
from typing import Any

from autogen_agentchat.messages import TextMessage

from semantic_validation import (
    filter_selection_issues_for_human_log,
    substitute_agent_keys_with_display_names,
)

from audit_instrumentation import log_audit_exception
from beat_shift_state import (
    build_director_beat_shift_prompt_prefix,
    is_pending_beat_shift_active,
)
from orchestration_helpers import (
    apply_participation_fairness_to_decision,
    resolve_progression_override_actor,
)
from anti_regression_advisory import sync_anti_regression_advisory_for_prompts
from progression_advisory import (
    build_progression_director_prompt_prefix,
    sync_progression_advisory_for_prompts,
)
from scene_grounding import format_grounding_prompt_prefix
from perception_audibility import redact_structured_move_for_orchestration
from director_low_pressure_guidance import (
    all_available_have_spoken_this_cycle,
    build_director_selection_metrics,
    build_low_pressure_director_prompt_prefix,
    build_low_pressure_turn_selection_payload,
    compute_responder_hint,
    consecutive_trailing_same_speaker,
    low_pressure_turn_guidance_active,
)

logger = logging.getLogger("rp_app.progression_advisory")


def split_actionable_and_stalled_issues(
    *, issues: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actionable_statuses = {"active", "escalating", ""}
    actionable_issues: list[dict[str, Any]] = []
    stalled_background_issues: list[dict[str, Any]] = []

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        status = str(issue.get("status", "") or "").strip().lower()
        if status in actionable_statuses:
            actionable_issues.append(issue)
        else:
            stalled_background_issues.append(issue)

    return actionable_issues, stalled_background_issues


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

    def _actor_label_for_selector(actor_key: str) -> str:
        if not (actor_key or "").strip():
            return actor_key
        label = str(get_character_display_name_fn(actor_key) or "").strip()
        return label if label else actor_key

    def _reason_text_for_human_logs(reason: str) -> str:
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

    forced_speaker = st_module.session_state.get("pending_forced_speaker")
    if forced_speaker in available_actors and not st_module.session_state.get(
        "forced_speaker_consumed", False
    ):
        st_module.session_state["forced_speaker_consumed"] = True
        decision = {
            "next_actor": forced_speaker,
            "environment_event": "",
            "tension_shift": "",
            "reason": "Forced by direct address routing.",
        }
        st_module.session_state["selector_decisions"].append(
            f"Director override to addressed character: {_actor_label_for_selector(forced_speaker)}"
        )
        return decision

    if continuation_override_actor in available_actors:
        decision = {
            "next_actor": continuation_override_actor,
            "environment_event": "",
            "tension_shift": "",
            "reason": "Forced by continuation override.",
        }
        st_module.session_state["selector_decisions"].append(
            f"Director override to continuation owner: {_actor_label_for_selector(continuation_override_actor)}"
        )
        return decision

    orchestration_state = get_orchestration_state_fn()
    beat_shift_active = is_pending_beat_shift_active(orchestration_state)
    state_manager = st_module.session_state.get("character_state_manager")
    chat_history = st_module.session_state.get("chat_history", [])
    continuity_manager = get_continuity_manager_fn()
    continuity_snapshot = (
        continuity_manager.get_snapshot() if continuity_manager is not None else None
    )
    orchestration_continuity_context = (
        continuity_manager.get_orchestration_context(
            active_issue_limit=4,
            recent_event_limit=4,
            summary_limit=3,
        )
        if continuity_manager is not None
        else None
    )
    continuity_scene_state = (
        continuity_snapshot.scene_state.to_dict()
        if continuity_snapshot is not None
        else orchestration_state.get("scene_state", {})
    )
    scene_state_for_prompt = (
        continuity_scene_state
        if continuity_scene_state
        else orchestration_state.get("scene_state", {})
    )
    scene_roles = build_scene_role_prompt_context_fn(
        scene_state_for_prompt, participant_names
    )
    continuity_tension_history = orchestration_state.get("scene_state", {}).get(
        "tension_history", []
    )
    generated_summary_blocks = (
        continuity_manager.summary_blocks[:] if continuity_manager is not None else []
    )
    available_summary_blocks = (
        continuity_manager.retrieve_summary_blocks(limit=0)
        if continuity_manager is not None
        else []
    )
    selected_summary_blocks = (
        orchestration_continuity_context.get("summary_blocks", [])
        if orchestration_continuity_context is not None
        else []
    )
    summary_blocks = (
        serialize_summary_blocks_for_prompt_fn(selected_summary_blocks)
        if orchestration_continuity_context is not None
        else []
    )
    summary_block_audit = build_summary_block_audit_metadata_fn(
        generated_blocks=generated_summary_blocks,
        available_blocks=available_summary_blocks,
        selected_blocks=selected_summary_blocks,
        selection_reason=(
            "ranked deterministic retrieval for orchestration prompt"
            if selected_summary_blocks
            else ""
        ),
        skipped_reason=(
            "Continuity manager unavailable"
            if continuity_manager is None
            else (
                "No summary blocks generated yet"
                if not generated_summary_blocks
                else (
                    "No orchestration summary blocks available after retrieval"
                    if not selected_summary_blocks
                    else ""
                )
            )
        ),
        summary_generation_eligible=(
            continuity_manager is not None
            and continuity_manager.summary_interval > 0
            and continuity_manager.turn_counter >= continuity_manager.summary_interval
        ),
        summary_limit=3,
    )
    director_payload = {
        "current_scene_state": {
            "opening_description": continuity_scene_state.get(
                "opening_description",
                orchestration_state.get("scene_state", {}).get(
                    "opening_description", ""
                ),
            ),
            "recent_environment_events": continuity_scene_state.get(
                "recent_environment_events",
                orchestration_state.get("scene_state", {}).get(
                    "recent_environment_events", []
                ),
            )[-4:],
            "tension_history": continuity_tension_history[-4:],
            "resolved_events": orchestration_state.get("scene_state", {}).get(
                "resolved_events", []
            )[-4:],
            "location": continuity_scene_state.get("location"),
            "scene_phase": continuity_scene_state.get("phase"),
            "current_tension_level": continuity_scene_state.get(
                "current_tension_level"
            ),
            "recent_delta": continuity_scene_state.get("recent_delta", ""),
            "latest_trigger": trigger_text,
            "present_characters": scene_state_for_prompt.get(
                "present_characters", participant_names
            ),
            "offstage_characters": scene_state_for_prompt.get(
                "offstage_characters", []
            ),
        },
        "scene_template": {
            "template_id": str(
                scene_state_for_prompt.get("scene_template_id", "") or ""
            ),
            "premise": str(scene_state_for_prompt.get("scene_premise", "") or ""),
            "location_entry_slots": [
                str(item)
                for item in scene_state_for_prompt.get("location_entry_slots", [])
                if str(item or "").strip()
            ],
        },
        "scene_roles": scene_roles,
        "recent_structured_character_actions": [
            redact_structured_move_for_orchestration(
                dict(item),
                present_characters=scene_state_for_prompt.get(
                    "present_characters", participant_names
                ),
            )
            for item in (orchestration_state.get("recent_structured_moves", []) or [])[
                -4:
            ]
            if isinstance(item, dict)
        ],
        "character_states": (
            state_manager.public_state_snapshot() if state_manager else {}
        ),
        "recent_dialogue_history": build_recent_dialogue_history_fn(
            chat_history,
            limit=prompt_dialogue_history_limit,
            viewer_character_name=None,
        ),
        "spotlight_history": orchestration_state.get("spotlight_history", [])[
            -director_spotlight_history_limit:
        ],
        "active_issues": (
            [
                issue.to_dict()
                for issue in orchestration_continuity_context.get("active_issues", [])
            ]
            if orchestration_continuity_context is not None
            else []
        ),
        "summary_blocks": summary_blocks,
        "recent_public_events": (
            serialize_events_for_prompt_fn(
                orchestration_continuity_context.get("recent_public_events", [])
            )
            if orchestration_continuity_context is not None
            else []
        ),
        "scene_canon_anchors": (
            serialize_canon_anchors_for_prompt_fn(
                orchestration_continuity_context.get("scene_canon_anchors", [])
            )
            if orchestration_continuity_context is not None
            else []
        ),
        "participants": participant_names,
        "available_next_actors": available_actors,
        "actors_already_used_this_round": [
            name for name in participant_names if name not in available_actors
        ],
        "response_cycle_acting_counts": {
            str(name): used_this_round.count(str(name))
            for name in participant_names
            if str(name or "").strip()
        },
    }

    actionable_issues, stalled_background_issues = split_actionable_and_stalled_issues(
        issues=director_payload.get("active_issues", []),
    )
    director_payload["active_issues"] = actionable_issues
    director_payload["stalled_background_issues"] = stalled_background_issues

    progression_advisory_snapshot = sync_progression_advisory_for_prompts(
        orchestration_state=orchestration_state,
        continuity_manager=continuity_manager,
    )

    anti_regression_bundle = sync_anti_regression_advisory_for_prompts(
        orchestration_state=orchestration_state,
        progression_advisory=progression_advisory_snapshot,
        session_state=st_module.session_state,
        participant_names=participant_names,
    )
    anti_prefix = str(anti_regression_bundle.get("prompt_prefix", "") or "")
    anti_blob = anti_regression_bundle.get("advisory_blob") or {}

    if beat_shift_active:
        director_payload["beat_shift_director_hints"] = {
            "active": True,
            "prompt_prefix": build_director_beat_shift_prompt_prefix(),
        }

    if progression_advisory_snapshot.get("progression_pressure") == "high":
        prog_prefix = build_progression_director_prompt_prefix(
            progression_advisory_snapshot
        )
        if prog_prefix:
            director_payload["progression_director_hints"] = {
                "active": True,
                "prompt_prefix": prog_prefix,
            }
            logger.info(
                "[progression_advisory] director prompt injected pressure=high "
                "stall_score=%s",
                progression_advisory_snapshot.get("stall_score"),
            )

    if anti_prefix:
        director_payload["anti_regression_director_hints"] = {
            "active": True,
            "prompt_prefix": anti_prefix,
        }
        logger.info(
            "[anti_regression] director prompt injected ping_pong=%s post_break=%s low_agency=%s",
            anti_blob.get("ping_pong_detected"),
            anti_blob.get("post_break_window_active"),
            anti_blob.get("low_player_agency"),
        )

    anti_regression_director_hints_active = bool(str(anti_prefix or "").strip())
    progression_pressure_val = progression_advisory_snapshot.get("progression_pressure")
    spotlight_slice = orchestration_state.get("spotlight_history", [])[
        -director_spotlight_history_limit:
    ]
    spotlight_recent = [
        str(x or "").strip() for x in (spotlight_slice or []) if str(x or "").strip()
    ]
    raw_moves = orchestration_state.get("recent_structured_moves", []) or []
    last_raw_move = raw_moves[-1] if raw_moves and isinstance(raw_moves[-1], dict) else None
    present_for_audibility = [
        str(x or "").strip()
        for x in scene_state_for_prompt.get("present_characters", participant_names)
        if str(x or "").strip()
    ]

    low_pressure_turn_guidance_active_flag = low_pressure_turn_guidance_active(
        beat_shift_active=beat_shift_active,
        progression_pressure=str(progression_pressure_val or ""),
        available_actors=available_actors,
        continuation_override_actor=continuation_override_actor,
        anti_regression_director_hints_active=anti_regression_director_hints_active,
    )

    spotlight_last_before_pick: str | None = None
    sh_full = orchestration_state.get("spotlight_history", []) or []
    if isinstance(sh_full, list) and sh_full:
        spotlight_last_before_pick = str(sh_full[-1] or "").strip() or None

    responder_hint_for_audit: dict[str, Any] = {"confidence": "none"}
    if low_pressure_turn_guidance_active_flag:
        director_payload["low_pressure_turn_selection"] = (
            build_low_pressure_turn_selection_payload(
                spotlight_recent=spotlight_recent,
                response_cycle_counts=director_payload["response_cycle_acting_counts"],
                actors_used_this_round=used_this_round,
                available_actors=available_actors,
            )
        )
        director_payload["responder_hint"] = compute_responder_hint(
            last_structured_move=last_raw_move,
            available_actors=available_actors,
            present_characters=present_for_audibility,
        )
        responder_hint_for_audit = dict(director_payload["responder_hint"])
        director_payload["low_pressure_turn_director_hints"] = {
            "active": True,
            "prompt_prefix": build_low_pressure_director_prompt_prefix(),
        }

    director_payload["settled_scene_facts_prompt"] = format_grounding_prompt_prefix(
        st_module.session_state.get("scene_grounding")
    )

    prompt = build_director_selection_prompt_fn(director_payload)
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
            prefer_continuing_spotlight=beat_shift_active,
        )
        decision = {
            "next_actor": fallback_actor or "",
            "environment_event": "",
            "tension_shift": "",
            "reason": f"Fallback selection after director parse failure: {error}",
            "source": "fallback",
        }

    director_pick_for_audit = str(decision.get("next_actor", "") or "").strip()
    end_round_for_audit = bool(decision.get("end_round"))
    director_selection_audit_metrics = build_director_selection_metrics(
        low_pressure_regime=low_pressure_turn_guidance_active_flag,
        consecutive_spotlight_same=consecutive_trailing_same_speaker(spotlight_recent),
        all_available_have_spoken=all_available_have_spoken_this_cycle(
            available_actors=available_actors,
            actors_used_this_round=used_this_round,
        ),
        responder_hint=responder_hint_for_audit,
        director_pick=director_pick_for_audit,
        spotlight_last_before_pick=spotlight_last_before_pick,
        end_round=end_round_for_audit,
    )

    pending_forced = st_module.session_state.get("pending_forced_speaker")
    pending_forced_str = (
        pending_forced if isinstance(pending_forced, str) and pending_forced.strip() else None
    )
    offstage_raw = scene_state_for_prompt.get("offstage_characters", [])
    offstage_list = offstage_raw if isinstance(offstage_raw, list) else None

    deterministic_turn_selection_issues = validate_turn_selection_decision_fn(
        decision,
        participant_names,
        available_actors,
        trigger_text,
        orchestration_state.get("spotlight_history", [])[
            -director_spotlight_history_limit:
        ],
        pending_forced_speaker=pending_forced_str,
        forced_speaker_consumed=bool(
            st_module.session_state.get("forced_speaker_consumed", False)
        ),
        continuation_override_actor=continuation_override_actor,
        offstage_characters=offstage_list,
    )
    semantic_turn_selection_assessment = (
        await assess_turn_selection_decision_semantics_fn(
            model_client=get_model_client_fn(),
            trigger_text=trigger_text,
            participant_names=participant_names,
            available_actors=available_actors,
            decision=decision,
            spotlight_history=orchestration_state.get("spotlight_history", [])[
                -director_spotlight_history_limit:
            ],
            scene_state=scene_state_for_prompt,
            recent_dialogue_history=recent_dialogue_history,
            cancellation_token=cancellation_token,
            beat_shift_active=beat_shift_active,
        )
    )
    reconciled_turn_selection_issues = reconcile_turn_selection_issues_fn(
        deterministic_turn_selection_issues,
        semantic_turn_selection_assessment,
    )
    human_turn_selection_issues = filter_selection_issues_for_human_log(
        base_issues=deterministic_turn_selection_issues,
        reconciled_issues=reconciled_turn_selection_issues,
        semantic_assessment=semantic_turn_selection_assessment,
    )
    if human_turn_selection_issues:
        decision["reason"] = (
            f"{decision.get('reason', '')} | Validation: {'; '.join(human_turn_selection_issues)}"
        ).strip(" |")

    if st_module.session_state.get("progression_enforcement_disabled"):
        progression_enforcement_gate = False
    else:
        progression_enforcement_gate = beat_shift_active or (
            progression_advisory_snapshot.get("progression_pressure") == "high"
        )
    progression_override_actor = resolve_progression_override_actor(
        director_selected_actor=str(decision.get("next_actor", "") or ""),
        available_actors=available_actors,
        active_issues=[
            issue
            for issue in (director_payload.get("active_issues", []) or [])
            if isinstance(issue, dict)
        ],
        recent_structured_moves=[
            item
            for item in (orchestration_state.get("recent_structured_moves", []) or [])
            if isinstance(item, dict)
        ],
        spotlight_history=[
            str(x or "").strip()
            for x in (orchestration_state.get("spotlight_history", []) or [])
            if str(x or "").strip()
        ],
        progression_enforcement_gate=progression_enforcement_gate,
    )
    if progression_override_actor and progression_override_actor != decision.get(
        "next_actor"
    ):
        original_actor = str(decision.get("next_actor", "") or "")
        decision["next_actor"] = progression_override_actor
        decision["reason"] = (
            f"{decision.get('reason', '')} | Progression override from {original_actor} to {progression_override_actor}"
        ).strip(" |")

    apply_participation_fairness_to_decision(
        decision,
        participant_names=participant_names,
        available_actors=available_actors,
        actors_used_this_round=used_this_round,
    )

    decision["reason"] = _reason_text_for_human_logs(
        str(decision.get("reason", "") or "")
    )

    if is_audit_enabled_fn():
        try:
            audit_logger = get_audit_logger_fn()
            session_owner, session_num, _, _ = get_audit_context_fn()
            scene_audit_kwargs = get_scene_audit_logging_kwargs_fn(
                continuity_manager.scene_state
                if continuity_manager is not None
                else None
            )

            entry = audit_logger.create_entry(
                session_owner=session_owner,
                session_number=session_num,
                round_number=round_number,
                turn_number=turn_number,
                bot_name="Director",
                bot_type="director",
                input_messages=[{"role": "system", "content": prompt}],
                raw_response=raw_response,
                parsed_output=decision,
                context_snapshot={
                    "participant_names": participant_names,
                    "forced_speaker": forced_speaker,
                    "spotlight_history": orchestration_state.get(
                        "spotlight_history", []
                    )[-6:],
                },
                metadata={
                    "parse_error": error,
                    "is_fallback": bool(error),
                    "beat_shift_active": beat_shift_active,
                    "progression_advisory": {
                        "stall_score": progression_advisory_snapshot.get("stall_score"),
                        "progression_pressure": progression_advisory_snapshot.get(
                            "progression_pressure"
                        ),
                        "recommended_channels": progression_advisory_snapshot.get(
                            "recommended_channels"
                        ),
                        "note": progression_advisory_snapshot.get("note"),
                        "stall_components": progression_advisory_snapshot.get(
                            "stall_components"
                        ),
                    },
                    "anti_regression_advisory": dict(anti_blob),
                    "turn_selection_issues": reconciled_turn_selection_issues,
                    "semantic_turn_selection_assessment": semantic_turn_selection_assessment
                    or {},
                    "summary_blocks": summary_block_audit,
                    "director_selection_metrics": director_selection_audit_metrics,
                },
                **scene_audit_kwargs,
            )
            audit_logger.log_bot_interaction(entry)
            refresh_audit_summary_report_fn()
        except Exception as exc:
            log_audit_exception(
                f"audit: director log_bot_interaction or summary refresh failed "
                f"(round={round_number} turn={turn_number})",
                exc,
            )

    st_module.session_state["selector_decisions"].append(
        f"Director selected {_actor_label_for_selector(str(decision.get('next_actor') or ''))}: "
        f"{decision.get('reason', '')}"
    )
    return decision

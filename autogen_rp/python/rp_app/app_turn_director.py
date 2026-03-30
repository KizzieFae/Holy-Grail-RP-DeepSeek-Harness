import logging
from typing import Any

from autogen_agentchat.messages import TextMessage

from audit_instrumentation import log_audit_exception
from beat_shift_state import (
    build_director_beat_shift_prompt_prefix,
    is_pending_beat_shift_active,
)
from orchestration_helpers import resolve_progression_override_actor
from anti_regression_advisory import sync_anti_regression_advisory_for_prompts
from progression_advisory import (
    build_progression_director_prompt_prefix,
    sync_progression_advisory_for_prompts,
)
from progression_pressure import (
    build_director_progression_pressure_payload,
    build_director_progression_pressure_prefix,
    get_cached_progression_pressure,
)
from scene_grounding import format_grounding_prompt_prefix

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
    available_actors: list[str] | None,
    continuation_override_actor: str | None,
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

    if available_actors is None:
        available_actors = participant_names

    if not available_actors:
        return {
            "next_actor": "",
            "environment_event": "",
            "tension_shift": "",
            "reason": "No available actors remaining in this response cycle.",
        }

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
            f"Director override to addressed character: {forced_speaker}"
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
            f"Director override to continuation owner: {continuation_override_actor}"
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
        "recent_structured_character_actions": orchestration_state.get(
            "recent_structured_moves", []
        )[-4:],
        "character_states": (
            state_manager.public_state_snapshot() if state_manager else {}
        ),
        "recent_dialogue_history": build_recent_dialogue_history_fn(chat_history),
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
    }

    actionable_issues, stalled_background_issues = split_actionable_and_stalled_issues(
        issues=director_payload.get("active_issues", []),
    )
    director_payload["active_issues"] = actionable_issues
    director_payload["stalled_background_issues"] = stalled_background_issues
    progression_pressure_snapshot = get_cached_progression_pressure(orchestration_state)
    if progression_pressure_snapshot:
        director_payload["progression_pressure"] = (
            build_director_progression_pressure_payload(
                orchestration_state=orchestration_state,
                active_issues=actionable_issues,
            )
        )

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

    pressure_prefix = build_director_progression_pressure_prefix(orchestration_state)
    if pressure_prefix:
        director_payload["progression_pressure_director_hints"] = {
            "active": True,
            "prompt_prefix": pressure_prefix,
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

    director_payload["settled_scene_facts_prompt"] = format_grounding_prompt_prefix(
        st_module.session_state.get("scene_grounding")
    )

    prompt = build_director_selection_prompt_fn(director_payload)
    recent_dialogue_history = build_recent_dialogue_history_fn(chat_history)

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
        }

    turn_selection_issues = validate_turn_selection_decision_fn(
        decision,
        participant_names,
        available_actors,
        trigger_text,
        orchestration_state.get("spotlight_history", [])[
            -director_spotlight_history_limit:
        ],
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
    turn_selection_issues = reconcile_turn_selection_issues_fn(
        turn_selection_issues,
        semantic_turn_selection_assessment,
    )
    if turn_selection_issues:
        decision["reason"] = (
            f"{decision.get('reason', '')} | Validation: {'; '.join(turn_selection_issues)}"
        ).strip(" |")

    progression_override_actor = resolve_progression_override_actor(
        director_selected_actor=str(decision.get("next_actor", "") or ""),
        available_actors=available_actors,
        active_issues=[
            issue
            for issue in (director_payload.get("active_issues", []) or [])
            if isinstance(issue, dict)
        ],
        orchestration_state=orchestration_state,
    )
    if progression_override_actor and progression_override_actor != decision.get(
        "next_actor"
    ):
        original_actor = str(decision.get("next_actor", "") or "")
        decision["next_actor"] = progression_override_actor
        decision["reason"] = (
            f"{decision.get('reason', '')} | Progression override from {original_actor} to {progression_override_actor}"
        ).strip(" |")

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
                        "stall_components": progression_advisory_snapshot.get(
                            "stall_components"
                        ),
                    },
                    "progression_pressure": (
                        build_director_progression_pressure_payload(
                            orchestration_state=orchestration_state,
                            active_issues=actionable_issues,
                        )
                        if progression_pressure_snapshot
                        else {}
                    ),
                    "anti_regression_advisory": dict(anti_blob),
                    "turn_selection_issues": turn_selection_issues,
                    "semantic_turn_selection_assessment": semantic_turn_selection_assessment
                    or {},
                    "summary_blocks": summary_block_audit,
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
        f"Director selected {decision['next_actor']}: {decision.get('reason', '')}"
    )
    return decision

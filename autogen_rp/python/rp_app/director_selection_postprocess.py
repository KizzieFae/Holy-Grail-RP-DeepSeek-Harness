"""Post-parse Director selection pipeline for ``choose_next_actor`` (Issue #151)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from arch_quality_variants import (
    arch_quality_c_disable_progression_override,
    arch_quality_variant,
)
from audit_instrumentation import log_audit_exception
from audit_interpretation_metadata import (
    attach_signal_interpretation_v1,
    merge_scene_grounding_audit_family,
)
from director_low_pressure_guidance import (
    all_available_have_spoken_this_cycle,
    build_director_selection_metrics,
    consecutive_trailing_same_speaker,
)
from director_prompt_payload import DirectorPromptAssembly
from orchestration_helpers import (
    assign_progression_band_for_actor,
    apply_participation_fairness_to_decision,
    resolve_progression_override_actor,
)
from selection_attribution import record_selection_attribution_event, semantic_flag_summary
from semantic_validation import (
    apply_gated_addressee_alignment_under_progression_enforcement,
    filter_selection_issues_for_human_log,
)
from turn_selection_preference import (
    build_routing_preference_snapshot,
    build_turn_selection_diagnostics_for_audit,
    format_turn_selection_diagnostic_block,
    sanitize_semantic_turn_selection_assessment,
)


async def finalize_director_selection_after_llm(
    *,
    assembly: DirectorPromptAssembly,
    st_module: Any,
    decision: dict[str, Any],
    error: Any,
    raw_response: str,
    prompt: str,
    forced_speaker: Any,
    continuation_override_actor: str | None,
    p1_continuation_applied: bool,
    continuation_override_skipped_c2: bool,
    used_this_round: list[str],
    participant_names: list[str],
    available_actors: list[str],
    trigger_text: str,
    round_number: int,
    turn_number: int,
    recent_dialogue_history: Any,
    cancellation_token,
    director_spotlight_history_limit: int,
    progression_delta_required_fn: Callable[..., Any],
    normalize_reason_for_human_logs: Callable[[str], str],
    actor_label_for_selector: Callable[[str], str],
    get_model_client_fn: Callable[..., Any],
    validate_turn_selection_decision_fn: Callable[..., Any],
    assess_turn_selection_decision_semantics_fn: Callable[..., Any],
    reconcile_turn_selection_issues_fn: Callable[..., Any],
    get_character_display_name_fn: Callable[[str], str],
    is_audit_enabled_fn: Callable[[], bool],
    get_audit_logger_fn: Callable[[], Any],
    get_audit_context_fn: Callable[..., Any],
    get_scene_audit_logging_kwargs_fn: Callable[..., Any],
    refresh_audit_summary_report_fn: Callable[[], None],
) -> dict[str, Any]:
    director_payload = assembly.director_payload
    continuity_manager = assembly.continuity_manager
    orchestration_state = assembly.orchestration_state
    progression_advisory_snapshot = assembly.progression_advisory_snapshot
    beat_shift_active = assembly.beat_shift_active
    low_pressure_turn_guidance_active_flag = assembly.low_pressure_turn_guidance_active_flag
    responder_hint_for_audit = assembly.responder_hint_for_audit
    anti_prefix = assembly.anti_prefix
    anti_blob = assembly.anti_blob
    summary_block_audit = assembly.summary_block_audit
    director_prefix_eligible = assembly.director_prefix_eligible
    director_prefix_in_prompt = assembly.director_prefix_in_prompt
    spotlight_recent = assembly.spotlight_recent
    spotlight_last_before_pick = assembly.spotlight_last_before_pick
    scene_state_for_prompt = assembly.scene_state_for_prompt

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
    routing_snapshot = build_routing_preference_snapshot(
        responder_obligation=director_payload.get("responder_obligation"),
        action_responsibility=director_payload.get("action_responsibility"),
        available_actors=available_actors,
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
            routing_preference=routing_snapshot,
        )
    )
    effective_semantic_assessment = None
    if isinstance(semantic_turn_selection_assessment, dict):
        if semantic_turn_selection_assessment.get("parse_error"):
            effective_semantic_assessment = semantic_turn_selection_assessment
        else:
            effective_semantic_assessment = sanitize_semantic_turn_selection_assessment(
                semantic_turn_selection_assessment,
                selected_actor=director_pick_for_audit,
                participant_names=participant_names,
                display_name_for_key=get_character_display_name_fn,
            )
    reconciled_turn_selection_issues = reconcile_turn_selection_issues_fn(
        deterministic_turn_selection_issues,
        semantic_turn_selection_assessment,
        selected_actor=director_pick_for_audit,
        participant_names=participant_names,
        display_name_for_key=get_character_display_name_fn,
    )
    human_turn_selection_issues = filter_selection_issues_for_human_log(
        base_issues=deterministic_turn_selection_issues,
        reconciled_issues=reconciled_turn_selection_issues,
        semantic_assessment=effective_semantic_assessment,
    )
    reason_before_semantic_note = str(decision.get("reason", "") or "")
    pref_candidate = routing_snapshot.get("preference_candidate")
    routing_misaligned = bool(
        pref_candidate and str(pref_candidate).strip() != str(director_pick_for_audit).strip()
    )
    reason_amended_for_semantic = False
    actor_after_semantic = str(director_pick_for_audit or "").strip()

    if st_module.session_state.get("progression_enforcement_disabled"):
        progression_enforcement_gate = False
    else:
        progression_enforcement_gate = progression_delta_required_fn(
            orchestration_state=orchestration_state,
            continuity_manager=continuity_manager,
        )

    addressee_alignment_applied = False
    addressee_alignment_previous = ""
    addressee_alignment_next = ""
    applied_addr, prev_addr, _resolved_addr = (
        apply_gated_addressee_alignment_under_progression_enforcement(
            decision=decision,
            progression_enforcement_gate=progression_enforcement_gate,
            effective_semantic_assessment=effective_semantic_assessment,
            available_actors=available_actors,
            participant_names=participant_names,
            display_name_for_key=get_character_display_name_fn,
        )
    )
    if applied_addr:
        addressee_alignment_applied = True
        addressee_alignment_previous = prev_addr
        addressee_alignment_next = str(decision.get("next_actor") or "").strip()
        actor_after_semantic = addressee_alignment_next
        reconciled_turn_selection_issues = reconcile_turn_selection_issues_fn(
            deterministic_turn_selection_issues,
            semantic_turn_selection_assessment,
            selected_actor=addressee_alignment_next,
            participant_names=participant_names,
            display_name_for_key=get_character_display_name_fn,
        )
        human_turn_selection_issues = filter_selection_issues_for_human_log(
            base_issues=deterministic_turn_selection_issues,
            reconciled_issues=reconciled_turn_selection_issues,
            semantic_assessment=effective_semantic_assessment,
        )

    actor_before_progression_override = actor_after_semantic
    progression_override_actor = None
    progression_override_high_candidate_available = False
    progression_override_suppressed_med_band = False
    progression_override_director_band = None
    if not p1_continuation_applied and not arch_quality_c_disable_progression_override(
        st_module
    ):
        progression_override_active_issues = [
            issue
            for issue in (director_payload.get("active_issues", []) or [])
            if isinstance(issue, dict)
        ]
        progression_override_recent_structured_moves = [
            item
            for item in (orchestration_state.get("recent_structured_moves", []) or [])
            if isinstance(item, dict)
        ]
        progression_override_bands: dict[str, str] = {}
        for actor in available_actors:
            progression_override_bands[actor] = assign_progression_band_for_actor(
                actor=actor,
                available_actors=available_actors,
                active_issues=progression_override_active_issues,
                recent_structured_moves=progression_override_recent_structured_moves,
            )
        progression_override_director_band = progression_override_bands.get(
            str(decision.get("next_actor", "") or "")
        )
        progression_override_high_candidate_available = (
            progression_override_director_band == "med"
            and any(
                progression_override_bands.get(actor) == "high"
                for actor in available_actors
            )
        )
        progression_override_actor = resolve_progression_override_actor(
            director_selected_actor=str(decision.get("next_actor", "") or ""),
            available_actors=available_actors,
            active_issues=progression_override_active_issues,
            recent_structured_moves=progression_override_recent_structured_moves,
            spotlight_history=[
                str(x or "").strip()
                for x in (orchestration_state.get("spotlight_history", []) or [])
                if str(x or "").strip()
            ],
            progression_enforcement_gate=progression_enforcement_gate,
        )
    progression_override_applied = False
    if progression_override_actor and progression_override_actor != decision.get(
        "next_actor"
    ):
        progression_override_applied = True
        original_actor = str(decision.get("next_actor", "") or "")
        decision["next_actor"] = progression_override_actor
        decision["reason"] = (
            f"{decision.get('reason', '')} | Progression override from {original_actor} to {progression_override_actor}"
        ).strip(" |")
    progression_override_suppressed_med_band = (
        progression_override_director_band == "med"
        and progression_enforcement_gate
        and progression_override_high_candidate_available
        and not progression_override_applied
    )

    actor_after_override = str(decision.get("next_actor", "") or "").strip()
    actor_before_fairness = actor_after_override
    if not p1_continuation_applied:
        apply_participation_fairness_to_decision(
            decision,
            participant_names=participant_names,
            available_actors=available_actors,
            actors_used_this_round=used_this_round,
        )
    actor_after_fairness = str(decision.get("next_actor", "") or "").strip()
    fairness_rotated = (
        actor_before_fairness != actor_after_fairness
        and not bool(decision.get("end_round"))
    )

    if human_turn_selection_issues or routing_misaligned:
        final_pick = str(decision.get("next_actor", "") or "").strip()
        diag = format_turn_selection_diagnostic_block(
            validated_pick=str(director_pick_for_audit or "").strip(),
            final_pick=final_pick,
            routing_snapshot=routing_snapshot,
            reconciled_issues=human_turn_selection_issues,
        )
        extra: list[str] = []
        if human_turn_selection_issues:
            extra.append(f"Validation: {'; '.join(human_turn_selection_issues)}")
        extra.append(diag)
        decision["reason"] = (
            f"{decision.get('reason', '')} | {' | '.join(extra)}"
        ).strip(" |")
    reason_amended_for_semantic = str(decision.get("reason", "") or "") != (
        reason_before_semantic_note
    )

    turn_selection_diag = build_turn_selection_diagnostics_for_audit(
        actual_pick=director_pick_for_audit,
        final_pick=str(decision.get("next_actor") or "").strip(),
        routing_snapshot=routing_snapshot,
        semantic_effective=effective_semantic_assessment,
        reconciled_issues=reconciled_turn_selection_issues,
    )

    decision["reason"] = normalize_reason_for_human_logs(
        str(decision.get("reason", "") or "")
    )

    director_source = "fallback" if (error or decision.get("source") == "fallback") else "director"
    attribution_chain: list[str] = []
    if director_source == "fallback":
        attribution_chain.append("fallback")
    else:
        attribution_chain.append("director")
    if addressee_alignment_applied:
        attribution_chain.append("addressee_alignment")
    if progression_override_applied:
        attribution_chain.append("progression_override")
    if fairness_rotated:
        attribution_chain.append("participation_fairness")

    selection_attribution_record: dict[str, Any] = {
        "round_number": round_number,
        "turn_number": turn_number,
        "available_actors": list(available_actors),
        "pending_forced_speaker": pending_forced_str,
        "forced_speaker_consumed": bool(
            st_module.session_state.get("forced_speaker_consumed", False)
        ),
        "continuation_override_actor": continuation_override_actor,
        "arch_quality_variant": arch_quality_variant(st_module),
        "hard_route": False,
        "director_raw": {
            "source": director_source,
            "next_actor": director_pick_for_audit,
            "end_round": end_round_for_audit,
            "parse_error": str(error) if error else None,
            "is_fallback": director_source == "fallback",
        },
        "after_semantic_note": {
            "reason_amended": reason_amended_for_semantic,
            "next_actor": actor_after_semantic,
        },
        "after_addressee_alignment": {
            "applied": addressee_alignment_applied,
            "previous_actor": addressee_alignment_previous or None,
            "next_actor": addressee_alignment_next or None,
        },
        "after_progression_override": {
            "applied": progression_override_applied,
            "previous_actor": actor_before_progression_override,
            "next_actor": actor_after_override,
            "source": "progression_override" if progression_override_applied else None,
        },
        "after_fairness": {
            "rotated": fairness_rotated,
            "previous_actor": actor_before_fairness,
            "next_actor": actor_after_fairness,
            "source": "participation_fairness" if fairness_rotated else None,
        },
        "beat_shift_pending": beat_shift_active,
        "stall_score": progression_advisory_snapshot.get("stall_score"),
        "progression_pressure": progression_advisory_snapshot.get("progression_pressure"),
        "director_prefix_eligible": director_prefix_eligible,
        "director_prefix_in_prompt": director_prefix_in_prompt,
        "anti_regression_triggered": bool(str(anti_prefix or "").strip()),
        "low_pressure_regime_active": low_pressure_turn_guidance_active_flag,
        "progression_enforcement_gate": progression_enforcement_gate,
        "semantic_validation_ran": semantic_turn_selection_assessment is not None,
        "semantic_flag_summary": semantic_flag_summary(
            effective_semantic_assessment
            if effective_semantic_assessment is not None
            else semantic_turn_selection_assessment
        ),
        "turn_selection_diagnostics": turn_selection_diag,
        "progression_override_high_candidate_available": progression_override_high_candidate_available,
        "progression_override_suppressed_med_band": progression_override_suppressed_med_band,
        "final_next_actor": str(decision.get("next_actor", "") or "").strip(),
        "attribution_chain": attribution_chain,
        "continuation_override_skipped_c2": continuation_override_skipped_c2,
    }
    record_selection_attribution_event(st_module, selection_attribution_record)

    if is_audit_enabled_fn():
        try:
            audit_logger = get_audit_logger_fn()
            session_owner, session_num, _, _ = get_audit_context_fn()
            scene_audit_kwargs = get_scene_audit_logging_kwargs_fn(
                continuity_manager.scene_state
                if continuity_manager is not None
                else None
            )

            dir_turn_idx = (
                int(getattr(continuity_manager, "turn_counter", 0) or 0)
                if continuity_manager is not None
                else 0
            )
            last_public_event_dict: dict[str, Any] = {}
            if continuity_manager is not None:
                pe_list = getattr(continuity_manager, "public_events", []) or []
                if pe_list:
                    last_ev = pe_list[-1]
                    last_public_event_dict = (
                        last_ev.to_dict() if hasattr(last_ev, "to_dict") else {}
                    )
            sg_fam_dir = merge_scene_grounding_audit_family(
                scene_grounding_state=st_module.session_state.get("scene_grounding"),
                continuity_turn_index=dir_turn_idx,
                continuity_event=last_public_event_dict,
            )
            director_metadata: dict[str, Any] = {
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
                "turn_selection_diagnostics": turn_selection_diag,
                "semantic_turn_selection_assessment": semantic_turn_selection_assessment
                or {},
                "semantic_turn_selection_assessment_effective": effective_semantic_assessment
                or {},
                "summary_blocks": summary_block_audit,
                "director_selection_metrics": director_selection_audit_metrics,
                "selection_attribution": selection_attribution_record,
            }
            if sg_fam_dir:
                director_metadata["scene_grounding"] = sg_fam_dir
            attach_signal_interpretation_v1(director_metadata)

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
                effective_user_trigger=trigger_text,
                metadata=director_metadata,
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
        f"Director selected {actor_label_for_selector(str(decision.get('next_actor') or ''))}: "
        f"{decision.get('reason', '')}"
    )
    return decision

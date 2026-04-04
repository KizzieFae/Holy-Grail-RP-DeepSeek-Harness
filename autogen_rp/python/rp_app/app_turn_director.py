import logging
from collections.abc import Callable
from typing import Any

from autogen_agentchat.messages import TextMessage

from semantic_validation import (
    filter_selection_issues_for_human_log,
    substitute_agent_keys_with_display_names,
)

from arch_quality_variants import (
    arch_quality_a1_suppress_director_soft_prefixes,
    arch_quality_c_disable_progression_override,
    arch_quality_variant,
)
from audit_instrumentation import log_audit_exception
from beat_shift_state import (
    build_director_beat_shift_prompt_prefix,
    is_pending_beat_shift_active,
)
from orchestration_helpers import (
    assign_progression_band_for_actor,
    apply_participation_fairness_to_decision,
    resolve_progression_override_actor,
)
from selection_attribution import record_selection_attribution_event, semantic_flag_summary
from anti_regression_advisory import sync_anti_regression_advisory_for_prompts
from progression_advisory import (
    build_progression_director_prompt_prefix,
    sync_progression_advisory_for_prompts,
)
from scene_grounding import format_grounding_prompt_prefix
from perception_audibility import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    normalize_move_audibility,
    redact_structured_move_for_orchestration,
)
from director_low_pressure_guidance import (
    all_available_have_spoken_this_cycle,
    build_director_selection_metrics,
    build_low_pressure_director_prompt_prefix,
    build_low_pressure_turn_selection_payload,
    compute_responder_hint,
    consecutive_trailing_same_speaker,
    low_pressure_turn_guidance_active,
)
from turn_selection_preference import (
    build_routing_preference_snapshot,
    build_turn_selection_diagnostics_for_audit,
    format_turn_selection_diagnostic_block,
    sanitize_semantic_turn_selection_assessment,
)

logger = logging.getLogger("rp_app.progression_advisory")

_OBLIGATION_CHALLENGE_OR_ACCUSATION_CUES = (
    "answer me",
    "explain yourself",
    "explain yourselves",
    "prove it",
    "prove yourself",
    "admit it",
    "admit it.",
    "defend yourself",
    "justify yourself",
    "look at me",
    "say it again",
    "say that again",
    "liar",
    "lying",
    "coward",
    "then say it",
)

_OBLIGATION_REQUIRED_RESPONSE_CUES = (
    "answer",
    "explain",
    "respond",
    "tell me",
    "say it",
    "justify",
    "defend",
    "admit",
    "deny",
    "prove",
)

_OBLIGATION_IMMEDIATE_EXECUTOR_CUES = (
    "go",
    "get",
    "bring",
    "take",
    "leave",
    "come",
    "call",
    "open",
    "close",
    "move",
    "step",
    "stay",
    "wait",
    "sit",
    "stand",
    "look",
)

_ACTION_RESPONSIBILITY_CONTROL_CUES = (
    "key",
    "keys",
    "access",
    "permission",
    "permit",
    "allow",
    "let me in",
    "let us in",
    "let her in",
    "let him in",
    "let them in",
    "give me",
    "hand me",
    "pass me",
    "unlock",
    "open the door",
    "open up",
)

_ACTION_RESPONSIBILITY_DIRECTIVE_CUES = (
    "wait here",
    "stay here",
    "stay put",
    "sit down",
    "stand down",
    "come here",
    "go now",
    "leave now",
    "step back",
    "move aside",
    "hold still",
    "take the couch",
    "turn around",
)

# Responder obligation activates only when the beat seeks a verbal/social reply, not
# merely directed attention or a concrete physical/task directive (those use action_responsibility).
_REPLY_EXPECTATION_SIGNALS = frozenset(
    {
        "explicit_question",
        "accusation_or_challenge",
        "required_response_to_prior_move",
    }
)


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


def _empty_responder_obligation_hint() -> dict[str, Any]:
    return {
        "active": False,
        "soft_priority": True,
        "confidence": "none",
        "candidates": [],
        "instruction": "No clear immediate responder obligation detected.",
    }


def _append_candidate_signal(
    candidate_signals: dict[str, list[str]], actor: str, signal: str
) -> None:
    actor_key = str(actor or "").strip()
    signal_key = str(signal or "").strip()
    if not actor_key or not signal_key:
        return
    bucket = candidate_signals.setdefault(actor_key, [])
    if signal_key not in bucket:
        bucket.append(signal_key)


def _empty_action_responsibility_hint() -> dict[str, Any]:
    return {
        "active": False,
        "soft_priority": True,
        "confidence": "none",
        "candidates": [],
        "instruction": (
            "No clear bounded action owner detected from the immediately prior move."
        ),
    }


def _extract_local_candidate_targets(
    *, last_structured_move: dict[str, Any], available_actors: list[str]
) -> list[str]:
    available = [str(x or "").strip() for x in available_actors if str(x or "").strip()]
    available_set = set(available)
    audibility = str(last_structured_move.get("audibility", "") or "").strip().lower()
    raw_audience = last_structured_move.get("audience", [])
    audience = raw_audience if isinstance(raw_audience, list) else []
    audience_targets = [
        str(x or "").strip() for x in audience if str(x or "").strip() in available_set
    ]
    if audibility in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE) and audience_targets:
        return audience_targets

    dialogue = str(last_structured_move.get("dialogue", "") or "").strip().lower()
    action = str(last_structured_move.get("action", "") or "").strip().lower()
    combined = " ".join(part for part in [dialogue, action] if part)
    named_targets = [actor for actor in available if actor.lower() in combined]
    return named_targets


def _classify_action_responsibility_mode(text: str) -> str | None:
    normalized = " ".join(str(text or "").strip().lower().split())
    if not normalized:
        return None
    if any(cue in normalized for cue in _ACTION_RESPONSIBILITY_CONTROL_CUES):
        return "grant_or_withhold_controlled_action"
    if any(cue in normalized for cue in _ACTION_RESPONSIBILITY_DIRECTIVE_CUES):
        return "comply_or_refuse_concrete_directive"
    return None


def _compute_action_responsibility_hint(
    *,
    last_structured_move: dict[str, Any] | None,
    available_actors: list[str],
    responder_obligation: dict[str, Any] | None,
) -> dict[str, Any]:
    hint = _empty_action_responsibility_hint()
    if isinstance(responder_obligation, dict) and responder_obligation.get("active"):
        return hint
    if not isinstance(last_structured_move, dict):
        return hint

    available = [str(x or "").strip() for x in available_actors if str(x or "").strip()]
    if not available:
        return hint

    dialogue = str(last_structured_move.get("dialogue", "") or "").strip()
    action = str(last_structured_move.get("action", "") or "").strip()
    combined_text = " ".join(part for part in [dialogue, action] if part)
    mode = _classify_action_responsibility_mode(combined_text)
    if mode is None:
        return hint

    targets = _extract_local_candidate_targets(
        last_structured_move=last_structured_move,
        available_actors=available,
    )
    if not targets:
        return hint

    candidate_signals: dict[str, list[str]] = {}
    if mode == "grant_or_withhold_controlled_action":
        for target in targets:
            _append_candidate_signal(
                candidate_signals, target, "controls_bounded_next_step"
            )
            _append_candidate_signal(candidate_signals, target, "must_grant_or_refuse")
    else:
        for target in targets:
            _append_candidate_signal(
                candidate_signals, target, "concrete_directive_target"
            )
            _append_candidate_signal(candidate_signals, target, "must_comply_or_refuse")

    candidates = [
        {
            "actor": actor,
            "signals": list(candidate_signals[actor]),
        }
        for actor in available
        if candidate_signals.get(actor)
    ]
    if not candidates:
        return hint

    hint["active"] = True
    hint["responsibility_mode"] = mode
    if len(candidates) == 1:
        hint["confidence"] = "high"
        hint["primary_actor"] = candidates[0]["actor"]
        hint["instruction"] = (
            "If the next meaningful beat is a bounded controlled action or concrete "
            "directive outcome rather than a reply beat, prefer the actor who owns "
            "that next step. This is advisory only."
        )
    else:
        hint["confidence"] = "medium"
        hint["instruction"] = (
            "Multiple available actors plausibly own the next bounded action beat. "
            "Treat this as advisory only."
        )
    hint["candidates"] = candidates
    return hint


def _looks_like_immediate_executor_signal(text: str, target: str) -> bool:
    norm_text = " ".join(str(text or "").strip().lower().replace(",", " ").split())
    target_name = str(target or "").strip().lower()
    if not norm_text or not target_name or "?" in norm_text:
        return False
    for cue in _OBLIGATION_IMMEDIATE_EXECUTOR_CUES:
        if norm_text.startswith(f"{cue} "):
            return True
        if norm_text.startswith(f"you {cue} "):
            return True
        if norm_text.startswith(f"{target_name} {cue} "):
            return True
        if f" {target_name} {cue} " in f" {norm_text} ":
            return True
        if f" you {cue} " in f" {norm_text} ":
            return True
    return False


def _compute_responder_obligation_hint(
    *,
    last_structured_move: dict[str, Any] | None,
    available_actors: list[str],
    present_characters: list[str],
) -> dict[str, Any]:
    hint = _empty_responder_obligation_hint()
    if not isinstance(last_structured_move, dict):
        return hint

    speaker = str(last_structured_move.get("speaker", "") or "").strip()
    if not speaker:
        return hint

    available = [str(x or "").strip() for x in available_actors if str(x or "").strip()]
    if not available:
        return hint
    available_set = set(available)

    present = [
        str(x or "").strip() for x in (present_characters or []) if str(x or "").strip()
    ]
    if not present:
        present = list(available)

    normalized_move = normalize_move_audibility(dict(last_structured_move), speaker, present)
    audibility = str(normalized_move.get("audibility", "") or "").strip().lower()
    raw_audience = normalized_move.get("audience", [])
    audience = raw_audience if isinstance(raw_audience, list) else []
    audience_targets = [
        str(x or "").strip() for x in audience if str(x or "").strip() in available_set
    ]

    dialogue = str(last_structured_move.get("dialogue", "") or "").strip()
    action = str(last_structured_move.get("action", "") or "").strip()
    combined_text = " ".join(part for part in [dialogue, action] if part).lower()
    question_like = "?" in dialogue or "?" in action
    challenge_like = any(
        cue in combined_text for cue in _OBLIGATION_CHALLENGE_OR_ACCUSATION_CUES
    )
    required_response_like = question_like or challenge_like or any(
        cue in combined_text for cue in _OBLIGATION_REQUIRED_RESPONSE_CUES
    )

    candidate_signals: dict[str, list[str]] = {}
    if audibility in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE):
        if len(audience_targets) == 1:
            target = audience_targets[0]
            _append_candidate_signal(candidate_signals, target, "direct_address")
            if question_like:
                _append_candidate_signal(candidate_signals, target, "explicit_question")
            if challenge_like:
                _append_candidate_signal(
                    candidate_signals, target, "accusation_or_challenge"
                )
            if required_response_like:
                _append_candidate_signal(
                    candidate_signals, target, "required_response_to_prior_move"
                )
            if _looks_like_immediate_executor_signal(dialogue or action, target):
                _append_candidate_signal(
                    candidate_signals, target, "immediate_consequence_executor"
                )
        elif len(audience_targets) > 1 and required_response_like:
            for target in audience_targets:
                if question_like:
                    _append_candidate_signal(
                        candidate_signals, target, "explicit_question"
                    )
                if challenge_like:
                    _append_candidate_signal(
                        candidate_signals, target, "accusation_or_challenge"
                    )
                _append_candidate_signal(
                    candidate_signals, target, "required_response_to_prior_move"
                )

    candidates = [
        {
            "actor": actor,
            "signals": list(candidate_signals[actor]),
        }
        for actor in available
        if candidate_signals.get(actor)
        and _REPLY_EXPECTATION_SIGNALS.intersection(candidate_signals[actor])
    ]
    if not candidates:
        return hint

    hint["active"] = True
    if len(candidates) == 1:
        hint["confidence"] = "high"
        hint["primary_actor"] = candidates[0]["actor"]
        hint["instruction"] = (
            "Prefer the available actor with the clearest immediate obligation to respond. "
            "This is advisory only."
        )
    else:
        hint["confidence"] = "medium"
        hint["instruction"] = (
            "Multiple available actors have plausible immediate obligation. Treat this "
            "as advisory only and choose the actor who best advances the immediate beat."
        )
    hint["candidates"] = candidates
    return hint


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
            f"Director override to addressed character: {_actor_label_for_selector(forced_speaker)}"
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

    director_payload["responder_obligation"] = _compute_responder_obligation_hint(
        last_structured_move=last_raw_move,
        available_actors=available_actors,
        present_characters=present_for_audibility,
    )
    if director_payload["responder_obligation"].get("active"):
        director_payload["responder_obligation_director_hints"] = {"active": True}

    director_payload["action_responsibility"] = _compute_action_responsibility_hint(
        last_structured_move=last_raw_move,
        available_actors=available_actors,
        responder_obligation=director_payload["responder_obligation"],
    )
    if director_payload["action_responsibility"].get("active"):
        director_payload["action_responsibility_director_hints"] = {"active": True}

    director_prefix_eligible = {
        "progression": "progression_director_hints" in director_payload,
        "beat_shift": "beat_shift_director_hints" in director_payload,
        "anti_regression": "anti_regression_director_hints" in director_payload,
        "low_pressure": "low_pressure_turn_director_hints" in director_payload,
    }
    if arch_quality_a1_suppress_director_soft_prefixes(st_module):
        director_payload.pop("progression_director_hints", None)
        director_payload.pop("anti_regression_director_hints", None)
        director_payload.pop("low_pressure_turn_director_hints", None)
        director_payload.pop("responder_obligation_director_hints", None)
        director_payload.pop("action_responsibility_director_hints", None)

    director_prefix_in_prompt = {
        "progression": "progression_director_hints" in director_payload,
        "beat_shift": "beat_shift_director_hints" in director_payload,
        "anti_regression": "anti_regression_director_hints" in director_payload,
        "low_pressure": "low_pressure_turn_director_hints" in director_payload,
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
        progression_enforcement_gate = beat_shift_active or (
            progression_advisory_snapshot.get("progression_pressure") == "high"
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
        final_pick=str(decision.get("next_actor", "") or "").strip(),
        routing_snapshot=routing_snapshot,
        semantic_effective=effective_semantic_assessment,
        reconciled_issues=reconciled_turn_selection_issues,
    )

    decision["reason"] = _reason_text_for_human_logs(
        str(decision.get("reason", "") or "")
    )

    director_source = "fallback" if (error or decision.get("source") == "fallback") else "director"
    attribution_chain: list[str] = []
    if director_source == "fallback":
        attribution_chain.append("fallback")
    else:
        attribution_chain.append("director")
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
                    "turn_selection_diagnostics": turn_selection_diag,
                    "semantic_turn_selection_assessment": semantic_turn_selection_assessment
                    or {},
                    "semantic_turn_selection_assessment_effective": effective_semantic_assessment
                    or {},
                    "summary_blocks": summary_block_audit,
                    "director_selection_metrics": director_selection_audit_metrics,
                    "selection_attribution": selection_attribution_record,
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

"""Director prompt payload assembly for ``choose_next_actor`` (Issue #151)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from arch_quality_variants import arch_quality_a1_suppress_director_soft_prefixes
from anti_regression_advisory import sync_anti_regression_advisory_for_prompts
from beat_shift_state import build_director_beat_shift_prompt_prefix, is_pending_beat_shift_active
from continuity_prompt_projection_v77 import build_continuity_prompt_projection_v77
from director_low_pressure_guidance import (
    build_low_pressure_director_prompt_prefix,
    build_low_pressure_turn_selection_payload,
    compute_responder_hint,
    low_pressure_turn_guidance_active,
)
from perception_audibility import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    normalize_move_audibility,
    redact_structured_move_for_orchestration,
)
from progression_advisory import (
    build_progression_director_prompt_prefix,
    sync_progression_advisory_for_prompts,
)
from scene_grounding import format_grounding_prompt_prefix

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


@dataclass
class DirectorPromptAssembly:
    """Mutable ``director_payload`` plus contextual state for selection post-processing."""

    director_payload: dict[str, Any]
    summary_block_audit: dict[str, Any]
    scene_state_for_prompt: dict[str, Any]
    continuity_manager: Any
    orchestration_state: dict[str, Any]
    progression_advisory_snapshot: dict[str, Any]
    anti_prefix: str
    anti_blob: dict[str, Any]
    beat_shift_active: bool
    low_pressure_turn_guidance_active_flag: bool
    responder_hint_for_audit: dict[str, Any]
    director_prefix_eligible: dict[str, bool]
    director_prefix_in_prompt: dict[str, bool]
    spotlight_recent: list[str]
    spotlight_last_before_pick: str | None


@dataclass
class _DirectorPayloadWork:
    """Mutable assembly state for :func:`build_director_prompt_payload` (Issue #172)."""

    st_module: Any
    orchestration_state: dict[str, Any]
    continuity_manager: Any
    participant_names: list[str]
    trigger_text: str
    available_actors: list[str]
    used_this_round: list[str]
    continuation_override_actor: str | None
    build_scene_role_prompt_context_fn: Callable[..., Any]
    serialize_summary_blocks_for_prompt_fn: Callable[..., Any]
    build_summary_block_audit_metadata_fn: Callable[..., Any]
    serialize_events_for_prompt_fn: Callable[..., Any]
    serialize_canon_anchors_for_prompt_fn: Callable[..., Any]
    build_recent_dialogue_history_fn: Callable[..., Any]
    prompt_dialogue_history_limit: int
    director_spotlight_history_limit: int
    state_manager: Any = None
    chat_history: list[Any] = field(default_factory=list)
    orchestration_continuity_context: dict[str, Any] | None = None
    scene_state_for_prompt: dict[str, Any] = field(default_factory=dict)
    scene_roles: Any = None
    continuity_tension_history: list[Any] = field(default_factory=list)
    summary_block_audit: dict[str, Any] = field(default_factory=dict)
    summary_blocks: list[Any] = field(default_factory=list)
    director_payload: dict[str, Any] = field(default_factory=dict)
    progression_advisory_snapshot: dict[str, Any] = field(default_factory=dict)
    anti_prefix: str = ""
    anti_blob: dict[str, Any] = field(default_factory=dict)
    beat_shift_active: bool = False
    anti_regression_director_hints_active: bool = False
    progression_pressure_val: Any = None
    spotlight_recent: list[str] = field(default_factory=list)
    spotlight_last_before_pick: str | None = None
    last_raw_move: dict[str, Any] | None = None
    present_for_audibility: list[str] = field(default_factory=list)
    low_pressure_turn_guidance_active_flag: bool = False
    responder_hint_for_audit: dict[str, Any] = field(
        default_factory=lambda: {"confidence": "none"}
    )


def _collect_runtime_inputs(
    *,
    st_module: Any,
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    participant_names: list[str],
    trigger_text: str,
    available_actors: list[str],
    used_this_round: list[str],
    continuation_override_actor: str | None,
    build_scene_role_prompt_context_fn: Callable[..., Any],
    serialize_summary_blocks_for_prompt_fn: Callable[..., Any],
    build_summary_block_audit_metadata_fn: Callable[..., Any],
    serialize_events_for_prompt_fn: Callable[..., Any],
    serialize_canon_anchors_for_prompt_fn: Callable[..., Any],
    build_recent_dialogue_history_fn: Callable[..., Any],
    prompt_dialogue_history_limit: int,
    director_spotlight_history_limit: int,
) -> _DirectorPayloadWork:
    work = _DirectorPayloadWork(
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
    work.state_manager = st_module.session_state.get("character_state_manager")
    work.chat_history = st_module.session_state.get("chat_history", [])
    v77_projection = build_continuity_prompt_projection_v77(
        continuity_manager,
        orchestration_scene_state_fallback=orchestration_state.get("scene_state", {}),
    )
    work.orchestration_continuity_context = (
        continuity_manager.get_orchestration_context(
            active_issue_limit=4,
            recent_event_limit=4,
            summary_limit=3,
        )
        if continuity_manager is not None
        else None
    )
    continuity_scene_state = v77_projection.scene_state_dict
    work.scene_state_for_prompt = (
        continuity_scene_state
        if continuity_scene_state
        else orchestration_state.get("scene_state", {})
    )
    work.scene_roles = work.build_scene_role_prompt_context_fn(
        work.scene_state_for_prompt, participant_names
    )
    work.continuity_tension_history = (
        work.scene_state_for_prompt.get("tension_history", []) or []
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
        work.orchestration_continuity_context.get("summary_blocks", [])
        if work.orchestration_continuity_context is not None
        else []
    )
    work.summary_blocks = (
        work.serialize_summary_blocks_for_prompt_fn(selected_summary_blocks)
        if work.orchestration_continuity_context is not None
        else []
    )
    work.summary_block_audit = work.build_summary_block_audit_metadata_fn(
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
    return work


def _build_base_payload(work: _DirectorPayloadWork) -> None:
    scene_state_for_prompt = work.scene_state_for_prompt
    participant_names = work.participant_names
    trigger_text = work.trigger_text
    orchestration_state = work.orchestration_state
    ctx = work.orchestration_continuity_context

    work.director_payload = {
        "current_scene_state": {
            "opening_description": scene_state_for_prompt.get(
                "opening_description", ""
            ),
            "recent_environment_events": (
                scene_state_for_prompt.get("recent_environment_events", []) or []
            )[-4:],
            "tension_history": work.continuity_tension_history[-4:],
            "resolved_events": (
                scene_state_for_prompt.get("resolved_events", []) or []
            )[-4:],
            "location": scene_state_for_prompt.get("location"),
            "scene_phase": scene_state_for_prompt.get("phase"),
            "current_tension_level": scene_state_for_prompt.get(
                "current_tension_level"
            ),
            "recent_delta": scene_state_for_prompt.get("recent_delta", ""),
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
        "scene_roles": work.scene_roles,
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
            work.state_manager.public_state_snapshot()
            if work.state_manager
            else {}
        ),
        "recent_dialogue_history": work.build_recent_dialogue_history_fn(
            work.chat_history,
            limit=work.prompt_dialogue_history_limit,
            viewer_character_name=None,
        ),
        "spotlight_history": orchestration_state.get("spotlight_history", [])[
            -work.director_spotlight_history_limit :
        ],
        "active_issues": (
            [
                issue.to_dict()
                for issue in ctx.get("active_issues", [])
            ]
            if ctx is not None
            else []
        ),
        "summary_blocks": work.summary_blocks,
        "recent_public_events": (
            work.serialize_events_for_prompt_fn(
                ctx.get("recent_public_events", [])
            )
            if ctx is not None
            else []
        ),
        "scene_canon_anchors": (
            work.serialize_canon_anchors_for_prompt_fn(
                ctx.get("scene_canon_anchors", [])
            )
            if ctx is not None
            else []
        ),
        "participants": participant_names,
        "available_next_actors": work.available_actors,
        "actors_already_used_this_round": [
            name for name in participant_names if name not in work.available_actors
        ],
        "response_cycle_acting_counts": {
            str(name): work.used_this_round.count(str(name))
            for name in participant_names
            if str(name or "").strip()
        },
    }


def _attach_issue_views(work: _DirectorPayloadWork) -> None:
    dp = work.director_payload
    actionable_issues, stalled_background_issues = split_actionable_and_stalled_issues(
        issues=dp.get("active_issues", []),
    )
    dp["active_issues"] = actionable_issues
    dp["stalled_background_issues"] = stalled_background_issues


def _attach_progression_views(work: _DirectorPayloadWork) -> None:
    orchestration_state = work.orchestration_state
    continuity_manager = work.continuity_manager
    participant_names = work.participant_names
    st_module = work.st_module
    dp = work.director_payload

    work.progression_advisory_snapshot = sync_progression_advisory_for_prompts(
        orchestration_state=orchestration_state,
        continuity_manager=continuity_manager,
    )

    anti_regression_bundle = sync_anti_regression_advisory_for_prompts(
        orchestration_state=orchestration_state,
        progression_advisory=work.progression_advisory_snapshot,
        session_state=st_module.session_state,
        participant_names=participant_names,
    )
    work.anti_prefix = str(anti_regression_bundle.get("prompt_prefix", "") or "")
    anti_blob_raw = anti_regression_bundle.get("advisory_blob") or {}
    work.anti_blob = anti_blob_raw if isinstance(anti_blob_raw, dict) else {}

    work.beat_shift_active = is_pending_beat_shift_active(orchestration_state)

    if work.beat_shift_active:
        dp["beat_shift_director_hints"] = {
            "active": True,
            "prompt_prefix": build_director_beat_shift_prompt_prefix(),
        }

    if work.progression_advisory_snapshot.get("progression_pressure") == "high":
        prog_prefix = build_progression_director_prompt_prefix(
            work.progression_advisory_snapshot
        )
        if prog_prefix:
            dp["progression_director_hints"] = {
                "active": True,
                "prompt_prefix": prog_prefix,
            }
            logger.info(
                "[progression_advisory] director prompt injected pressure=high "
                "stall_score=%s",
                work.progression_advisory_snapshot.get("stall_score"),
            )

    if work.anti_prefix:
        dp["anti_regression_director_hints"] = {
            "active": True,
            "prompt_prefix": work.anti_prefix,
        }
        logger.info(
            "[anti_regression] director prompt injected ping_pong=%s post_break=%s low_agency=%s",
            work.anti_blob.get("ping_pong_detected"),
            work.anti_blob.get("post_break_window_active"),
            work.anti_blob.get("low_player_agency"),
        )

    work.anti_regression_director_hints_active = bool(
        str(work.anti_prefix or "").strip()
    )
    work.progression_pressure_val = work.progression_advisory_snapshot.get(
        "progression_pressure"
    )


def _attach_turn_obligation_views(work: _DirectorPayloadWork) -> None:
    orchestration_state = work.orchestration_state
    dp = work.director_payload
    participant_names = work.participant_names
    scene_state_for_prompt = work.scene_state_for_prompt

    spotlight_slice = orchestration_state.get("spotlight_history", [])[
        -work.director_spotlight_history_limit :
    ]
    work.spotlight_recent = [
        str(x or "").strip()
        for x in (spotlight_slice or [])
        if str(x or "").strip()
    ]
    raw_moves = orchestration_state.get("recent_structured_moves", []) or []
    work.last_raw_move = (
        raw_moves[-1] if raw_moves and isinstance(raw_moves[-1], dict) else None
    )
    work.present_for_audibility = [
        str(x or "").strip()
        for x in scene_state_for_prompt.get("present_characters", participant_names)
        if str(x or "").strip()
    ]

    work.low_pressure_turn_guidance_active_flag = low_pressure_turn_guidance_active(
        beat_shift_active=work.beat_shift_active,
        progression_pressure=str(work.progression_pressure_val or ""),
        available_actors=work.available_actors,
        continuation_override_actor=work.continuation_override_actor,
        anti_regression_director_hints_active=work.anti_regression_director_hints_active,
    )

    sh_full = orchestration_state.get("spotlight_history", []) or []
    if isinstance(sh_full, list) and sh_full:
        work.spotlight_last_before_pick = str(sh_full[-1] or "").strip() or None
    else:
        work.spotlight_last_before_pick = None

    work.responder_hint_for_audit = {"confidence": "none"}
    if work.low_pressure_turn_guidance_active_flag:
        dp["low_pressure_turn_selection"] = build_low_pressure_turn_selection_payload(
            spotlight_recent=work.spotlight_recent,
            response_cycle_counts=dp["response_cycle_acting_counts"],
            actors_used_this_round=work.used_this_round,
            available_actors=work.available_actors,
        )
        dp["responder_hint"] = compute_responder_hint(
            last_structured_move=work.last_raw_move,
            available_actors=work.available_actors,
            present_characters=work.present_for_audibility,
        )
        work.responder_hint_for_audit = dict(dp["responder_hint"])
        dp["low_pressure_turn_director_hints"] = {
            "active": True,
            "prompt_prefix": build_low_pressure_director_prompt_prefix(),
        }

    dp["responder_obligation"] = _compute_responder_obligation_hint(
        last_structured_move=work.last_raw_move,
        available_actors=work.available_actors,
        present_characters=work.present_for_audibility,
    )
    dp["action_responsibility"] = _compute_action_responsibility_hint(
        last_structured_move=work.last_raw_move,
        available_actors=work.available_actors,
        responder_obligation=dp["responder_obligation"],
    )


def _attach_prompt_hints(work: _DirectorPayloadWork) -> None:
    dp = work.director_payload
    if dp["responder_obligation"].get("active"):
        dp["responder_obligation_director_hints"] = {"active": True}
    if dp["action_responsibility"].get("active"):
        dp["action_responsibility_director_hints"] = {"active": True}


def _apply_final_suppressions(work: _DirectorPayloadWork) -> None:
    dp = work.director_payload
    if arch_quality_a1_suppress_director_soft_prefixes(work.st_module):
        dp.pop("progression_director_hints", None)
        dp.pop("anti_regression_director_hints", None)
        dp.pop("low_pressure_turn_director_hints", None)
        dp.pop("responder_obligation_director_hints", None)
        dp.pop("action_responsibility_director_hints", None)


def _finalize_payload(work: _DirectorPayloadWork) -> DirectorPromptAssembly:
    dp = work.director_payload
    director_prefix_eligible = {
        "progression": "progression_director_hints" in dp,
        "beat_shift": "beat_shift_director_hints" in dp,
        "anti_regression": "anti_regression_director_hints" in dp,
        "low_pressure": "low_pressure_turn_director_hints" in dp,
    }
    director_prefix_in_prompt = {
        "progression": "progression_director_hints" in dp,
        "beat_shift": "beat_shift_director_hints" in dp,
        "anti_regression": "anti_regression_director_hints" in dp,
        "low_pressure": "low_pressure_turn_director_hints" in dp,
    }
    dp["settled_scene_facts_prompt"] = format_grounding_prompt_prefix(
        work.st_module.session_state.get("scene_grounding")
    )
    return DirectorPromptAssembly(
        director_payload=dp,
        summary_block_audit=work.summary_block_audit,
        scene_state_for_prompt=work.scene_state_for_prompt,
        continuity_manager=work.continuity_manager,
        orchestration_state=work.orchestration_state,
        progression_advisory_snapshot=work.progression_advisory_snapshot,
        anti_prefix=work.anti_prefix,
        anti_blob=work.anti_blob,
        beat_shift_active=work.beat_shift_active,
        low_pressure_turn_guidance_active_flag=work.low_pressure_turn_guidance_active_flag,
        responder_hint_for_audit=work.responder_hint_for_audit,
        director_prefix_eligible=director_prefix_eligible,
        director_prefix_in_prompt=director_prefix_in_prompt,
        spotlight_recent=work.spotlight_recent,
        spotlight_last_before_pick=work.spotlight_last_before_pick,
    )


def build_director_prompt_payload(
    *,
    st_module: Any,
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    participant_names: list[str],
    trigger_text: str,
    available_actors: list[str],
    used_this_round: list[str],
    continuation_override_actor: str | None,
    build_scene_role_prompt_context_fn: Callable[..., Any],
    serialize_summary_blocks_for_prompt_fn: Callable[..., Any],
    build_summary_block_audit_metadata_fn: Callable[..., Any],
    serialize_events_for_prompt_fn: Callable[..., Any],
    serialize_canon_anchors_for_prompt_fn: Callable[..., Any],
    build_recent_dialogue_history_fn: Callable[..., Any],
    prompt_dialogue_history_limit: int,
    director_spotlight_history_limit: int,
) -> DirectorPromptAssembly:
    work = _collect_runtime_inputs(
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
    _build_base_payload(work)
    _attach_issue_views(work)
    _attach_progression_views(work)
    _attach_turn_obligation_views(work)
    _attach_prompt_hints(work)
    _apply_final_suppressions(work)
    return _finalize_payload(work)

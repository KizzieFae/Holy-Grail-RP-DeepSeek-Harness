"""Bind ``run_character_turns`` kwargs for headless simulation (audit_simulation harness)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import app_memory_helpers as memory_helpers
import app_state_helpers as state_helpers
import app_turn_helpers as turn_helpers
from character_loader import CharacterLoader, make_agent_identifier
from continuity_manager import ContinuityManager
from orchestration_helpers import (
    append_turn_to_orchestration_state,
    build_recent_scene_context as build_recent_scene_context_impl,
    choose_fallback_actor as choose_fallback_actor_impl,
    ensure_orchestration_state,
    sync_orchestration_state_from_continuity as sync_orchestration_state_from_continuity_impl,
)
from perception_audibility import build_recent_dialogue_history_for_viewer
from prompt_builders import (
    build_director_selection_prompt,
    build_narrator_render_prompt,
    build_scene_role_prompt_context,
)
from prompt_topology_issue240 import build_character_turn_prompt_for_runtime as build_character_turn_prompt_text
from response_validation import (
    build_attempted_post_details,
    get_available_actors,
    get_must_remain_characters,
    parse_character_move,
    validate_turn_selection_decision,
)
from semantic_validation import (
    assess_narrator_render_semantics,
    assess_presence_violation_semantics,
    assess_proposal_beat_contradiction,
    assess_turn_selection_decision_semantics,
    reconcile_turn_selection_issues,
    should_override_presence_rejection,
)
from summary_audit_helpers import (
    build_summary_block_audit_metadata,
    get_character_scene_audit_context,
    get_scene_audit_logging_kwargs,
    serialize_canon_anchors_for_prompt,
    serialize_events_for_prompt,
    serialize_summary_blocks_for_prompt,
)
from audit_logger import get_audit_logger
from character_state import CharacterState
from cross_session_memory_policy import compact_report_for_audit

PROMPT_DIALOGUE_HISTORY_LIMIT = 6
PROMPT_STRUCTURED_MOVE_LIMIT = 4
DIRECTOR_SPOTLIGHT_HISTORY_LIMIT = 6
ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT = 12
ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT = 8
ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT = 8
ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT = 8
ORCHESTRATION_TENSION_HISTORY_LIMIT = 8


def _issue29_resolve_synthetic_available_actors(
    participant_names: list[str],
    *,
    last_successful_actor: str | None,
    actors_used_this_round_tail: str | None,
) -> list[str]:
    """Single-actor pool when real availability is empty (Issue #29 long-run harness, headless only)."""
    names = [str(n or "").strip() for n in participant_names if str(n or "").strip()]
    if not names:
        return []
    ls = str(last_successful_actor or "").strip()
    if ls and ls in names:
        return [ls]
    tu = str(actors_used_this_round_tail or "").strip()
    if tu and tu in names:
        return [tu]
    return [names[0]]


def _wrap_get_available_actors_for_issue29_long_run(
    inner: Callable[..., list[str]],
    *,
    st_module: Any,
) -> Callable[..., list[str]]:
    """When ``issue29_long_run_harness`` is on and the inner pool is empty, inject one actor."""

    def wrapped(
        participant_names: list[str],
        used_actors: list[str] | None,
        eligible_participants: list[str] | None,
        offstage_characters: list[str] | None,
    ) -> list[str]:
        out = inner(
            participant_names,
            used_actors,
            eligible_participants,
            offstage_characters,
        )
        sess = getattr(st_module, "session_state", {}) or {}
        if not sess.get("issue29_long_run_harness") or out:
            return out
        return _issue29_resolve_synthetic_available_actors(
            participant_names,
            last_successful_actor=sess.get("issue29_last_successful_actor"),
            actors_used_this_round_tail=sess.get("issue29_actors_used_this_round_tail"),
        )

    return wrapped


def resolve_bot_reply_limit_deep_simulation(
    active_bot_count: int, configured_limit: int | None
) -> int:
    """Headless scenario runs: honor ``configured_limit`` without capping at bot count.

    Streamlit uses ``min(limit, bot_count)`` so each bot speaks at most once per user round.
    Validation scenarios often need the same cast to trade lines many times in one simulated
    user message; this helper allows that while keeping the production path unchanged.
    """
    if active_bot_count <= 0:
        return 0
    if configured_limit is None or configured_limit < 1:
        return active_bot_count
    return int(configured_limit)


def get_available_actors_allow_repeat_in_round(
    participant_names: list[str],
    used_actors: list[str] | None,
    eligible_participants: list[str] | None,
    offstage_characters: list[str] | None,
) -> list[str]:
    """Same as ``get_available_actors`` but ignore ``used_actors`` (repeat speakers allowed)."""
    return get_available_actors(
        participant_names,
        None,
        eligible_participants,
        offstage_characters,
    )


def build_headless_turn_runner_kwargs(*, st_module: Any) -> dict[str, Any]:
    """Return kwargs for ``run_character_turns_impl`` bound to ``st_module``."""
    import headless_scene_simulation as facade_mod

    parse_director_decision_fn = facade_mod.parse_director_decision
    validate_bot_response_fn = facade_mod.validate_bot_response

    sess = getattr(st_module, "session_state", {}) or {}
    deep = bool(sess.get("headless_deep_simulation_turns"))
    resolve_limit_fn = (
        resolve_bot_reply_limit_deep_simulation
        if deep
        else memory_helpers.resolve_bot_reply_limit
    )
    base_available_actors_fn = (
        get_available_actors_allow_repeat_in_round
        if deep
        else get_available_actors
    )
    available_actors_fn: Callable[..., list[str]] = base_available_actors_fn
    if bool(sess.get("issue29_long_run_harness")):
        available_actors_fn = _wrap_get_available_actors_for_issue29_long_run(
            base_available_actors_fn,
            st_module=st_module,
        )

    def get_scene_audit_logging_kwargs_for_headless(scene_state: Any | None) -> dict[str, Any]:
        base = get_scene_audit_logging_kwargs(scene_state)
        report = st_module.session_state.get("cross_session_injection_report")
        if isinstance(report, dict):
            base = dict(base)
            base["cross_session_injection_report"] = compact_report_for_audit(report)
        return base

    def is_audit_on() -> bool:
        return bool(st_module.session_state.get("audit_enabled"))

    def get_orchestration_state_fn() -> dict[str, Any]:
        return state_helpers.get_orchestration_state(
            st_module=st_module,
            ensure_orchestration_state_fn=ensure_orchestration_state,
        )

    def get_model_client_fn() -> Any:
        return st_module.session_state.get("model_client")

    def get_continuity_manager_fn() -> ContinuityManager | None:
        return state_helpers.get_continuity_manager(
            st_module=st_module,
            continuity_manager_cls=ContinuityManager,
        )

    def enforce_must_remain_presence_fn() -> None:
        state_helpers.enforce_must_remain_presence(
            st_module=st_module,
            get_continuity_manager_fn=get_continuity_manager_fn,
            get_must_remain_characters_fn=get_must_remain_characters,
            get_orchestration_state_fn=get_orchestration_state_fn,
        )

    def sync_orchestration_state_from_continuity_fn() -> None:
        state_helpers.sync_orchestration_state_from_continuity(
            st_module=st_module,
            get_continuity_manager_fn=get_continuity_manager_fn,
            get_orchestration_state_fn=get_orchestration_state_fn,
            sync_orchestration_state_from_continuity_impl_fn=sync_orchestration_state_from_continuity_impl,
            enforce_must_remain_presence_fn=enforce_must_remain_presence_fn,
        )

    def get_character_display_name_fn(identifier: str) -> str:
        return state_helpers.get_character_display_name(
            st_module=st_module,
            identifier=identifier,
            character_state_cls=CharacterState,
            character_loader_cls=CharacterLoader,
            resolve_character_file_fn=lambda loader, ident: state_helpers.resolve_character_file(
                loader=loader,
                identifier=ident,
                make_agent_identifier_fn=make_agent_identifier,
            ),
        )

    def build_recent_dialogue_history_fn(
        chat_history: list[dict[str, Any]],
        limit: int = PROMPT_DIALOGUE_HISTORY_LIMIT,
        viewer_character_name: str | None = None,
    ) -> list[dict[str, str]]:
        names = [
            str(a.name)
            for a in st_module.session_state.get("characters", [])
            if getattr(a, "name", None)
        ]
        return build_recent_dialogue_history_for_viewer(
            chat_history=chat_history,
            viewer_character_name=viewer_character_name,
            character_names=names,
            get_character_display_name_fn=get_character_display_name_fn,
            limit=limit,
        )

    def build_character_turn_prompt_fn(
        char_name: str,
        user_name: str,
        trigger_text: str,
        director_decision: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        return turn_helpers.build_character_turn_prompt(
            st_module=st_module,
            char_name=char_name,
            user_name=user_name,
            trigger_text=trigger_text,
            director_decision=director_decision,
            enforce_must_remain_presence_fn=enforce_must_remain_presence_fn,
            get_orchestration_state_fn=get_orchestration_state_fn,
            get_continuity_manager_fn=get_continuity_manager_fn,
            build_recent_dialogue_history_fn=build_recent_dialogue_history_fn,
            serialize_events_for_prompt_fn=serialize_events_for_prompt,
            serialize_canon_anchors_for_prompt_fn=serialize_canon_anchors_for_prompt,
            serialize_summary_blocks_for_prompt_fn=serialize_summary_blocks_for_prompt,
            build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata,
            build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
            build_character_turn_prompt_text_fn=build_character_turn_prompt_text,
            prompt_structured_move_limit=PROMPT_STRUCTURED_MOVE_LIMIT,
            prompt_dialogue_history_limit=PROMPT_DIALOGUE_HISTORY_LIMIT,
            get_character_display_name_fn=get_character_display_name_fn,
        )

    def choose_fallback_actor_fn(
        available_actors: list[str],
        forced_speaker: str | None,
        *,
        prefer_continuing_spotlight: bool = False,
    ) -> str | None:
        return turn_helpers.choose_fallback_actor(
            available_actors=available_actors,
            forced_speaker=forced_speaker,
            spotlight_history=get_orchestration_state_fn().get("spotlight_history", []),
            choose_fallback_actor_impl_fn=choose_fallback_actor_impl,
            prefer_continuing_spotlight=prefer_continuing_spotlight,
        )

    async def choose_next_actor_fn(**kwargs: Any) -> dict[str, Any]:
        return await turn_helpers.choose_next_actor(
            st_module=st_module,
            get_model_client_fn=get_model_client_fn,
            enforce_must_remain_presence_fn=enforce_must_remain_presence_fn,
            get_orchestration_state_fn=get_orchestration_state_fn,
            get_continuity_manager_fn=get_continuity_manager_fn,
            build_scene_role_prompt_context_fn=build_scene_role_prompt_context,
            serialize_summary_blocks_for_prompt_fn=serialize_summary_blocks_for_prompt,
            build_summary_block_audit_metadata_fn=build_summary_block_audit_metadata,
            serialize_events_for_prompt_fn=serialize_events_for_prompt,
            serialize_canon_anchors_for_prompt_fn=serialize_canon_anchors_for_prompt,
            build_director_selection_prompt_fn=build_director_selection_prompt,
            parse_director_decision_fn=parse_director_decision_fn,
            choose_fallback_actor_fn=choose_fallback_actor_fn,
            validate_turn_selection_decision_fn=validate_turn_selection_decision,
            assess_turn_selection_decision_semantics_fn=assess_turn_selection_decision_semantics,
            reconcile_turn_selection_issues_fn=reconcile_turn_selection_issues,
            get_character_display_name_fn=get_character_display_name_fn,
            is_audit_enabled_fn=is_audit_on,
            get_audit_logger_fn=get_audit_logger,
            get_audit_context_fn=lambda: state_helpers.get_audit_context(
                st_module=st_module,
                is_audit_enabled_fn=is_audit_on,
                get_audit_logger_fn=get_audit_logger,
            ),
            get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_for_headless,
            refresh_audit_summary_report_fn=lambda: state_helpers.refresh_audit_summary_report(
                st_module=st_module,
                is_audit_enabled_fn=is_audit_on,
                get_audit_logger_fn=get_audit_logger,
                get_audit_context_fn=lambda: state_helpers.get_audit_context(
                    st_module=st_module,
                    is_audit_enabled_fn=is_audit_on,
                    get_audit_logger_fn=get_audit_logger,
                ),
                get_continuity_manager_fn=get_continuity_manager_fn,
            ),
            build_recent_dialogue_history_fn=build_recent_dialogue_history_fn,
            prompt_dialogue_history_limit=PROMPT_DIALOGUE_HISTORY_LIMIT,
            director_spotlight_history_limit=DIRECTOR_SPOTLIGHT_HISTORY_LIMIT,
            **kwargs,
        )

    def log_turn_failure_fn(**kwargs: Any) -> None:
        turn_helpers.log_turn_failure(
            st_module=st_module,
            is_audit_enabled_fn=is_audit_on,
            get_audit_logger_fn=get_audit_logger,
            get_audit_context_fn=lambda: state_helpers.get_audit_context(
                st_module=st_module,
                is_audit_enabled_fn=is_audit_on,
                get_audit_logger_fn=get_audit_logger,
            ),
            build_attempted_post_details_fn=build_attempted_post_details,
            get_continuity_manager_fn=get_continuity_manager_fn,
            get_scene_audit_logging_kwargs_fn=get_scene_audit_logging_kwargs_for_headless,
            get_character_scene_audit_context_fn=get_character_scene_audit_context,
            **kwargs,
        )

    def record_character_memories_fn(
        acting_character: str,
        move: dict[str, Any],
        director_decision: dict[str, Any],
        *,
        st_module: Any,
        char_names: list[str],
        display_name_for_key=None,
    ) -> None:
        memory_helpers.record_character_memories(
            st_module=st_module,
            acting_character=acting_character,
            move=move,
            director_decision=director_decision,
            build_memory_fact_summary_fn=memory_helpers.build_memory_fact_summary,
            character_names=char_names,
            display_name_for_key=display_name_for_key or get_character_display_name_fn,
        )

    async def reset_agents_fn(agents: list[Any], cancellation_token: Any) -> None:
        await state_helpers.reset_agents(agents, cancellation_token)

    async def render_character_move_fn(
        narrator: Any,
        char_name: str,
        move: dict[str, Any],
        scene_context: str,
        director_decision: dict[str, Any],
        cancellation_token: Any,
        *,
        beat_shift_narrator_suffix: str = "",
    ) -> tuple[str, str, str, bool]:
        return await turn_helpers.render_character_move(
            narrator=narrator,
            char_name=char_name,
            move=move,
            scene_context=scene_context,
            director_decision=director_decision,
            cancellation_token=cancellation_token,
            build_narrator_render_prompt_fn=build_narrator_render_prompt,
            fallback_render_move_fn=turn_helpers.fallback_render_move,
            beat_shift_narrator_suffix=beat_shift_narrator_suffix,
        )

    return {
        "get_orchestration_state_fn": get_orchestration_state_fn,
        "start_audit_round_fn": lambda: state_helpers.start_audit_round(st_module=st_module),
        "resolve_bot_reply_limit_fn": resolve_limit_fn,
        "get_current_bot_reply_limit_fn": lambda n: state_helpers.get_current_bot_reply_limit(
            st_module=st_module,
            active_bot_count=n,
            get_bot_reply_limit_widget_key_fn=lambda: state_helpers.get_bot_reply_limit_widget_key(
                st_module=st_module
            ),
            resolve_bot_reply_limit_fn=resolve_limit_fn,
        ),
        "get_available_actors_fn": available_actors_fn,
        "set_audit_turn_fn": lambda tn: state_helpers.set_audit_turn(
            st_module=st_module, turn_number=tn
        ),
        "choose_next_actor_fn": choose_next_actor_fn,
        "log_turn_failure_fn": log_turn_failure_fn,
        "build_character_turn_prompt_fn": build_character_turn_prompt_fn,
        "parse_character_move_fn": parse_character_move,
        "is_audit_enabled_fn": is_audit_on,
        "is_llm_audit_enabled_fn": lambda: state_helpers.is_llm_audit_enabled(
            st_module=st_module
        ),
        "get_audit_logger_fn": get_audit_logger,
        "get_audit_context_fn": lambda: state_helpers.get_audit_context(
            st_module=st_module,
            is_audit_enabled_fn=is_audit_on,
            get_audit_logger_fn=get_audit_logger,
        ),
        "get_scene_audit_logging_kwargs_fn": get_scene_audit_logging_kwargs_for_headless,
        "get_character_scene_audit_context_fn": get_character_scene_audit_context,
        "get_continuity_manager_fn": get_continuity_manager_fn,
        "get_model_client_fn": get_model_client_fn,
        "validate_bot_response_fn": validate_bot_response_fn,
        "assess_presence_violation_semantics_fn": assess_presence_violation_semantics,
        "should_override_presence_rejection_fn": should_override_presence_rejection,
        "assess_proposal_beat_contradiction_fn": assess_proposal_beat_contradiction,
        "build_recent_scene_context_fn": lambda ch, orch, limit=6: turn_helpers.build_recent_scene_context(
            chat_history=ch,
            orchestration_state=orch,
            get_continuity_manager_fn=get_continuity_manager_fn,
            build_recent_dialogue_history_fn=build_recent_dialogue_history_fn,
            build_recent_scene_context_impl_fn=build_recent_scene_context_impl,
            limit=limit,
        ),
        "render_character_move_fn": render_character_move_fn,
        "fallback_render_move_fn": turn_helpers.fallback_render_move,
        "assess_narrator_render_semantics_fn": assess_narrator_render_semantics,
        "record_character_memories_fn": record_character_memories_fn,
        "sync_orchestration_state_from_continuity_fn": sync_orchestration_state_from_continuity_fn,
        "refresh_audit_summary_report_fn": lambda: state_helpers.refresh_audit_summary_report(
            st_module=st_module,
            is_audit_enabled_fn=is_audit_on,
            get_audit_logger_fn=get_audit_logger,
            get_audit_context_fn=lambda: state_helpers.get_audit_context(
                st_module=st_module,
                is_audit_enabled_fn=is_audit_on,
                get_audit_logger_fn=get_audit_logger,
            ),
            get_continuity_manager_fn=get_continuity_manager_fn,
        ),
        "reset_agents_fn": reset_agents_fn,
        "get_character_display_name_fn": get_character_display_name_fn,
        "append_turn_to_orchestration_state_fn": append_turn_to_orchestration_state,
        "spotlight_history_limit": ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT,
        "structured_move_history_limit": ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT,
        "director_decision_history_limit": ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT,
        "environment_history_limit": ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT,
        "tension_history_limit": ORCHESTRATION_TENSION_HISTORY_LIMIT,
        "ignore_director_end_round": bool(
            (getattr(st_module, "session_state", {}) or {}).get(
                "headless_ignore_director_end_round"
            )
        ),
    }

"""Wire ``turn_runner.run_character_turns`` without Streamlit (same LLM stack as the app).

Director selection, character generation, narrator render, validation, progression gate,
and continuity updates follow the production path. Use for checklist-style review instead
of only hand-running Streamlit scenes.
"""

from __future__ import annotations

import json
import os
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import app_memory_helpers as memory_helpers
import app_state_helpers as state_helpers
import app_turn_helpers as turn_helpers
from character_loader import CharacterLoader, make_agent_identifier
from character_state_manager import CharacterStateManager
from continuity_manager import ContinuityManager
from continuity_state import IssueState, IssueStatus, ScenePhase
from model_client import create_deepseek_client, create_director_agent, create_narrator_agent
from orchestration_helpers import (
    append_turn_to_orchestration_state,
    build_recent_scene_context as build_recent_scene_context_impl,
    choose_fallback_actor as choose_fallback_actor_impl,
    ensure_orchestration_state,
    sync_orchestration_state_from_continuity as sync_orchestration_state_from_continuity_impl,
)
from perception_audibility import build_recent_dialogue_history_for_viewer
from prompt_builders import (
    build_character_turn_prompt as build_character_turn_prompt_text,
    build_director_selection_prompt,
    build_narrator_render_prompt,
    build_scene_role_prompt_context,
)
from response_validation import (
    build_attempted_post_details,
    get_available_actors,
    get_must_remain_characters,
    parse_character_move,
    parse_director_decision,
    validate_bot_response,
    validate_turn_selection_decision,
)
from scene_grounding import empty_grounding_dict
from semantic_validation import (
    assess_narrator_render_semantics,
    assess_presence_violation_semantics,
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
from progression_run_metrics import (
    build_structured_eval_payload,
    summarize_sim_progression_metrics,
)
from retrieval_audit_helpers import (
    build_retrieval_session_audit,
    merge_retrieval_session_into_audit_summary,
    verify_retrieval_strict_or_raise,
)
from turn_runner import run_character_turns as run_character_turns_impl

PROMPT_DIALOGUE_HISTORY_LIMIT = 6
PROMPT_STRUCTURED_MOVE_LIMIT = 4
DIRECTOR_SPOTLIGHT_HISTORY_LIMIT = 6
ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT = 12
ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT = 8
ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT = 8
ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT = 8
ORCHESTRATION_TENSION_HISTORY_LIMIT = 8


def _rebuild_headless_agents_and_character_states(*, st_module: Any, model_client: Any) -> None:
    """Load agents once and register ``character_states`` + ``character_state_manager``.

    ``rebuild_character_agents`` alone omits the state manager; without it, memory-layer
    commits no-op and simulation memory assertions cannot observe episodic writes.
    """
    loader = CharacterLoader()
    identifiers = list(st_module.session_state.get("selected_chars") or [])
    agents: list[Any] = []
    resolved_files: list[str] = []
    char_states: dict[str, Any] = {}
    for ident in identifiers:
        char_file = state_helpers.resolve_character_file(
            loader=loader,
            identifier=ident,
            make_agent_identifier_fn=make_agent_identifier,
        )
        if char_file is None:
            continue
        try:
            agent, cstate = loader.load_and_create_agent(char_file, model_client)
        except FileNotFoundError:
            continue
        agents.append(agent)
        resolved_files.append(char_file)
        char_states[agent.name] = cstate
    if not agents:
        return
    st_module.session_state["characters"] = agents
    st_module.session_state["selected_chars"] = resolved_files
    st_module.session_state["character_states"] = char_states
    mgr = CharacterStateManager()
    for name, cstate in char_states.items():
        mgr.register_character(name, cstate)
    st_module.session_state["character_state_manager"] = mgr


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


def _parse_scene_phase(value: str) -> ScenePhase:
    v = str(value or "").strip().lower()
    for p in ScenePhase:
        if p.value == v:
            return p
    raise ValueError(f"Unknown scene phase: {value!r}; use one of {[e.value for e in ScenePhase]}")


class HeadlessStreamlit:
    """Minimal stand-in for ``streamlit`` module (session_state + spinner)."""

    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}

    def spinner(self, _message: str):
        return nullcontext()


def build_headless_turn_runner_kwargs(*, st_module: Any) -> dict[str, Any]:
    """Return kwargs for ``run_character_turns_impl`` bound to ``st_module``."""
    sess = getattr(st_module, "session_state", {}) or {}
    deep = bool(sess.get("headless_deep_simulation_turns"))
    resolve_limit_fn = (
        resolve_bot_reply_limit_deep_simulation
        if deep
        else memory_helpers.resolve_bot_reply_limit
    )
    available_actors_fn = (
        get_available_actors_allow_repeat_in_round
        if deep
        else get_available_actors
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
            parse_director_decision_fn=parse_director_decision,
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
    ) -> None:
        memory_helpers.record_character_memories(
            st_module=st_module,
            acting_character=acting_character,
            move=move,
            director_decision=director_decision,
            build_memory_fact_summary_fn=memory_helpers.build_memory_fact_summary,
            character_names=char_names,
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
        "validate_bot_response_fn": validate_bot_response,
        "assess_presence_violation_semantics_fn": assess_presence_violation_semantics,
        "should_override_presence_rejection_fn": should_override_presence_rejection,
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
        ),
        "reset_agents_fn": reset_agents_fn,
        "get_character_display_name_fn": get_character_display_name_fn,
        "append_turn_to_orchestration_state_fn": append_turn_to_orchestration_state,
        "spotlight_history_limit": ORCHESTRATION_SPOTLIGHT_HISTORY_LIMIT,
        "structured_move_history_limit": ORCHESTRATION_STRUCTURED_MOVE_HISTORY_LIMIT,
        "director_decision_history_limit": ORCHESTRATION_DIRECTOR_DECISION_HISTORY_LIMIT,
        "environment_history_limit": ORCHESTRATION_ENVIRONMENT_HISTORY_LIMIT,
        "tension_history_limit": ORCHESTRATION_TENSION_HISTORY_LIMIT,
    }


@dataclass
class HeadlessSimulationResult:
    chat_history: list[dict[str, Any]]
    recent_structured_moves: list[dict[str, Any]]
    selector_decisions: list[str]
    continuity_turn_counter: int
    last_turn_consequences: list[Any]
    scenario_id: str | None = None
    scenario_title: str | None = None
    scenario_intent: str | None = None
    audit_session_number: int | None = None
    audit_summary_report_path: str | None = None
    progression_metrics_summary: dict[str, Any] | None = None
    structured_eval: dict[str, Any] | None = None


async def run_headless_llm_scene(
    *,
    st_module: Any,
    max_turns: int,
    trigger_text: str,
    user_name: str,
    verdict: str | None = None,
    failure_classification: str | None = None,
) -> HeadlessSimulationResult:
    """Run ``run_character_turns_impl``; session must already hold model client and agents."""
    char_agents: list[Any] = list(st_module.session_state.get("characters") or [])
    if not char_agents:
        raise ValueError("st_module.session_state['characters'] must list loaded agents")
    if st_module.session_state.get("model_client") is None:
        raise ValueError("st_module.session_state['model_client'] is required")

    client = st_module.session_state["model_client"]
    narrator = create_narrator_agent(client)
    director = create_director_agent(client)

    kwargs = build_headless_turn_runner_kwargs(st_module=st_module)
    await run_character_turns_impl(
        st_module=st_module,
        char_agents=char_agents,
        narrator=narrator,
        director=director,
        trigger_text=trigger_text,
        user_name=user_name,
        max_turns=max_turns,
        **kwargs,
    )

    cm = state_helpers.get_continuity_manager(
        st_module=st_module, continuity_manager_cls=ContinuityManager
    )
    scene_tpl_id = None
    if cm is not None and cm.scene_state is not None:
        scene_tpl_id = (
            str(getattr(cm.scene_state, "scene_template_id", None) or "").strip() or None
        )
    session_retrieval = build_retrieval_session_audit(
        saw_nonempty_bundle=bool(
            st_module.session_state.get("sim_retrieval_saw_nonempty_bundle")
        ),
    )
    verify_retrieval_strict_or_raise(session_retrieval, scene_template_id=scene_tpl_id)
    rep_path_pre = st_module.session_state.get("audit_summary_report_path")
    merge_retrieval_session_into_audit_summary(
        str(rep_path_pre) if rep_path_pre else None,
        session_retrieval,
    )
    ti = int(getattr(cm, "turn_counter", 0) or 0) if cm else 0
    meta = (
        (getattr(cm, "turn_metadata_by_index", {}) or {}).get(ti, {})
        if cm
        else {}
    )
    last_cons = meta.get("consequences", []) if isinstance(meta, dict) else []

    orch = ensure_orchestration_state(st_module.session_state.get("team_state"))
    st_module.session_state["team_state"] = orch
    moves = orch.get("recent_structured_moves", [])

    rep_path = st_module.session_state.get("audit_summary_report_path")
    raw_metrics = st_module.session_state.get("sim_progression_metrics")
    metrics_list = raw_metrics if isinstance(raw_metrics, list) else []
    enf_on = not bool(st_module.session_state.get("progression_enforcement_disabled"))
    metrics_summary = summarize_sim_progression_metrics(
        metrics_list,
        progression_enforcement_enabled=enf_on,
        arch_quality_variant=str(
            st_module.session_state.get("arch_quality_variant") or "baseline"
        ),
    )
    structured = build_structured_eval_payload(
        scenario_id=st_module.session_state.get("simulation_scenario_id"),
        verdict=verdict,
        failure_classification=failure_classification,
        metrics=metrics_summary,
        audit_session_number=st_module.session_state.get("audit_session_number"),
        audit_summary_report_path=str(rep_path) if rep_path else None,
        expected_pressure_profile=st_module.session_state.get(
            "simulation_expected_pressure_profile"
        ),
        retrieval_session=session_retrieval,
    )
    return HeadlessSimulationResult(
        chat_history=list(st_module.session_state.get("chat_history") or []),
        recent_structured_moves=list(moves) if isinstance(moves, list) else [],
        selector_decisions=list(st_module.session_state.get("selector_decisions") or []),
        continuity_turn_counter=ti,
        last_turn_consequences=list(last_cons) if isinstance(last_cons, list) else [],
        scenario_id=st_module.session_state.get("simulation_scenario_id"),
        scenario_title=st_module.session_state.get("simulation_scenario_title"),
        scenario_intent=st_module.session_state.get("simulation_scenario_intent"),
        audit_session_number=st_module.session_state.get("audit_session_number"),
        audit_summary_report_path=str(rep_path) if rep_path else None,
        progression_metrics_summary=metrics_summary,
        structured_eval=structured,
    )


def prepare_headless_session(
    *,
    character_card_ids: list[str],
    opening_description: str,
    location: str,
    seed_escalating_issue: bool = True,
    beat_shift_active: bool = False,
    progression_enforcement_disabled: bool = False,
    arch_quality_variant: str = "baseline",
    audit_enabled: bool = False,
    llm_audit_enabled: bool = False,
    audit_session_owner: str = "headless_sim",
    scenario_id: str | None = None,
    scenario_title: str | None = None,
    scenario_intent: str | None = None,
    initial_tension: str | None = None,
    initial_phase: str | None = None,
    seed_issue: dict[str, Any] | None = None,
    expected_pressure_profile: str | None = None,
    deep_simulation_turns: bool = False,
    enable_episodic_memory: bool = False,
    scene_template_id: str | None = None,
) -> Any:
    """Build ``HeadlessStreamlit`` session: continuity, orchestration sync, DeepSeek client, agents.

    When ``enable_episodic_memory`` is True, sets process env ``RP_EPISODIC_MEMORY=1`` so character
    prompts merge continuity-backed episodic lines into the retrieved bundle (same as shell export).
    Issue seed participants use **agent keys** (card ``agent_name`` or ``make_agent_identifier``)
    so ``select_episodic_items_for_character`` visibility matches ``next_actor`` from the turn runner.

    When ``scene_template_id`` is set, writes it to ``ContinuityManager.scene_state`` (same field
    Streamlit sets via scene setup) so template-linked authored retrieval can run unchanged.
    """
    if enable_episodic_memory:
        os.environ["RP_EPISODIC_MEMORY"] = "1"
    st = HeadlessStreamlit()
    state_helpers.init_session_state(st_module=st)
    st.session_state["scene_grounding"] = empty_grounding_dict()
    st.session_state["headless_deep_simulation_turns"] = bool(deep_simulation_turns)

    st.session_state["simulation_scenario_id"] = scenario_id
    st.session_state["simulation_scenario_title"] = scenario_title
    st.session_state["simulation_scenario_intent"] = scenario_intent
    st.session_state["simulation_expected_pressure_profile"] = expected_pressure_profile
    st.session_state["sim_progression_metrics"] = []
    st.session_state["sim_retrieval_saw_nonempty_bundle"] = False
    st.session_state["progression_enforcement_disabled"] = bool(
        progression_enforcement_disabled
    )
    aq = str(arch_quality_variant or "baseline").strip().lower()
    st.session_state["arch_quality_variant"] = (
        aq if aq in ("baseline", "a1", "b", "c") else "baseline"
    )

    owner = str(audit_session_owner or "headless_sim").strip() or "headless_sim"
    st.session_state["scene_owner"] = owner
    if audit_enabled:
        st.session_state["audit_enabled"] = True
        logger = get_audit_logger()
        st.session_state["audit_session_number"] = logger.get_next_session_number()
        st.session_state["audit_session_owner"] = owner
        st.session_state["audit_round_number"] = 0
        st.session_state["audit_turn_number"] = 0
        st.session_state["audit_summary_report_path"] = None
        st.session_state["llm_audit_enabled"] = bool(llm_audit_enabled)
    else:
        st.session_state["audit_enabled"] = False
        st.session_state["audit_session_number"] = None
        st.session_state["audit_session_owner"] = None
        st.session_state["llm_audit_enabled"] = False

    loader = CharacterLoader()
    resolved_files: list[str] = []
    display_names: list[str] = []
    agent_keys: list[str] = []
    for cid in character_card_ids:
        cf = state_helpers.resolve_character_file(
            loader=loader,
            identifier=cid,
            make_agent_identifier_fn=make_agent_identifier,
        )
        if cf is None:
            raise ValueError(f"Unknown character card id: {cid!r}")
        card = loader.load_character_card(cf)
        resolved_files.append(cf)
        name = str(card.get("name", "") or "").strip() or cf
        display_names.append(name)
        ak = str(card.get("agent_name", "") or "").strip() or make_agent_identifier(name)
        agent_keys.append(ak)
    st.session_state["selected_chars"] = resolved_files

    def _sync() -> None:
        state_helpers.sync_orchestration_state_from_continuity(
            st_module=st,
            get_continuity_manager_fn=lambda: state_helpers.get_continuity_manager(
                st_module=st, continuity_manager_cls=ContinuityManager
            ),
            get_orchestration_state_fn=lambda: state_helpers.get_orchestration_state(
                st_module=st, ensure_orchestration_state_fn=ensure_orchestration_state
            ),
            sync_orchestration_state_from_continuity_impl_fn=sync_orchestration_state_from_continuity_impl,
            enforce_must_remain_presence_fn=lambda: state_helpers.enforce_must_remain_presence(
                st_module=st,
                get_continuity_manager_fn=lambda: state_helpers.get_continuity_manager(
                    st_module=st, continuity_manager_cls=ContinuityManager
                ),
                get_must_remain_characters_fn=get_must_remain_characters,
                get_orchestration_state_fn=lambda: state_helpers.get_orchestration_state(
                    st_module=st, ensure_orchestration_state_fn=ensure_orchestration_state
                ),
            ),
        )

    state_helpers.restore_or_initialize_continuity_manager(
        st_module=st,
        continuity_state=None,
        character_names=display_names,
        opening_description=opening_description,
        scene_setup=None,
        continuity_manager_cls=ContinuityManager,
        build_initial_scene_issues_fn=state_helpers.build_initial_scene_issues,
        apply_scene_setup_to_scene_state_fn=state_helpers.apply_scene_setup_to_scene_state,
        sync_orchestration_state_from_continuity_fn=_sync,
    )

    cm = state_helpers.get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    if cm is not None and cm.scene_state is not None:
        cm.scene_state.location = location
        _tpl = str(scene_template_id or "").strip()
        cm.scene_state.scene_template_id = _tpl or None
        if initial_tension is not None:
            cm.scene_state.current_tension_level = str(initial_tension)
        else:
            cm.scene_state.current_tension_level = "high" if seed_escalating_issue else "low"
        if initial_phase is not None:
            cm.scene_state.phase = _parse_scene_phase(str(initial_phase))
        else:
            cm.scene_state.phase = ScenePhase.RISING if seed_escalating_issue else ScenePhase.OPENING
        if seed_escalating_issue:
            now = datetime.now(timezone.utc)
            card_to_agent = dict(zip(character_card_ids, agent_keys))
            if seed_issue and isinstance(seed_issue, dict):
                iid = str(seed_issue.get("issue_id") or "sim_standoff").strip() or "sim_standoff"
                desc = str(
                    seed_issue.get("description")
                    or "Competing demands at a pressure point; the scene must move."
                )
                p_cards = seed_issue.get("participant_card_ids")
                if isinstance(p_cards, list) and p_cards:
                    participants = []
                    for c in p_cards:
                        key = str(c).strip()
                        if key not in card_to_agent:
                            raise ValueError(
                                f"seed_issue participant_card_ids contains {key!r} "
                                f"not in character_card_ids"
                            )
                        participants.append(card_to_agent[key])
                    if not participants:
                        participants = list(agent_keys)
                else:
                    participants = list(agent_keys)
            else:
                iid = "sim_standoff"
                desc = "Competing demands at a pressure point; the scene must move."
                participants = list(agent_keys)
            issue = IssueState(
                issue_id=iid,
                description=desc,
                participants=participants,
                status=IssueStatus.ESCALATING,
                created_at=now,
                last_turn_index=None,
                status_reason="headless simulation seed",
            )
            cm.issues[issue.issue_id] = issue
        _sync()

    if beat_shift_active:
        orch = state_helpers.get_orchestration_state(
            st_module=st, ensure_orchestration_state_fn=ensure_orchestration_state
        )
        pbs = orch.get("pending_beat_shift")
        if isinstance(pbs, dict):
            pbs["active"] = True
            pbs["reason"] = "short_user_message"
            pbs["source_turn_id"] = "headless_sim_user_round_1"

    client = create_deepseek_client()
    st.session_state["model_client"] = client
    _rebuild_headless_agents_and_character_states(st_module=st, model_client=client)
    return st


def format_simulation_audit_markdown(result: HeadlessSimulationResult) -> str:
    """Human-readable audit block for checklist review."""
    lines = [
        "## LLM scene simulation audit",
        "",
    ]
    if result.scenario_id:
        lines.append(f"* **Scenario:** `{result.scenario_id}`")
    if result.scenario_title:
        lines.append(f"* **Title:** {result.scenario_title}")
    if result.scenario_intent:
        lines.append(f"* **Intent:** {result.scenario_intent}")
    if result.audit_session_number is not None:
        lines.append(f"* **Audit session:** {result.audit_session_number:03d}")
    if result.audit_summary_report_path:
        lines.append(f"* **Audit summary report:** `{result.audit_summary_report_path}`")
    if result.progression_metrics_summary:
        m = result.progression_metrics_summary
        lines.append(
            f"* **First qualifying delta (continuity turn index):** "
            f"{m.get('first_qualifying_progression_delta_turn_index')!r}"
        )
        lines.append(f"* **Progression retries:** {m.get('progression_retries_triggered', 0)}")
        lines.append(
            f"* **Failed progression attempts:** {m.get('failed_progression_attempts', 0)}"
        )
        lines.append(
            f"* **Qualifying / non-qualifying accepted turns:** "
            f"{m.get('qualifying_turns', 0)} / {m.get('non_qualifying_turns', 0)}"
        )
        lines.append(
            f"* **Progression enforcement:** "
            f"{'on' if m.get('progression_enforcement_enabled') else 'off (baseline)'}"
        )
    if result.structured_eval:
        se = result.structured_eval
        if se.get("verdict") is not None:
            lines.append(f"* **Verdict (manual):** {se.get('verdict')!r}")
        if se.get("failure_classification") is not None:
            lines.append(
                f"* **Failure classification (manual):** {se.get('failure_classification')!r}"
            )
    lines.extend(
        [
            f"* **Continuity turns processed:** {result.continuity_turn_counter}",
            f"* **Last turn classifier consequences:** {result.last_turn_consequences!r}",
            "",
            "### Selector / pipeline notes",
        ]
    )
    for s in result.selector_decisions:
        lines.append(f"- {s}")
    lines.extend(["", "### Structured moves (orchestration)", ""])
    for i, m in enumerate(result.recent_structured_moves, 1):
        if not isinstance(m, dict):
            lines.append(f"{i}. {m!r}")
            continue
        sp = m.get("speaker", "")
        lines.append(f"{i}. **{sp}** action={m.get('action', '')!r} dialogue={m.get('dialogue', '')!r}")
        lines.append(f"   - consequences: {m.get('consequences', [])!r}")
    lines.extend(["", "### Chat history (rendered + user lines)", ""])
    for entry in result.chat_history[-24:]:
        role = entry.get("role", "")
        name = entry.get("name", "")
        content = str(entry.get("content", ""))[:500]
        lines.append(f"- [{role}] {name}: {content!r}")
    if result.structured_eval:
        lines.extend(
            [
                "",
                "### Structured run result (JSON)",
                "",
                "```json",
                json.dumps(result.structured_eval, indent=2, ensure_ascii=False),
                "```",
            ]
        )
    return "\n".join(lines)

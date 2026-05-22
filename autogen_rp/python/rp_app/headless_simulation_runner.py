"""Run headless LLM scene loop and assemble structured simulation results."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import app_state_helpers as state_helpers
from continuity_manager import ContinuityManager
from model_client import create_director_agent, create_narrator_agent
from orchestration_helpers import ensure_orchestration_state
from progression_run_metrics import (
    build_structured_eval_payload,
    summarize_sim_progression_metrics,
)
from retrieval_audit_helpers import (
    apply_retrieval_session_to_audit_summary,
    verify_retrieval_strict_or_raise,
)
from turn_runner import run_character_turns as run_character_turns_impl


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
    get_effective_user_trigger: Callable[[int], str] | None = None,
    resolve_character_turn_trigger: Callable[[int, str], tuple[str, dict[str, Any]]]
    | None = None,
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

    import headless_scene_simulation as facade

    kwargs = facade.build_headless_turn_runner_kwargs(st_module=st_module)
    await run_character_turns_impl(
        st_module=st_module,
        char_agents=char_agents,
        narrator=narrator,
        director=director,
        trigger_text=trigger_text,
        user_name=user_name,
        max_turns=max_turns,
        get_effective_user_trigger=get_effective_user_trigger,
        resolve_character_turn_trigger=resolve_character_turn_trigger,
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
    rep_path_pre = st_module.session_state.get("audit_summary_report_path")
    session_retrieval = apply_retrieval_session_to_audit_summary(
        str(rep_path_pre) if rep_path_pre else None,
        saw_nonempty_bundle=bool(
            st_module.session_state.get("sim_retrieval_saw_nonempty_bundle")
        ),
    )
    verify_retrieval_strict_or_raise(session_retrieval, scene_template_id=scene_tpl_id)
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
        sim_progression_metrics_events=(
            list(metrics_list) if isinstance(metrics_list, list) else []
        ),
        issue29_long_run_harness=bool(
            st_module.session_state.get("issue29_long_run_harness")
        ),
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

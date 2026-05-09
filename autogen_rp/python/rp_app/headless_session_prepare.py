"""Build headless Streamlit-shaped session_state (parity with Streamlit scene-start spine)."""

from __future__ import annotations

import os
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any

import app_memory_cross_session
from character_loader import CharacterLoader, make_agent_identifier
from character_state_manager import CharacterStateManager
from continuity_manager import ContinuityManager
from continuity_setup_seam_v77 import (
    ensure_interim_anchor_role_fallback_for_finalize,
    finalize_continuity_setup_seam,
)
from continuity_state import IssueState, IssueStatus, ScenePhase
from orchestration_helpers import (
    ensure_orchestration_state,
    sync_orchestration_state_from_continuity as sync_orchestration_state_from_continuity_impl,
)
from response_validation import get_must_remain_characters
from scene_grounding import empty_grounding_dict
from scene_lifecycle_start import (
    seed_scene_role_character_priorities,
    seed_scene_role_relationship_context,
)
from bootstrap_composition import (
    BootstrapCompositionError,
    compose_headless_bootstrap,
    interpretation_to_jsonable,
    interpretation_to_seed_scene_setup,
)
from scene_opener import OpenerManager
from scene_start_bootstrap import (
    append_scene_opening_chat_message,
    headless_prepare_scene_setup_bundle,
    mirror_opening_into_scene_state,
)
from scene_template import (
    SceneTemplateManager,
    normalize_role_assignments,
    validate_role_assignments,
)
from summary_audit_helpers import get_scene_audit_logging_kwargs
from audit_instrumentation import log_audit_exception
from audit_logger import get_audit_logger
from session_manager import SessionManager


class HeadlessStreamlit:
    """Minimal stand-in for ``streamlit`` module (session_state + spinner)."""

    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}

    def spinner(self, _message: str):
        return nullcontext()


def _parse_scene_phase(value: str) -> ScenePhase:
    v = str(value or "").strip().lower()
    for p in ScenePhase:
        if p.value == v:
            return p
    raise ValueError(f"Unknown scene phase: {value!r}; use one of {[e.value for e in ScenePhase]}")


def _rebuild_headless_agents_and_character_states(
    *,
    st_module: Any,
    model_client: Any,
    state_helpers: Any,
) -> None:
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


def prepare_headless_session(
    *,
    character_card_ids: list[str],
    opening_description: str,
    location: str,
    user_name: str = "Traveler",
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
    scene_template_role_assignments: dict[str, str] | None = None,
    ignore_director_end_round: bool = False,
    issue29_long_run_harness: bool = False,
    scenario_raw: dict[str, Any] | None = None,
    cli_trigger_for_composition: str | None = None,
) -> Any:
    """Build ``HeadlessStreamlit`` session using the same continuity init/apply path as the app.

    Template: resolve ``scene_setup`` before ``restore_or_initialize_continuity_manager``;
    ``scene_template_role_assignments`` is required when ``scene_template_id`` is set (Issue #80).
    Opening is applied on first init; continuity narrative fields are mirrored before finalize;
    role / cross-session / canon seeding runs in the pre-finalize block; then interim anchor
    fallback, finalize, ``simulation_opening_final``, and a Scene Opening row in ``chat_history``.

    ``simulation_opening_final`` supports CLI/scenario round-1 trigger resolution (``startup_trigger_mode``).
    """
    import headless_scene_simulation as facade

    state_helpers = facade.state_helpers
    create_deepseek_client = facade.create_deepseek_client

    if enable_episodic_memory:
        os.environ["RP_EPISODIC_MEMORY"] = "1"
    st = HeadlessStreamlit()
    state_helpers.init_session_state(st_module=st)
    st.session_state["scene_grounding"] = empty_grounding_dict()
    st.session_state["headless_deep_simulation_turns"] = bool(deep_simulation_turns)
    long_h = bool(issue29_long_run_harness)
    st.session_state["issue29_long_run_harness"] = long_h
    if long_h:
        st.session_state["headless_ignore_director_end_round"] = True
        st.session_state["issue29_last_successful_actor"] = None
        st.session_state["issue29_actors_used_this_round_tail"] = None
    else:
        st.session_state["headless_ignore_director_end_round"] = bool(
            ignore_director_end_round
        )

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

    def _apply_scene_setup_to_scene_state(
        scene_state: Any,
        scene_setup: dict[str, Any] | None,
        *,
        continuity_manager: Any | None = None,
    ) -> None:
        state_helpers.apply_scene_setup_to_scene_state(
            scene_state=scene_state,
            scene_setup=scene_setup,
            get_must_remain_characters_fn=get_must_remain_characters,
            continuity_manager=continuity_manager,
        )

    client = create_deepseek_client()
    st.session_state["model_client"] = client
    _rebuild_headless_agents_and_character_states(
        st_module=st, model_client=client, state_helpers=state_helpers
    )
    char_states: dict[str, Any] = dict(st.session_state.get("character_states") or {})

    def _resolve_template() -> tuple[Any, str]:
        return state_helpers.resolve_scene_template_setup(
            st_module=st,
            selected_chars=resolved_files,
            character_names_by_file=dict(zip(resolved_files, agent_keys)),
            scene_template_manager_cls=SceneTemplateManager,
            normalize_role_assignments_fn=normalize_role_assignments,
            validate_role_assignments_fn=validate_role_assignments,
        )

    scene_setup, setup_err = headless_prepare_scene_setup_bundle(
        st_module=st,
        scene_template_id=scene_template_id,
        scene_template_role_assignments=scene_template_role_assignments,
        character_card_ids=list(character_card_ids),
        resolved_character_files=resolved_files,
        resolve_scene_template_setup_fn=_resolve_template,
    )
    if setup_err:
        raise ValueError(f"Headless scene template setup failed: {setup_err}")

    if not str(opening_description or "").strip() and not (
        scene_setup and str(scene_setup.get("opening_text") or "").strip()
    ):
        raise ValueError(
            "prepare_headless_session requires opening_description or template opening_text"
        )

    harness_narrative: dict[str, Any] = {}
    if initial_tension is not None:
        harness_narrative["initial_tension"] = str(initial_tension)
    if initial_phase is not None:
        harness_narrative["initial_phase"] = str(initial_phase)

    opener_manager = OpenerManager()
    try:
        interpretation = compose_headless_bootstrap(
            scene_setup=scene_setup,
            character_card_ids=list(character_card_ids),
            opening_description_operand=str(opening_description or ""),
            scenario_raw=scenario_raw,
            cli_trigger_operand=(
                str(cli_trigger_for_composition).strip()
                if cli_trigger_for_composition
                else None
            ),
            harness_location_operand=str(location or ""),
            opener_manager=opener_manager,
            harness_seed_issue=seed_issue,
            harness_narrative_start=harness_narrative or None,
        )
    except BootstrapCompositionError as exc:
        raise ValueError(f"bootstrap composition failed: {exc}") from exc

    opening_final = interpretation.opening_resolved_text
    scene_setup_apply = interpretation.scene_setup_for_continuity_apply()
    st.session_state["bootstrap_interpretation"] = interpretation_to_jsonable(interpretation)
    st.session_state["first_round_user_line_composed"] = interpretation.first_round_user_line
    seed_scene_setup = interpretation_to_seed_scene_setup(interpretation)

    st.session_state["session_id"] = SessionManager().generate_session_id()

    state_helpers.restore_or_initialize_continuity_manager(
        st_module=st,
        continuity_state=None,
        character_names=agent_keys,
        opening_description=opening_final,
        scene_setup=scene_setup_apply,
        continuity_manager_cls=ContinuityManager,
        build_initial_scene_issues_fn=state_helpers.build_initial_scene_issues,
        apply_scene_setup_to_scene_state_fn=_apply_scene_setup_to_scene_state,
        sync_orchestration_state_from_continuity_fn=_sync,
    )

    cm = state_helpers.get_continuity_manager(st_module=st, continuity_manager_cls=ContinuityManager)
    if cm is not None and cm.scene_state is not None:
        cm.scene_state.location = interpretation.location
        cm.notify_raw_location_bypass_for_audit()
        if not str(scene_template_id or "").strip():
            cm.scene_state.scene_template_id = None
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

        mirror_opening_into_scene_state(cm, opening_final)

        cross_payload = app_memory_cross_session.load_cross_session_memories(
            st_module=st,
            character_names=agent_keys,
            user_name=user_name,
            session_manager_cls=SessionManager,
        )
        app_memory_cross_session.apply_cross_session_memories(
            char_states,
            cross_payload,
            user_name,
            st_module=st,
        )
        st.session_state["cross_session_memories"] = cross_payload

        seed_scene_role_character_priorities(
            char_states=char_states, scene_setup=seed_scene_setup
        )
        seed_scene_role_relationship_context(
            char_states=char_states, scene_setup=seed_scene_setup
        )
        cm.seed_character_canon_anchors(char_states)

        _sync()
        ensure_interim_anchor_role_fallback_for_finalize(cm, cast=agent_keys)
        finalize_continuity_setup_seam(cm, cast=agent_keys)

    st.session_state["simulation_opening_final"] = opening_final
    append_scene_opening_chat_message(
        st_module=st,
        opening_final=opening_final,
        user_name=user_name,
    )

    if audit_enabled:
        try:
            audit_logger = get_audit_logger()
            session_owner = (
                st.session_state.get("audit_session_owner")
                or st.session_state.get("scene_owner")
                or owner
            )
            session_num = st.session_state.get("audit_session_number")
            if session_num is None:
                raise ValueError("audit_session_number missing with audit_enabled")
            cm_audit = state_helpers.get_continuity_manager(
                st_module=st, continuity_manager_cls=ContinuityManager
            )
            ss = (
                cm_audit.scene_state
                if cm_audit is not None and cm_audit.scene_state is not None
                else None
            )
            scene_audit_kwargs = get_scene_audit_logging_kwargs(ss)
            audit_logger.write_session_manifest(
                session_owner=session_owner,
                session_number=int(session_num),
                cast=display_names,
                opening_description=opening_final,
                user_name=user_name,
                bootstrap_interpretation=st.session_state.get("bootstrap_interpretation"),
                **scene_audit_kwargs,
            )
            state_helpers.refresh_audit_summary_report(
                st_module=st,
                is_audit_enabled_fn=lambda: bool(
                    st.session_state.get("audit_enabled", False)
                ),
                get_audit_logger_fn=get_audit_logger,
                get_audit_context_fn=lambda: state_helpers.get_audit_context(
                    st_module=st,
                    is_audit_enabled_fn=lambda: bool(
                        st.session_state.get("audit_enabled", False)
                    ),
                    get_audit_logger_fn=get_audit_logger,
                ),
                get_continuity_manager_fn=lambda: state_helpers.get_continuity_manager(
                    st_module=st, continuity_manager_cls=ContinuityManager
                ),
            )
        except Exception as exc:
            log_audit_exception(
                "audit: headless prepare_headless_session write_session_manifest or "
                "refresh_audit_summary_report failed",
                exc,
            )

    if beat_shift_active:
        orch = state_helpers.get_orchestration_state(
            st_module=st, ensure_orchestration_state_fn=ensure_orchestration_state
        )
        pbs = orch.get("pending_beat_shift")
        if isinstance(pbs, dict):
            pbs["active"] = True
            pbs["reason"] = "short_user_message"
            pbs["source_turn_id"] = "headless_sim_user_round_1"

    return st

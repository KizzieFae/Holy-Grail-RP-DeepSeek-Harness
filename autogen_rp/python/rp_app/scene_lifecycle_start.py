from typing import Any, Awaitable, Callable

from audit_instrumentation import log_audit_exception
from continuity_setup_seam_v77 import (
    ContinuitySetupSeamError,
    ensure_interim_anchor_role_fallback_for_finalize,
    finalize_continuity_setup_seam,
)
from bootstrap_composition import (
    BootstrapCompositionError,
    compose_streamlit_bootstrap,
    interpretation_to_jsonable,
    interpretation_to_seed_scene_setup,
    validate_streamlit_opening_mode_untrusted,
)
from scene_start_bootstrap import (
    apply_opener_location_time_to_continuity,
    mirror_opening_into_scene_state,
    resolve_streamlit_opening_narrative,
)
from ui_sidebar_opening import streamlit_opener_selection_error


def _role_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_scene_holder_role(role_name: str) -> bool:
    role = _role_text(role_name)
    return any(
        token in role
        for token in (
            "protector",
            "dominator",
            "holder",
            "host",
            "captor",
            "interrogator",
            "caretaker",
            "guardian",
            "handler",
            "owner",
            "boss",
            "warden",
            "guard",
            "miko",
            "staff",
            "roommate",
            "mother",
        )
    )


def _is_scene_protagonist_role(role_name: str) -> bool:
    role = _role_text(role_name)
    return any(
        token in role
        for token in (
            "protagonist",
            "recovering",
            "patient",
            "guest",
            "subject",
            "captive",
            "ward",
            "charge",
            "outsider",
            "newcomer",
            "supplicant",
            "target",
            "applicant",
            "visitor",
            "arrival",
            "student",
            "child",
            "omega",
        )
    )


def _seed_scene_role_character_priorities(
    *,
    char_states: dict[str, Any],
    scene_setup: dict[str, Any] | None,
) -> None:
    if not scene_setup:
        return

    role_assignments = scene_setup.get("role_assignments", {})
    authority_labels = scene_setup.get("character_authority_labels", {})
    if not isinstance(role_assignments, dict) or not role_assignments:
        return

    character_names = [name for name in char_states if str(name or "").strip()]
    for source_name in character_names:
        source_state = char_states.get(source_name)
        if source_state is None:
            continue
        source_role = _role_text(role_assignments.get(source_name, ""))
        source_authority = _role_text(authority_labels.get(source_name, ""))
        source_is_holder = _is_scene_holder_role(source_role)
        source_is_protagonist = _is_scene_protagonist_role(source_role)

        counterpart_name = ""
        counterpart_is_holder = False
        counterpart_is_protagonist = False
        for target_name in character_names:
            if target_name == source_name:
                continue
            target_role = _role_text(role_assignments.get(target_name, ""))
            if source_is_holder and _is_scene_protagonist_role(target_role):
                counterpart_name = target_name
                counterpart_is_protagonist = True
                break
            if source_is_protagonist and _is_scene_holder_role(target_role):
                counterpart_name = target_name
                counterpart_is_holder = True
                break

        seeded_objective = ""
        seeded_tactic = ""
        if source_is_holder and counterpart_is_protagonist and counterpart_name:
            seeded_objective = f"stabilize {counterpart_name} while controlling the immediate scene around them"
            seeded_tactic = "prioritize assessment, stabilization, and control over low-value local detail while keeping emotional distance"
            if source_authority == "high":
                seeded_tactic = "use firm practical control to assess, stabilize, and direct the scene without letting small subtasks displace the main risk"
        elif source_is_protagonist and counterpart_is_holder and counterpart_name:
            seeded_objective = f"stay responsive and judge whether {counterpart_name}'s control is safe enough to cooperate with"
            seeded_tactic = "cooperate selectively while protecting your condition, freedom, and next options"
        elif source_is_holder:
            seeded_objective = "maintain control of the immediate scene while tracking the highest unresolved pressure"
            seeded_tactic = "keep the scene focused on the main obligation instead of drifting into easy local details"
        elif source_is_protagonist:
            seeded_objective = "stay responsive, protect your condition, and work out the safest next step"
            seeded_tactic = "conserve energy and answer the main pressure instead of getting lost in secondary details"

        if (
            seeded_objective
            and not str(getattr(source_state, "current_objective", "") or "").strip()
        ):
            source_state.current_objective = seeded_objective
        if (
            seeded_tactic
            and not str(getattr(source_state, "short_term_tactic", "") or "").strip()
        ):
            source_state.short_term_tactic = seeded_tactic


def _seed_scene_role_relationship_context(
    *,
    char_states: dict[str, Any],
    scene_setup: dict[str, Any] | None,
) -> None:
    if not scene_setup:
        return

    role_assignments = scene_setup.get("role_assignments", {})
    presence_constraints = scene_setup.get("character_presence_constraints", {})
    authority_labels = scene_setup.get("character_authority_labels", {})
    if not isinstance(role_assignments, dict) or not role_assignments:
        return

    character_names = [name for name in char_states if str(name or "").strip()]
    for source_name in character_names:
        source_state = char_states.get(source_name)
        if source_state is None or not hasattr(
            source_state, "set_relationship_context"
        ):
            continue
        source_role = _role_text(role_assignments.get(source_name, ""))
        source_authority = _role_text(authority_labels.get(source_name, ""))
        source_presence = _role_text(presence_constraints.get(source_name, ""))
        source_is_holder = _is_scene_holder_role(source_role)
        source_is_protagonist = _is_scene_protagonist_role(source_role)

        for target_name in character_names:
            if target_name == source_name:
                continue
            target_role = _role_text(role_assignments.get(target_name, ""))
            target_authority = _role_text(authority_labels.get(target_name, ""))
            target_presence = _role_text(presence_constraints.get(target_name, ""))
            target_is_holder = _is_scene_holder_role(target_role)
            target_is_protagonist = _is_scene_protagonist_role(target_role)

            relationship_kwargs: dict[str, str] | None = None
            if source_is_holder and target_is_protagonist:
                relationship_kwargs = {
                    "stance": (
                        "protective control"
                        if source_authority == "high"
                        else "watchful control"
                    ),
                    "medium_term_goal": f"stabilize {target_name} while controlling the immediate scene around them",
                    "current_objective": f"assess {target_name}'s condition and keep them responsive",
                    "tactical_posture": "use firm practical guidance while keeping emotional distance",
                }
            elif source_is_protagonist and target_is_holder:
                relationship_kwargs = {
                    "stance": "wary dependence",
                    "medium_term_goal": f"secure safety from {target_name} without surrendering autonomy",
                    "current_objective": f"judge whether {target_name}'s control is safe enough to cooperate with",
                    "tactical_posture": "cooperate selectively while preserving freedom and leverage",
                }
            elif source_is_holder and target_is_holder:
                relationship_kwargs = {
                    "stance": "measured coordination",
                    "medium_term_goal": f"manage the power dynamic with {target_name} without losing control of the scene",
                    "current_objective": f"coordinate with or outmaneuver {target_name} as needed",
                    "tactical_posture": "test alignment while guarding authority",
                }
            elif source_presence == "must_remain" and target_presence == "must_remain":
                relationship_kwargs = {
                    "stance": "watchful caution",
                    "tactical_posture": "keep them in peripheral awareness while focusing on the scene's core pressure",
                    "threat_level": (
                        "moderate" if target_authority in ("high", "medium") else "low"
                    ),
                    "usefulness": "situational",
                }

            if relationship_kwargs is None:
                continue
            source_state.set_relationship_context(target_name, **relationship_kwargs)


async def start_scene(
    *,
    st_module: Any,
    selected_chars: list[str],
    has_player_character_conflict_fn: Callable[[list[str], str | None], bool],
    close_active_scene_if_needed_fn: Callable[[str], Awaitable[None]],
    shutdown_runtime_resources_fn: Callable[[], Awaitable[None]],
    reset_state_for_new_scene_fn: Callable[[], None],
    create_deepseek_client_fn: Callable[[], Any],
    character_loader_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
    resolve_scene_template_setup_fn: Callable[
        [list[str], dict[str, str]], tuple[dict[str, Any] | None, str]
    ],
    resolve_bot_reply_limit_fn: Callable[[int, int | None], int],
    get_character_display_names_fn: Callable[[list[str]], list[str]],
    restore_or_initialize_continuity_manager_fn: Callable[..., Any],
    character_state_manager_cls: Any,
    load_cross_session_memories_fn: Callable[[list[str], str], dict[str, Any]],
    apply_cross_session_memories_fn: Callable[
        [dict[str, Any], dict[str, Any], str], None
    ],
    get_continuity_manager_fn: Callable[[], Any],
    create_narrator_agent_fn: Callable[[Any], Any],
    create_director_agent_fn: Callable[[Any], Any],
    session_manager_cls: Any,
    opener_manager_cls: Any,
    is_audit_enabled_fn: Callable[[], bool],
    get_audit_logger_fn: Callable[[], Any],
    get_audit_context_fn: Callable[[], tuple[str, int, int, int]],
    get_scene_audit_logging_kwargs_fn: Callable[[Any | None], dict[str, Any]],
    refresh_audit_summary_report_fn: Callable[[], None],
    run_character_turns_fn: Callable[..., Awaitable[None]],
    save_current_session_fn: Callable[..., Awaitable[None]],
    sync_orchestration_state_from_continuity_fn: Callable[[], None],
    get_orchestration_state_fn: Callable[[], dict[str, Any]],
    build_scene_role_prompt_context_fn: Callable[
        [dict[str, Any] | None, list[str] | None], list[dict[str, str]]
    ],
) -> bool:
    player_character = st_module.session_state.get("player_character")
    if has_player_character_conflict_fn(selected_chars, player_character):
        st_module.error(
            "The same character cannot be both player-controlled and bot-controlled in the same scene."
        )
        return False

    await close_active_scene_if_needed_fn("new_scene_started")
    await shutdown_runtime_resources_fn()
    reset_state_for_new_scene_fn()

    try:
        opening_mode = validate_streamlit_opening_mode_untrusted(
            st_module.session_state.get("opening_mode")
        )
    except BootstrapCompositionError as exc:
        st_module.error(str(exc))
        return False
    st_module.session_state["opening_mode"] = opening_mode

    try:
        model_client = create_deepseek_client_fn()
    except ValueError as exc:
        st_module.error(f"Model client error: {exc}")
        return False

    st_module.session_state["model_client"] = model_client

    loader = character_loader_cls()
    char_agents = []
    char_names = []
    char_states = {}
    character_names_by_file: dict[str, str] = {}

    for char_file in selected_chars:
        try:
            agent, state = loader.load_and_create_agent(char_file, model_client)
            char_agents.append(agent)
            char_names.append(agent.name)
            char_states[agent.name] = state
            character_names_by_file[char_file] = agent.name
        except FileNotFoundError as exc:
            st_module.error(f"Failed to load character: {exc}")
            return False

    scene_setup, scene_setup_error = resolve_scene_template_setup_fn(
        selected_chars,
        character_names_by_file,
    )
    if scene_setup_error:
        st_module.error(scene_setup_error)
        return False

    st_module.session_state["characters"] = char_agents
    st_module.session_state["character_states"] = char_states
    existing_bot_reply_limit = st_module.session_state.get("bot_reply_limit")
    st_module.session_state["bot_reply_limit"] = resolve_bot_reply_limit_fn(
        len(char_agents), existing_bot_reply_limit
    )
    display_char_names = get_character_display_names_fn(char_names)
    user_name = st_module.session_state.get("user_name", "Traveler")

    scene_owner = st_module.session_state.get(
        "scene_owner", display_char_names[0] if display_char_names else "Unknown"
    )
    st_module.session_state["scene_owner"] = scene_owner
    st_module.session_state["audit_session_owner"] = (
        scene_owner if is_audit_enabled_fn() else None
    )
    selected_opener_id = st_module.session_state.get("selected_opener_id")
    custom_text = st_module.session_state.get("custom_opener_text", "")

    opener_manager = opener_manager_cls()
    selection_err = streamlit_opener_selection_error(
        opening_mode=opening_mode,
        selected_opener_id=(
            (str(selected_opener_id).strip() or None)
            if selected_opener_id is not None
            else None
        ),
        scene_setup=scene_setup,
        opener_manager=opener_manager,
    )
    if selection_err:
        st_module.error(selection_err)
        return False

    narrator = create_narrator_agent_fn(model_client)

    async def _generate_opening() -> str:
        return await resolve_streamlit_opening_narrative(
            scene_setup=scene_setup,
            opener=None,
            resolve_opening_text_fn=lambda _s, _o: "",
            display_char_names=display_char_names,
            char_names=char_names,
            user_name=user_name,
            scene_owner=scene_owner,
            build_scene_role_prompt_context_fn=build_scene_role_prompt_context_fn,
            narrator=narrator,
        )

    with st_module.spinner("Narrator is setting the scene..."):
        try:
            interpretation, res_opener = await compose_streamlit_bootstrap(
                scene_setup=scene_setup,
                character_card_ids_or_files=selected_chars,
                display_names=display_char_names,
                opening_mode=opening_mode,
                specific_opener_id=selected_opener_id,
                custom_text=custom_text,
                scene_owner=scene_owner,
                opener_manager=opener_manager,
                authored_bootstrap_document=None,
                generate_opening_fn=_generate_opening,
                scenario_raw=None,
                cli_trigger_operand=None,
                template_default_location=None,
            )
        except BootstrapCompositionError as exc:
            st_module.error(str(exc))
            return False

    st_module.session_state["bootstrap_interpretation"] = interpretation_to_jsonable(
        interpretation
    )
    opening_description = interpretation.opening_resolved_text
    scene_setup_apply = interpretation.scene_setup_for_continuity_apply()
    scene_setup_for_seed = interpretation_to_seed_scene_setup(interpretation)

    restore_or_initialize_continuity_manager_fn(
        None,
        char_names,
        opening_description,
        scene_setup_apply,
    )

    state_manager = character_state_manager_cls()
    for name, state in char_states.items():
        state_manager.register_character(name, state)
    st_module.session_state["character_state_manager"] = state_manager
    cross_session_memories = load_cross_session_memories_fn(char_names, user_name)
    apply_cross_session_memories_fn(char_states, cross_session_memories, user_name)
    _seed_scene_role_character_priorities(
        char_states=char_states, scene_setup=scene_setup_for_seed
    )
    _seed_scene_role_relationship_context(
        char_states=char_states, scene_setup=scene_setup_for_seed
    )
    st_module.session_state["cross_session_memories"] = cross_session_memories
    continuity_manager = get_continuity_manager_fn()
    if continuity_manager is not None:
        continuity_manager.seed_character_canon_anchors(char_states)

    director = create_director_agent_fn(model_client)

    session_manager = session_manager_cls()
    session_id = session_manager.generate_session_id(char_names)
    st_module.session_state["session_id"] = session_id
    st_module.session_state["team_state"] = None

    if continuity_manager and continuity_manager.scene_state:
        mirror_opening_into_scene_state(continuity_manager, opening_description)
        continuity_manager.scene_state.location = interpretation.location
        continuity_manager.notify_raw_location_bypass_for_audit()
        apply_opener_location_time_to_continuity(
            continuity_manager, res_opener, apply_location=False
        )
        sync_orchestration_state_from_continuity_fn()

    if continuity_manager is not None and continuity_manager.scene_state is not None:
        try:
            ensure_interim_anchor_role_fallback_for_finalize(
                continuity_manager, cast=char_names
            )
            finalize_continuity_setup_seam(continuity_manager, cast=char_names)
        except ContinuitySetupSeamError as exc:
            st_module.error(str(exc))
            return False

    st_module.session_state["chat_history"].append(
        {
            "role": "system",
            "content": f"**Scene Opening**\n\n{opening_description}\n\n**You are playing as**: {user_name}",
            "speaker": "Narrator",
        }
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
            audit_logger.write_session_manifest(
                session_owner=session_owner,
                session_number=session_num,
                cast=display_char_names,
                opening_description=opening_description,
                user_name=user_name,
                bootstrap_interpretation=st_module.session_state.get(
                    "bootstrap_interpretation"
                ),
                **scene_audit_kwargs,
            )
            refresh_audit_summary_report_fn()
        except Exception as exc:
            log_audit_exception(
                "audit: scene start write_session_manifest or "
                "refresh_audit_summary_report failed",
                exc,
            )
            st_module.error(
                "Audit logging failed during scene start (manifest write or summary "
                "refresh, including retrieval_session merge). The scene will continue, "
                f"but audit artifacts may be incomplete. Details: {exc}"
            )

    await run_character_turns_fn(
        char_agents=char_agents,
        narrator=narrator,
        director=director,
        trigger_text=interpretation.first_round_user_line,
        user_name=user_name,
    )

    st_module.session_state["scene_started"] = True
    await save_current_session_fn()
    return True


async def recreate_team_from_state(
    *,
    st_module: Any,
    rebuild_character_agents_fn: Callable[[Any], list[Any]],
    get_orchestration_state_fn: Callable[[], dict[str, Any]],
    get_continuity_manager_fn: Callable[[], Any],
    restore_or_initialize_continuity_manager_fn: Callable[..., Any],
    create_narrator_agent_fn: Callable[[Any], Any],
    create_director_agent_fn: Callable[[Any], Any],
) -> tuple[Any, Any, Any, Any]:
    model_client = st_module.session_state.get("model_client")
    characters = st_module.session_state.get("characters", [])

    if not model_client:
        return None, None, None, None

    if not characters:
        rebuilt_characters = rebuild_character_agents_fn(model_client)
        if rebuilt_characters:
            characters = rebuilt_characters

    if not characters:
        return None, None, None, None

    get_orchestration_state_fn()
    if get_continuity_manager_fn() is None:
        restore_or_initialize_continuity_manager_fn(
            None,
            [agent.name for agent in characters],
            get_orchestration_state_fn()
            .get("scene_state", {})
            .get("opening_description", ""),
        )
    cm = get_continuity_manager_fn()
    if (
        cm is not None
        and cm.scene_state is not None
        and not cm.setup_seam_complete
    ):
        orch = get_orchestration_state_fn()
        ra = orch.get("scene_state", {}).get("role_assignments")
        if isinstance(ra, dict) and ra:
            merged = dict(cm.scene_state.role_assignments or {})
            for k, v in ra.items():
                merged[str(k)] = str(v) if v is not None else ""
            cm.scene_state.role_assignments = merged
        ensure_interim_anchor_role_fallback_for_finalize(
            cm, cast=[agent.name for agent in characters]
        )
        finalize_continuity_setup_seam(cm, cast=[agent.name for agent in characters])
    narrator = create_narrator_agent_fn(model_client)
    director = create_director_agent_fn(model_client)
    return characters, narrator, director, model_client


# Public aliases (e.g. headless imports shared seeding without duplicating helpers).
seed_scene_role_character_priorities = _seed_scene_role_character_priorities
seed_scene_role_relationship_context = _seed_scene_role_relationship_context

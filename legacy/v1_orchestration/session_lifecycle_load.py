from typing import Any, Awaitable, Callable

from bootstrap_composition import (
    STREAMLIT_OPENING_MODE_CHARACTER,
    STREAMLIT_OPENING_MODE_CUSTOM,
    STREAMLIT_OPENING_MODE_GENERATED,
    STREAMLIT_OPENING_MODE_TEMPLATE,
    migrate_legacy_generated_streamlit_opening_state,
    VALID_STREAMLIT_OPENING_MODES,
)
from continuity_setup_seam_v77 import ContinuitySetupSeamError
from scene_opener import OpenerManager
from scene_template import SceneTemplateManager
from ui_sidebar_opening import streamlit_opener_scope_fingerprint


async def load_existing_session(
    *,
    st_module: Any,
    session_id: str,
    close_active_scene_if_needed_fn: Callable[[str], Awaitable[None]],
    shutdown_runtime_resources_fn: Callable[[], Awaitable[None]],
    session_manager_cls: Any,
    character_loader_cls: Any,
    create_deepseek_client_fn: Callable[[], Any],
    character_state_from_dict_fn: Callable[[dict[str, Any]], Any],
    make_agent_identifier_fn: Callable[[str], str],
    resolve_character_file_fn: Callable[[Any, str], str | None],
    load_cross_session_memories_fn: Callable[[list[str], str], dict[str, Any]],
    apply_cross_session_memories_fn: Callable[
        [dict[str, Any], dict[str, Any], str], None
    ],
    character_state_manager_cls: Any,
    restore_or_initialize_continuity_manager_fn: Callable[..., Any],
    get_continuity_manager_fn: Callable[[], Any],
    resolve_bot_reply_limit_fn: Callable[[int, int | None], int],
    has_player_character_conflict_fn: Callable[[list[str], str | None], bool],
) -> None:
    await close_active_scene_if_needed_fn("session_loaded")
    await shutdown_runtime_resources_fn()

    session_manager = session_manager_cls()

    try:
        session_data = session_manager.load_session(session_id)
    except FileNotFoundError:
        st_module.error(f"Session not found: {session_id}")
        return

    player_character = session_data.get("player_character")
    st_module.session_state["player_character"] = player_character or None
    st_module.session_state.pop("player_character_select", None)
    if player_character:
        loader = character_loader_cls()
        try:
            char_card = loader.load_character_card(player_character)
            st_module.session_state["user_name"] = char_card.get(
                "name", player_character
            )
        except Exception:
            st_module.session_state["user_name"] = player_character

    chat_history = session_data.get("chat_history", [])
    st_module.session_state["chat_history"] = chat_history if chat_history else []

    user_name = st_module.session_state.get("user_name", "Traveler")
    char_states_data = session_data.get("metadata", {}).get("character_states", {})
    restored_states: dict[str, Any] = {}
    if char_states_data:
        for name, state_dict in char_states_data.items():
            state = character_state_from_dict_fn(state_dict)
            restored_states[name] = state

    try:
        model_client = create_deepseek_client_fn()
    except ValueError as exc:
        st_module.error(f"Model client error: {exc}")
        return

    st_module.session_state["model_client"] = model_client

    char_names = session_data.get("characters", [])
    loader = character_loader_cls()
    agents = []
    restored_state_aliases: dict[str, Any] = {}
    for key, state in restored_states.items():
        restored_state_aliases[str(key)] = state
        restored_state_aliases[make_agent_identifier_fn(str(key))] = state
        if str(state.name).strip():
            restored_state_aliases[str(state.name).strip()] = state
            restored_state_aliases[
                make_agent_identifier_fn(str(state.name).strip())
            ] = state
    char_states: dict[str, Any] = {}
    resolved_files: list[str] = []

    for name in char_names:
        char_file = resolve_character_file_fn(loader, name)
        if char_file is None:
            st_module.warning(f"Could not resolve character file for: {name}")
            continue
        try:
            agent, state = loader.load_and_create_agent(char_file, model_client)
            agents.append(agent)
            resolved_files.append(char_file)
            char_states[agent.name] = (
                restored_state_aliases.get(agent.name)
                or restored_state_aliases.get(name)
                or state
            )
        except FileNotFoundError:
            st_module.warning(f"Could not reload character: {name}")

    if not agents:
        st_module.error("No valid characters found in session")
        return

    st_module.session_state["characters"] = agents
    st_module.session_state["selected_chars"] = resolved_files
    st_module.session_state.pop("npc_selection", None)
    st_module.session_state["character_states"] = char_states
    cross_session_memories = load_cross_session_memories_fn(
        [agent.name for agent in agents],
        user_name,
    )
    apply_cross_session_memories_fn(char_states, cross_session_memories, user_name)
    st_module.session_state["cross_session_memories"] = cross_session_memories
    state_manager = character_state_manager_cls()
    for name, state in char_states.items():
        state_manager.register_character(name, state)
    st_module.session_state["character_state_manager"] = state_manager
    st_module.session_state["team_state"] = session_data.get("team_state", {})
    try:
        restore_or_initialize_continuity_manager_fn(
            session_data.get("metadata", {}).get("continuity_state"),
            [agent.name for agent in agents],
            st_module.session_state["team_state"]
            .get("scene_state", {})
            .get("opening_description", ""),
        )
    except ContinuitySetupSeamError as exc:
        st_module.error(f"Continuity setup seam invalid: {exc}")
        return
    continuity_manager = get_continuity_manager_fn()
    if continuity_manager is not None:
        continuity_manager.seed_character_canon_anchors(char_states)
        from scene_grounding import rebuild_scene_grounding_from_continuity

        st_module.session_state["scene_grounding"] = (
            rebuild_scene_grounding_from_continuity(continuity_manager)
        )
    else:
        from scene_grounding import grounding_dict_from_session_metadata

        st_module.session_state["scene_grounding"] = grounding_dict_from_session_metadata(
            session_data.get("metadata", {})
        )
    st_module.session_state["session_id"] = session_id
    restored_scene_state = (
        continuity_manager.scene_state if continuity_manager is not None else None
    )
    st_module.session_state["selected_scene_template_id"] = session_data.get(
        "metadata", {}
    ).get("scene_template_id") or (
        restored_scene_state.scene_template_id
        if restored_scene_state is not None
        else None
    )
    restored_role_assignments = (
        restored_scene_state.role_assignments
        if restored_scene_state is not None
        else session_data.get("metadata", {}).get("scene_role_assignments", {})
    )
    st_module.session_state["scene_role_assignments"] = {
        char_file: restored_role_assignments.get(agent.name, "")
        for agent, char_file in zip(agents, resolved_files, strict=False)
        if restored_role_assignments.get(agent.name, "")
    }
    _meta = session_data.get("metadata") or {}
    # Issue #106: audit identity must come from ``audit_session_owner`` in metadata only.
    # Do not derive from ``scene_owner`` or other UI fields; missing owner disables audit.
    saved_audit_enabled = bool(
        _meta.get("audit_enabled", _meta.get("audit_session_number") is not None)
    )
    st_module.session_state.pop("audit_enabled_toggle", None)

    saved_audit_owner_raw = _meta.get("audit_session_owner")
    saved_audit_owner = (
        str(saved_audit_owner_raw).strip()
        if saved_audit_owner_raw is not None and str(saved_audit_owner_raw).strip()
        else None
    )
    if saved_audit_enabled and not saved_audit_owner:
        st_module.session_state["audit_enabled"] = False
        st_module.session_state["audit_session_owner"] = None
        st_module.warning(
            "This saved session has no canonical **audit_session_owner** in metadata; "
            "auditing is disabled. Legacy sessions are not audit-supported (Issue #106). "
            "Start a new scene with auditing enabled to produce new audit artifacts."
        )
    else:
        st_module.session_state["audit_enabled"] = saved_audit_enabled
        st_module.session_state["audit_session_owner"] = (
            saved_audit_owner if saved_audit_enabled else None
        )

    saved_scene_owner_ui = _meta.get("scene_owner")
    if saved_scene_owner_ui is not None and str(saved_scene_owner_ui).strip():
        st_module.session_state["scene_owner"] = str(saved_scene_owner_ui).strip()
    elif char_names:
        st_module.session_state["scene_owner"] = char_names[0]
    else:
        st_module.session_state["scene_owner"] = "Unknown"
    st_module.session_state.pop("scene_owner_select", None)
    st_module.session_state.pop("scene_owner_display", None)
    # Issue #100: non-canonical saved values must be unset (None), not coerced to a default mode.
    # Issue #108: legacy ``character`` opening_mode migrates to template or custom; clears opener pick.
    # Issue #113: legacy ``generated`` migrates to template (preserving a valid ``selected_opener_id``) or custom.
    _saved_opener_raw = _meta.get("selected_opener_id")
    if "opening_mode" in _meta:
        _raw_om: object = _meta.get("opening_mode")
    else:
        _raw_om = st_module.session_state.get("opening_mode", "custom")
    _s = str(_raw_om).strip().lower() if _raw_om is not None else ""
    migrated_from_character = _s == STREAMLIT_OPENING_MODE_CHARACTER
    migrated_from_generated = _s == STREAMLIT_OPENING_MODE_GENERATED
    if migrated_from_character:
        _tid = st_module.session_state.get("selected_scene_template_id")
        if _tid and str(_tid).strip():
            st_module.session_state["opening_mode"] = STREAMLIT_OPENING_MODE_TEMPLATE
        else:
            st_module.session_state["opening_mode"] = STREAMLIT_OPENING_MODE_CUSTOM
    elif migrated_from_generated:
        _tid_g = st_module.session_state.get("selected_scene_template_id")
        _om = OpenerManager()
        _tm = SceneTemplateManager()
        _ts = str(_tid_g).strip() if _tid_g else ""
        _topts = _om.get_template_openers(_ts, _tm) if _ts else []
        nmode, noid = migrate_legacy_generated_streamlit_opening_state(
            opening_mode=STREAMLIT_OPENING_MODE_GENERATED,
            selected_template_id=_tid_g if _tid_g else None,
            selected_opener_id=_saved_opener_raw
            if _saved_opener_raw is not None
            else None,
            template_openers=_topts,
        )
        st_module.session_state["opening_mode"] = nmode
    elif not _s or _s not in VALID_STREAMLIT_OPENING_MODES:
        st_module.session_state["opening_mode"] = None
    else:
        st_module.session_state["opening_mode"] = _s
    if migrated_from_character:
        st_module.session_state["selected_opener_id"] = None
    elif migrated_from_generated:
        st_module.session_state["selected_opener_id"] = noid
    else:
        st_module.session_state["selected_opener_id"] = _saved_opener_raw
    st_module.session_state["opener_selection_scope_key"] = (
        streamlit_opener_scope_fingerprint(
            str(st_module.session_state.get("opening_mode") or "custom"),
            st_module.session_state.get("selected_scene_template_id"),
        )
    )
    st_module.session_state["custom_opener_text"] = session_data.get(
        "metadata", {}
    ).get("custom_opener_text", "")
    st_module.session_state["audit_session_number"] = session_data.get(
        "metadata", {}
    ).get("audit_session_number")
    st_module.session_state["audit_round_number"] = session_data.get(
        "metadata", {}
    ).get("audit_round_number", 0)
    st_module.session_state["audit_turn_number"] = session_data.get("metadata", {}).get(
        "audit_turn_number", 0
    )
    st_module.session_state["audit_summary_report_path"] = None
    saved_bot_reply_limit = session_data.get("metadata", {}).get("bot_reply_limit")
    resolved_bot_reply_limit = resolve_bot_reply_limit_fn(
        len(agents), saved_bot_reply_limit
    )
    st_module.session_state["bot_reply_limit"] = resolved_bot_reply_limit
    st_module.session_state["bot_reply_limit_widget_nonce"] = (
        int(st_module.session_state.get("bot_reply_limit_widget_nonce", 0) or 0) + 1
    )
    if has_player_character_conflict_fn(
        resolved_files, st_module.session_state.get("player_character")
    ):
        st_module.warning(
            "Loaded session uses a character as both player-controlled and bot-controlled. The player-controlled version takes precedence in new scenes."
        )
    st_module.session_state["scene_started"] = True
    st_module.session_state["scene_ended"] = False

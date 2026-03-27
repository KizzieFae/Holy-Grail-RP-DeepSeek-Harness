from typing import Any, Awaitable, Callable


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
    cross_session_memories = session_manager.get_cross_session_memories(
        character_names=[agent.name for agent in agents],
        user_name=user_name,
        exclude_session_id=session_id,
    )
    apply_cross_session_memories_fn(char_states, cross_session_memories, user_name)
    st_module.session_state["cross_session_memories"] = cross_session_memories
    state_manager = character_state_manager_cls()
    for name, state in char_states.items():
        state_manager.register_character(name, state)
    st_module.session_state["character_state_manager"] = state_manager
    st_module.session_state["team_state"] = session_data.get("team_state", {})
    restore_or_initialize_continuity_manager_fn(
        session_data.get("metadata", {}).get("continuity_state"),
        [agent.name for agent in agents],
        st_module.session_state["team_state"]
        .get("scene_state", {})
        .get("opening_description", ""),
    )
    continuity_manager = get_continuity_manager_fn()
    if continuity_manager is not None:
        continuity_manager.seed_character_canon_anchors(char_states)
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
    saved_audit_enabled = session_data.get("metadata", {}).get(
        "audit_enabled",
        session_data.get("metadata", {}).get("audit_session_number") is not None,
    )
    st_module.session_state["audit_enabled"] = saved_audit_enabled
    st_module.session_state.pop("audit_enabled_toggle", None)
    saved_scene_owner = session_data.get("metadata", {}).get(
        "audit_session_owner",
        session_data.get("metadata", {}).get(
            "scene_owner", st_module.session_state.get("scene_owner")
        ),
    )
    st_module.session_state["scene_owner"] = saved_scene_owner
    st_module.session_state["audit_session_owner"] = (
        saved_scene_owner if saved_audit_enabled else None
    )
    st_module.session_state.pop("scene_owner_select", None)
    st_module.session_state["opening_mode"] = session_data.get("metadata", {}).get(
        "opening_mode", st_module.session_state.get("opening_mode", "character")
    )
    st_module.session_state["selected_opener_id"] = session_data.get(
        "metadata", {}
    ).get("selected_opener_id")
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

from typing import Any, Callable


async def save_current_session(
    *,
    st_module: Any,
    scene_status: str | None,
    scene_closed_reason: str | None,
    sync_orchestration_state_from_continuity_fn: Callable[[], None],
    get_continuity_manager_fn: Callable[[], Any],
    is_audit_enabled_fn: Callable[[], bool],
    get_current_bot_reply_limit_fn: Callable[[int], int],
    session_manager_cls: Any,
    build_memory_buckets_fn: Callable[
        [str, Any, list[dict[str, Any]], str], dict[str, Any]
    ],
    get_player_control_mode_fn: Callable[[str | None], str],
    get_scene_status_fn: Callable[..., str],
) -> None:
    sync_orchestration_state_from_continuity_fn()
    session_id = st_module.session_state.get("session_id")
    characters = st_module.session_state.get("characters", [])
    team_state = st_module.session_state.get("team_state")
    player_character = st_module.session_state.get("player_character")
    chat_history = st_module.session_state.get("chat_history", [])
    character_states = st_module.session_state.get("character_states", {})
    continuity_manager = get_continuity_manager_fn()
    audit_session_number = st_module.session_state.get("audit_session_number")
    audit_round_number = st_module.session_state.get("audit_round_number", 0)
    audit_turn_number = st_module.session_state.get("audit_turn_number", 0)
    scene_owner = st_module.session_state.get("scene_owner")
    audit_session_owner = st_module.session_state.get("audit_session_owner")
    audit_enabled = is_audit_enabled_fn()
    bot_reply_limit = get_current_bot_reply_limit_fn(len(characters))

    if not team_state or not session_id:
        return

    session_manager = session_manager_cls()
    char_names = [c.name for c in characters]

    summary = "RP session"
    if chat_history:
        recent = [m["content"] for m in chat_history[-3:] if m["role"] != "system"]
        if recent:
            summary = recent[-1][:80] + "..." if len(recent[-1]) > 80 else recent[-1]

    char_states_dict = {
        name: state.to_dict() for name, state in character_states.items()
    }
    memory_buckets = build_memory_buckets_fn(
        summary,
        continuity_manager,
        chat_history,
        st_module.session_state.get("user_name", "Traveler"),
    )

    session_manager.save_session(
        session_id=session_id,
        team_state=team_state,
        characters=char_names,
        metadata={
            "summary": summary,
            "character_states": char_states_dict,
            "memory_buckets": memory_buckets,
            "bot_reply_limit": bot_reply_limit,
            "continuity_state": (
                continuity_manager.to_dict() if continuity_manager is not None else None
            ),
            "player_control_mode": get_player_control_mode_fn(player_character),
            "scene_status": get_scene_status_fn(scene_status),
            "scene_closed_reason": scene_closed_reason,
            "audit_enabled": audit_enabled,
            "audit_session_number": audit_session_number,
            "audit_round_number": audit_round_number,
            "audit_turn_number": audit_turn_number,
            "scene_owner": scene_owner,
            "audit_session_owner": audit_session_owner,
            "scene_template_id": (
                continuity_manager.scene_state.scene_template_id
                if continuity_manager is not None
                and continuity_manager.scene_state is not None
                else None
            ),
            "scene_role_assignments": (
                continuity_manager.scene_state.role_assignments
                if continuity_manager is not None
                and continuity_manager.scene_state is not None
                else {}
            ),
            "opening_mode": st_module.session_state.get("opening_mode", "custom"),
            "selected_opener_id": st_module.session_state.get("selected_opener_id"),
            "custom_opener_text": st_module.session_state.get("custom_opener_text", ""),
            "scene_grounding": st_module.session_state.get("scene_grounding"),
        },
        player_character=player_character,
        chat_history=chat_history,
    )

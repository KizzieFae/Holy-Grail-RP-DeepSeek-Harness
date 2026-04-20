from typing import Any


def get_current_bot_reply_limit(
    *,
    st_module: Any,
    active_bot_count: int,
    get_bot_reply_limit_widget_key_fn,
    resolve_bot_reply_limit_fn,
) -> int:
    configured_limit = st_module.session_state.get("bot_reply_limit")
    widget_limit = st_module.session_state.get(get_bot_reply_limit_widget_key_fn())
    if isinstance(widget_limit, int):
        configured_limit = widget_limit
    if isinstance(configured_limit, int):
        return resolve_bot_reply_limit_fn(active_bot_count, configured_limit)
    return resolve_bot_reply_limit_fn(active_bot_count, None)


def get_bot_reply_limit_widget_key(*, st_module: Any) -> str:
    nonce = int(st_module.session_state.get("bot_reply_limit_widget_nonce", 0) or 0)
    return f"bot_reply_limit_widget_{nonce}"


def init_session_state(*, st_module: Any) -> None:
    defaults = {
        "model_client": None,
        "characters": [],
        "character_states": {},
        "character_state_manager": None,
        "session_id": None,
        "chat_history": [],
        "selected_chars": [],
        "scene_started": False,
        "scene_ended": False,
        "user_name": "Traveler",
        "user_description": "A mysterious newcomer",
        "team_state": None,
        "player_character": None,
        "pending_forced_speaker": None,
        "forced_speaker_consumed": False,
        "debug_mode": False,
        "selector_decisions": [],
        "rejected_messages": [],
        "scene_owner": None,
        "opening_mode": "character",
        "selected_opener_id": None,
        "custom_opener_text": "",
        "selected_scene_template_id": None,
        "scene_role_assignments": {},
        "bot_reply_limit": None,
        "bot_reply_limit_widget_nonce": 0,
        "audit_enabled": False,
        "llm_audit_enabled": False,
        "audit_round_number": 0,
        "audit_turn_number": 0,
        "audit_session_number": None,
        "audit_session_owner": None,
        "audit_summary_report_path": None,
        "sim_retrieval_saw_nonempty_bundle": False,
        "startup_recovery_completed": False,
        "recovered_session_ids": [],
        "continuity_manager": None,
        "cross_session_memories": {},
        "cross_session_injection_report": None,
    }

    for key, value in defaults.items():
        if key not in st_module.session_state:
            st_module.session_state[key] = value


def get_orchestration_state(
    *, st_module: Any, ensure_orchestration_state_fn
) -> dict[str, Any]:
    state = ensure_orchestration_state_fn(st_module.session_state.get("team_state"))
    st_module.session_state["team_state"] = state
    return state


def reset_state_for_new_scene(
    *, st_module: Any, get_audit_logger_fn, is_audit_enabled_fn
) -> None:
    from scene_grounding import empty_grounding_dict

    st_module.session_state["scene_grounding"] = empty_grounding_dict()
    st_module.session_state["chat_history"] = []
    st_module.session_state["team_state"] = None
    st_module.session_state["model_client"] = None
    st_module.session_state["characters"] = []
    st_module.session_state["character_states"] = {}
    st_module.session_state["character_state_manager"] = None
    st_module.session_state["selector_decisions"] = []
    st_module.session_state["rejected_messages"] = []
    st_module.session_state["pending_forced_speaker"] = None
    st_module.session_state["forced_speaker_consumed"] = False
    st_module.session_state["scene_started"] = False
    st_module.session_state["scene_ended"] = False
    st_module.session_state["bot_reply_limit"] = None
    st_module.session_state["bot_reply_limit_widget_nonce"] = (
        int(st_module.session_state.get("bot_reply_limit_widget_nonce", 0) or 0) + 1
    )
    st_module.session_state["audit_round_number"] = 0
    st_module.session_state["audit_turn_number"] = 0
    st_module.session_state["audit_session_number"] = (
        get_audit_logger_fn().get_next_session_number()
        if is_audit_enabled_fn()
        else None
    )
    st_module.session_state["audit_session_owner"] = None
    st_module.session_state["audit_summary_report_path"] = None
    st_module.session_state["sim_retrieval_saw_nonempty_bundle"] = False
    st_module.session_state["continuity_manager"] = None
    st_module.session_state["cross_session_memories"] = {}
    st_module.session_state["cross_session_injection_report"] = None

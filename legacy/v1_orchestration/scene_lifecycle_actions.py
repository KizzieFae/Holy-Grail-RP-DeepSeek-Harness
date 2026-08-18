from typing import Any, Awaitable, Callable


def _clear_fresh_scene_setup_state(st_module: Any) -> None:
    """Reset NPC multiselect carry-over after a scene is closed (Issue #104)."""
    st_module.session_state["selected_chars"] = []
    st_module.session_state.pop("npc_selection", None)
    st_module.session_state["scene_owner"] = None


def get_scene_status(
    *, scene_status: str | None, scene_ended: bool, scene_started: bool
) -> str:
    if scene_status is not None:
        return scene_status
    if scene_ended:
        return "closed"
    if scene_started:
        return "active"
    return "inactive"


async def close_active_scene_if_needed(
    *,
    st_module: Any,
    reason: str,
    save_current_session_fn: Callable[..., Awaitable[None]],
) -> None:
    if not st_module.session_state.get("scene_started"):
        return

    await save_current_session_fn(scene_status="closed", scene_closed_reason=reason)
    st_module.session_state["scene_started"] = False
    st_module.session_state["scene_ended"] = True
    _clear_fresh_scene_setup_state(st_module)


async def skip_turn(
    *,
    st_module: Any,
    recreate_team_from_state_fn: Callable[[], Awaitable[tuple[Any, Any, Any, Any]]],
    run_character_turns_fn: Callable[..., Awaitable[None]],
    save_current_session_fn: Callable[..., Awaitable[None]],
) -> None:
    characters, narrator, director, _model_client = await recreate_team_from_state_fn()
    if not characters or not narrator or not director:
        st_module.error("Failed to recreate scene!")
        return

    user_name = st_module.session_state.get("user_name", "You")
    st_module.session_state["chat_history"].append(
        {
            "role": "system",
            "content": "*{{user}} observes silently...*".replace("{{user}}", user_name),
            "speaker": "Narrator",
        }
    )

    skip_prompt = "The scene continues. {{user}} is present but silent, observing the interaction. The characters should continue their conversation naturally."
    skip_prompt = skip_prompt.replace("{{user}}", user_name)

    await run_character_turns_fn(
        char_agents=characters,
        narrator=narrator,
        director=director,
        trigger_text=skip_prompt,
        user_name=user_name,
    )

    await save_current_session_fn()


async def end_scene(
    *,
    st_module: Any,
    save_current_session_fn: Callable[..., Awaitable[None]],
    shutdown_runtime_resources_fn: Callable[[], Awaitable[None]],
) -> None:
    session_id = st_module.session_state.get("session_id")

    if not session_id:
        st_module.warning("No active scene to end.")
        return

    st_module.session_state["chat_history"].append(
        {
            "role": "system",
            "content": f"**Scene Ended** - Session saved as `{session_id}`. You can resume this scene later from the sidebar.",
            "speaker": "Narrator",
        }
    )

    st_module.session_state["scene_started"] = False
    st_module.session_state["scene_ended"] = True
    await save_current_session_fn(
        scene_status="closed", scene_closed_reason="user_ended"
    )
    await shutdown_runtime_resources_fn()
    _clear_fresh_scene_setup_state(st_module)

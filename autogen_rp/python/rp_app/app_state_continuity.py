from typing import Any


def get_continuity_manager(
    *, st_module: Any, continuity_manager_cls: Any
) -> Any | None:
    manager = st_module.session_state.get("continuity_manager")
    return manager if isinstance(manager, continuity_manager_cls) else None


def sync_orchestration_state_from_continuity(
    *,
    st_module: Any,
    get_continuity_manager_fn,
    get_orchestration_state_fn,
    sync_orchestration_state_from_continuity_impl_fn,
    enforce_must_remain_presence_fn,
) -> None:
    continuity_manager = get_continuity_manager_fn()
    if continuity_manager is None or continuity_manager.scene_state is None:
        return

    orchestration_state = sync_orchestration_state_from_continuity_impl_fn(
        orchestration_state=get_orchestration_state_fn(),
        continuity_manager=continuity_manager,
        enforce_must_remain_presence_fn=enforce_must_remain_presence_fn,
    )
    st_module.session_state["team_state"] = orchestration_state


def restore_or_initialize_continuity_manager(
    *,
    st_module: Any,
    continuity_state: dict[str, Any] | None,
    character_names: list[str],
    opening_description: str,
    scene_setup: dict[str, Any] | None,
    continuity_manager_cls: Any,
    build_initial_scene_issues_fn,
    apply_scene_setup_to_scene_state_fn,
    sync_orchestration_state_from_continuity_fn,
) -> Any:
    if isinstance(continuity_state, dict):
        manager = continuity_manager_cls.from_dict(continuity_state)
    else:
        manager = continuity_manager_cls()

    if manager.scene_state is None:
        manager.initialize_scene(
            location=None,
            opening_description=opening_description,
            present_characters=character_names,
            initial_issues=build_initial_scene_issues_fn(scene_setup),
        )

    if not manager.scene_state.present_characters:
        manager.scene_state.present_characters = character_names[:]
    if opening_description and not manager.scene_state.opening_description:
        manager.scene_state.opening_description = opening_description
    if scene_setup:
        apply_scene_setup_to_scene_state_fn(manager.scene_state, scene_setup)

    st_module.session_state["continuity_manager"] = manager
    sync_orchestration_state_from_continuity_fn()
    return manager

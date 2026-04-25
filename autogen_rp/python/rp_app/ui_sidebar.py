from typing import Any, Awaitable, Callable

from ui_debug import render_debug_panel
from ui_sidebar_player import render_player_controls
from ui_sidebar_scene_setup import render_scene_setup_controls
from ui_sidebar_session import (
    render_current_scene_controls,
    render_session_resume_controls,
)


def render_sidebar(
    *,
    st_module: Any,
    session_manager_cls: Any,
    get_available_characters_fn: Callable[[], list[str]],
    character_loader_cls: Any,
    has_player_character_conflict_fn: Callable[[list[str], str | None], bool],
    scene_template_manager_cls: Any,
    opener_manager_cls: Any,
    resolve_character_file_fn: Callable[[Any, str], str | None],
    start_scene_fn: Callable[[list[str]], Awaitable[bool]],
    skip_turn_fn: Callable[[], Awaitable[None]],
    end_scene_fn: Callable[[], Awaitable[None]],
) -> None:
    with st_module.sidebar:
        st_module.header("Session Management")

        render_current_scene_controls(
            st_module=st_module,
            skip_turn_fn=skip_turn_fn,
            end_scene_fn=end_scene_fn,
        )

        render_session_resume_controls(
            st_module=st_module,
            session_manager_cls=session_manager_cls,
        )

        st_module.divider()

        available = render_player_controls(
            st_module=st_module,
            get_available_characters_fn=get_available_characters_fn,
            character_loader_cls=character_loader_cls,
        )

        st_module.divider()

        render_scene_setup_controls(
            st_module=st_module,
            available=available,
            character_loader_cls=character_loader_cls,
            has_player_character_conflict_fn=has_player_character_conflict_fn,
            scene_template_manager_cls=scene_template_manager_cls,
            opener_manager_cls=opener_manager_cls,
            resolve_character_file_fn=resolve_character_file_fn,
            start_scene_fn=start_scene_fn,
        )

        st_module.divider()
        render_debug_panel(st_module=st_module)
        st_module.divider()

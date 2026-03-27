import asyncio
from typing import Any, Awaitable, Callable


def render_current_scene_controls(
    *,
    st_module: Any,
    skip_turn_fn: Callable[[], Awaitable[None]],
    end_scene_fn: Callable[[], Awaitable[None]],
) -> None:
    if not st_module.session_state.get("scene_started"):
        return

    st_module.subheader("Current Scene")

    if st_module.button(
        "⏭️ Skip Turn",
        type="secondary",
        help="Let the characters continue without your input",
    ):
        asyncio.run(skip_turn_fn())
        st_module.rerun()
    st_module.caption("Skip your turn and let the characters interact.")

    if st_module.button("⏹️ End Scene & Save", type="secondary"):
        asyncio.run(end_scene_fn())
        st_module.rerun()
    st_module.caption("Saves current state and ends the scene. You can resume later.")
    st_module.divider()


def render_session_resume_controls(*, st_module: Any, session_manager_cls: Any) -> None:
    session_manager = session_manager_cls()
    sessions = session_manager.list_sessions()

    if not sessions:
        return

    st_module.subheader("Resume Session")
    session_options = {
        f"{s['session_id']} ({', '.join(s['characters'])}) - {s['summary'][:40]}...": s[
            "session_id"
        ]
        for s in sessions[:10]
    }

    selected = st_module.selectbox(
        "Select session to load",
        options=[""] + list(session_options.keys()),
        index=0,
        key="session_select",
    )

    if selected and st_module.button("Load Session", key="load_session_btn"):
        st_module.session_state["load_session_id"] = session_options[selected]
        st_module.rerun()

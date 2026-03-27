import asyncio
from typing import Any, Awaitable, Callable


def run_app_startup(
    *,
    st_module: Any,
    session_manager_cls: Any,
    load_existing_session_fn: Callable[[str], Awaitable[None]],
) -> None:
    if not st_module.session_state.get("startup_recovery_completed", False):
        session_manager = session_manager_cls()
        st_module.session_state["recovered_session_ids"] = (
            session_manager.finalize_incomplete_sessions()
        )
        st_module.session_state["startup_recovery_completed"] = True

    if "load_session_id" in st_module.session_state:
        asyncio.run(
            load_existing_session_fn(st_module.session_state.pop("load_session_id"))
        )

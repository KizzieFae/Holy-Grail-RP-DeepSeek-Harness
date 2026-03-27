import asyncio
from typing import Any, Sequence


async def reset_agents(agents: Sequence[Any], reset_token=None) -> None:
    if reset_token is None:
        from autogen_core import CancellationToken

        reset_token = CancellationToken()

    for agent in agents:
        on_reset = getattr(agent, "on_reset", None)
        if callable(on_reset):
            try:
                result = on_reset(reset_token)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

        close_method = getattr(agent, "close", None)
        if callable(close_method):
            try:
                result = close_method()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass


async def shutdown_runtime_resources(*, st_module: Any, reset_agents_fn) -> None:
    from autogen_core import CancellationToken

    reset_token = CancellationToken()
    await reset_agents_fn(st_module.session_state.get("characters", []), reset_token)

    model_client = st_module.session_state.get("model_client")
    close_method = getattr(model_client, "close", None)
    if callable(close_method):
        try:
            result = close_method()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass

    st_module.session_state["model_client"] = None

import asyncio
from typing import Any, Awaitable, Callable


def render_chat(
    *,
    st_module: Any,
    process_user_message_fn: Callable[[str], Awaitable[None]],
    get_character_display_name_fn: Callable[[str], str],
) -> None:
    st_module.title("🎭 RP Session")

    if st_module.session_state.get("session_id"):
        chars = [c.name for c in st_module.session_state.get("characters", [])]
        st_module.caption(
            f"Session: {st_module.session_state['session_id']} | Characters: {', '.join(chars)}"
        )

    for msg in st_module.session_state.get("chat_history", []):
        if msg["role"] == "system":
            st_module.markdown(msg["content"])
        elif msg["role"] == "user":
            with st_module.chat_message("user"):
                speaker = msg.get("speaker", "You")
                st_module.markdown(f"**{speaker}**: {msg['content']}")
        else:
            with st_module.chat_message("assistant"):
                speaker = get_character_display_name_fn(
                    str(msg.get("speaker", "Character") or "Character")
                )
                st_module.markdown(f"**{speaker}**: {msg['content']}")

    if st_module.session_state.get("scene_started"):
        if prompt := st_module.chat_input("What do you say or do?"):
            asyncio.run(process_user_message_fn(prompt))
            st_module.rerun()
    elif not st_module.session_state.get("characters"):
        st_module.info(
            "👈 Select characters and start a scene from the sidebar to begin."
        )

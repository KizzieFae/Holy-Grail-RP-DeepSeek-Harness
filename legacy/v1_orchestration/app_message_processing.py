from typing import Any


async def process_user_message(
    *,
    st_module: Any,
    user_input: str,
    recreate_team_from_state_fn,
    detect_forced_speaker_fn,
    get_character_display_name_fn,
    record_user_memories_fn,
    run_character_turns_fn,
    save_current_session_fn,
) -> None:
    characters, narrator, director, _model_client = await recreate_team_from_state_fn()
    if not characters or not narrator or not director:
        st_module.error("Failed to recreate scene!")
        return

    previous_participant_speaker = next(
        (
            message.get("speaker")
            for message in reversed(st_module.session_state.get("chat_history", []))
            if message.get("role") == "assistant"
        ),
        None,
    )
    participant_names = [
        character.name for character in st_module.session_state.get("characters", [])
    ]
    st_module.session_state["pending_forced_speaker"] = detect_forced_speaker_fn(
        user_input,
        participant_names,
        previous_participant_speaker,
        resolve_display_name=get_character_display_name_fn,
    )
    st_module.session_state["forced_speaker_consumed"] = False

    user_name = st_module.session_state.get("user_name", "You")
    st_module.session_state["chat_history"].append(
        {
            "role": "user",
            "content": user_input,
            "speaker": user_name,
        }
    )
    record_user_memories_fn(user_name, user_input)

    await run_character_turns_fn(
        char_agents=characters,
        narrator=narrator,
        director=director,
        trigger_text=user_input,
        user_name=user_name,
    )

    st_module.session_state["pending_forced_speaker"] = None
    st_module.session_state["forced_speaker_consumed"] = False
    await save_current_session_fn()

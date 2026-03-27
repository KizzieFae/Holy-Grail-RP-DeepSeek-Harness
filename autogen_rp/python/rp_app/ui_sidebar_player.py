from typing import Any, Callable


def render_player_controls(
    *,
    st_module: Any,
    get_available_characters_fn: Callable[[], list[str]],
    character_loader_cls: Any,
) -> list[str]:
    st_module.subheader("Your Character")
    available = get_available_characters_fn()

    play_as_options = ["Custom (name yourself)"] + available
    stored_player_character = st_module.session_state.get("player_character")
    default_index = (
        play_as_options.index(stored_player_character)
        if isinstance(stored_player_character, str)
        and stored_player_character in play_as_options
        else 0
    )
    player_choice = st_module.selectbox(
        "Play as:",
        options=play_as_options,
        index=default_index,
        key="player_character_select",
    )

    if player_choice != "Custom (name yourself)":
        st_module.session_state["player_character"] = player_choice
        loader = character_loader_cls()
        try:
            char_card = loader.load_character_card(player_choice)
            st_module.session_state["user_name"] = char_card.get("name", player_choice)
            st_module.info(
                f"You are playing as **{char_card.get('name', player_choice)}**"
            )
        except Exception:
            st_module.session_state["user_name"] = player_choice
    else:
        st_module.session_state["player_character"] = None
        user_name = st_module.text_input(
            "Your Name",
            value=st_module.session_state.get("user_name", "Traveler"),
            key="user_name_input",
        )
        if user_name:
            st_module.session_state["user_name"] = user_name

        user_desc = st_module.text_area(
            "Your Description (optional)",
            value=st_module.session_state.get("user_description", ""),
            placeholder="A weary warrior seeking shelter...",
            height=68,
            key="user_desc_input",
        )
        if user_desc:
            st_module.session_state["user_description"] = user_desc

    return available

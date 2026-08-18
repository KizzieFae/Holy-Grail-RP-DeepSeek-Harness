def get_player_control_mode(player_character: str | None) -> str:
    return (
        "human_controlled_character"
        if player_character
        else "human_controlled_custom_persona"
    )


def has_player_character_conflict(
    selected_chars: list[str], player_character: str | None
) -> bool:
    return bool(player_character) and player_character in selected_chars


def resolve_bot_reply_limit(active_bot_count: int, configured_limit: int | None) -> int:
    if active_bot_count <= 0:
        return 0

    if configured_limit is None or configured_limit < 1:
        return active_bot_count

    return min(configured_limit, active_bot_count)

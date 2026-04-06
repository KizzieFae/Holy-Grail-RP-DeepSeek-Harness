from autogen_agentchat.messages import TextMessage


def fallback_render_move(
    char_name: str, move: dict[str, object], director_decision: dict[str, object]
) -> str:
    action = str(move.get("action", "") or "").strip().rstrip(".")
    dialogue = str(move.get("dialogue", "") or "").strip()
    environment_event = str(
        director_decision.get("environment_event", "") or ""
    ).strip()

    parts: list[str] = []
    if action:
        if action.lower().startswith(char_name.lower()):
            parts.append(f"{action}.")
        else:
            parts.append(f"{char_name} {action}.")
    if environment_event:
        suffix = "" if environment_event.endswith(".") else "."
        parts.append(environment_event[:1].upper() + environment_event[1:] + suffix)
    if dialogue:
        parts.append(f'"{dialogue}"')
    return "\n\n".join(parts).strip()


async def render_character_move(
    *,
    narrator,
    char_name: str,
    move: dict[str, object],
    scene_context: str,
    director_decision: dict[str, object],
    cancellation_token,
    build_narrator_render_prompt_fn,
    fallback_render_move_fn,
    beat_shift_narrator_suffix: str = "",
) -> tuple[str, str, str, bool]:
    action = move.get("action", "")
    dialogue = move.get("dialogue", "")
    environment_event = director_decision.get("environment_event", "")

    render_prompt = build_narrator_render_prompt_fn(
        char_name=char_name,
        action=str(action),
        dialogue=str(dialogue),
        environment_event=str(environment_event),
        scene_context=scene_context,
    )
    if beat_shift_narrator_suffix:
        render_prompt = f"{render_prompt}{beat_shift_narrator_suffix}"

    task = TextMessage(content=render_prompt, source="system")
    result = await narrator.on_messages([task], cancellation_token)
    raw_response = result.chat_message.content
    rendered = raw_response.strip()

    if dialogue and f'"{dialogue}"' not in rendered:
        fallback = fallback_render_move_fn(char_name, move, director_decision)
        return fallback, raw_response, render_prompt, True

    return rendered, raw_response, render_prompt, False

"""Narrator rendering for character turns (GitHub #139).

Renders only the **supplied** structured move view (canonical or per-recipient
projected from ``perception_audibility``). Does not decide visibility.
"""

from __future__ import annotations

from typing import Any

from autogen_agentchat.messages import TextMessage

from character_move_adapters import (
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)


def speech_dialogue_substrings_in_order(move: dict[str, Any] | None) -> list[str]:
    """Return non-empty speech ``dialogue`` strings in ``beats[]`` order (v2 only)."""
    if not is_canonical_v2_move(move) or not isinstance(move, dict):
        return []
    beats = move.get("beats")
    if not isinstance(beats, list):
        return []
    out: list[str] = []
    for b in beats:
        if not isinstance(b, dict) or b.get("type") != "speech":
            continue
        d = str(b.get("dialogue", "") or "")
        if d.strip():
            out.append(d)
    return out


def rendered_includes_ordered_speech_substrings(
    rendered: str, substrings: list[str]
) -> bool:
    """Each string must appear as a contiguous substring, in order (search from prior end)."""
    pos = 0
    for s in substrings:
        if not s:
            continue
        i = rendered.find(s, pos)
        if i < 0:
            return False
        pos = i + len(s)
    return True


def _v2_fallback_from_beats(
    char_name: str, move: dict[str, object], director_decision: dict[str, object]
) -> str:
    environment_event = str(
        director_decision.get("environment_event", "") or ""
    ).strip()
    parts: list[str] = []
    beats = move.get("beats")
    if not isinstance(beats, list):
        return ""
    for b in beats:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "action":
            action = str(b.get("action", "") or "").strip()
            if not action:
                continue
            if action.lower().startswith(char_name.lower()):
                parts.append(f"{action}.")
            else:
                parts.append(f"{char_name} {action}.")
        elif t == "speech":
            d = str(b.get("dialogue", "") or "").strip()
            if d:
                parts.append(f'"{d}"')
    if environment_event:
        suffix = "" if environment_event.endswith(".") else "."
        parts.append(environment_event[:1].upper() + environment_event[1:] + suffix)
    return "\n\n".join(parts).strip()


def fallback_render_move(
    char_name: str, move: dict[str, object], director_decision: dict[str, object]
) -> str:
    environment_event = str(
        director_decision.get("environment_event", "") or ""
    ).strip()

    if is_canonical_v2_move(move):
        return _v2_fallback_from_beats(char_name, move, director_decision)

    action = str(move.get("action", "") or "").strip().rstrip(".")
    dialogue = str(move.get("dialogue", "") or "").strip()

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
    v2 = is_canonical_v2_move(move)
    action = str(move.get("action", "") or "") if not v2 else legacy_flat_action_text(
        move  # type: ignore[arg-type]
    )
    dialogue = str(move.get("dialogue", "") or "") if not v2 else legacy_flat_dialogue_text(
        move  # type: ignore[arg-type]
    )
    environment_event = director_decision.get("environment_event", "")

    render_prompt = build_narrator_render_prompt_fn(
        char_name=char_name,
        action=str(action),
        dialogue=str(dialogue),
        environment_event=str(environment_event),
        scene_context=scene_context,
        structured_move=move if v2 else None,
    )
    if beat_shift_narrator_suffix:
        render_prompt = f"{render_prompt}{beat_shift_narrator_suffix}"

    task = TextMessage(content=render_prompt, source="system")
    result = await narrator.on_messages([task], cancellation_token)
    raw_response = result.chat_message.content
    rendered = raw_response.strip()

    if v2:
        substrings = speech_dialogue_substrings_in_order(
            move  # type: ignore[arg-type]
        )
        if substrings and not rendered_includes_ordered_speech_substrings(
            rendered, substrings
        ):
            fallback = fallback_render_move_fn(char_name, move, director_decision)
            return fallback, raw_response, render_prompt, True
    else:
        d_check = str(move.get("dialogue", "") or "").strip()
        if d_check and f'"{d_check}"' not in rendered:
            fallback = fallback_render_move_fn(char_name, move, director_decision)
            return fallback, raw_response, render_prompt, True

    return rendered, raw_response, render_prompt, False

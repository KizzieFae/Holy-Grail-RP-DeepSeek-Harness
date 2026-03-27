import re
from collections.abc import Callable
from typing import Any

from scene_exit_detection import detect_exit_from_scene


def get_must_remain_characters(scene_state: dict[str, Any] | None) -> list[str]:
    if not isinstance(scene_state, dict):
        return []
    presence_constraints = scene_state.get("character_presence_constraints", {})
    if not isinstance(presence_constraints, dict):
        return []
    return [
        str(character_name)
        for character_name, constraint in presence_constraints.items()
        if str(constraint or "") == "must_remain"
    ]


def detect_forced_speaker(
    content: str,
    participant_names: list[str],
    previous_participant_speaker: str | None,
    resolve_display_name: Callable[[str], str] | None = None,
) -> str | None:
    content_lower = content.lower()

    mentioned_names: list[tuple[int, str]] = []
    for name in participant_names:
        variants = {
            str(name).lower(),
            str(name).lower().replace("_", " "),
        }
        if resolve_display_name is not None:
            resolved_name = str(resolve_display_name(name) or "").strip().lower()
            if resolved_name:
                variants.add(resolved_name)
        for variant in sorted((item.strip() for item in variants if item.strip()), key=len, reverse=True):
            match = re.search(rf"\b{re.escape(variant)}(?:'s)?\b", content_lower)
            if match is not None:
                mentioned_names.append((match.start(), name))
                break

    if mentioned_names:
        mentioned_names.sort(key=lambda item: item[0])
        return mentioned_names[-1][1]

    if previous_participant_speaker is not None:
        if len(participant_names) == 2 and re.search(r"\b(friend|other\s+(?:woman|girl|one))\b", content_lower):
            for name in participant_names:
                if name != previous_participant_speaker:
                    return name
        return previous_participant_speaker

    return None


def detect_scene_presence_violation(
    content: str,
    speaker: str,
    move: dict[str, Any] | None = None,
    scene_state: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    if not isinstance(scene_state, dict):
        return False, ""

    must_remain = get_must_remain_characters(scene_state)
    if not must_remain:
        return False, ""

    presence_constraints = scene_state.get("character_presence_constraints", {})
    if not isinstance(presence_constraints, dict):
        return False, ""

    move_action = str((move or {}).get("action", "") or "")
    move_dialogue = str((move or {}).get("dialogue", "") or "")
    combined_text = " ".join([content, move_action, move_dialogue]).lower()

    if str(presence_constraints.get(speaker, "") or "") == "must_remain":
        if detect_exit_from_scene(move, scene_state):
            return (
                True,
                "Character with must_remain presence attempted an invalid exit under presence constraint",
            )

    for character_name in must_remain:
        if character_name == speaker:
            continue
        character_pattern = re.escape(character_name.lower())
        if re.search(
            rf"\b{character_pattern}\b.*\b(?:left|gone|away|not here|isn't here|wasn't here)\b",
            combined_text,
        ):
            return True, f"Move contradicts must_remain presence for {character_name}"
        if re.search(
            rf"\b{character_pattern}\b.*\blives?\s+alone\b",
            combined_text,
        ):
            return True, f"Move contradicts must_remain presence for {character_name}"

    return False, ""

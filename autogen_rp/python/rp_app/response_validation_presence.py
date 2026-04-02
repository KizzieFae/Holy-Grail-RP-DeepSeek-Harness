import re
from collections.abc import Callable
from typing import Any

from perception_audibility import (
    normalize_move_audibility,
    viewer_may_perceive_dialogue,
)

# must_remain: keep the character in the Director's selection pool for the scene.
# They may be offstage (hallway, another room, etc.) until the narrative brings them back;
# that is not a validation failure and does not drop them from cast obligations.

PERCEPTION_LEAK_MIN_DIALOGUE_LEN = 30
PERCEPTION_CHAT_WINDOW = 16


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


def _normalize_dialogue_for_scan(value: str) -> str:
    """Match duplicate-dialogue normalization without importing response_validation_content."""
    normalized = str(value or "")
    normalized = normalized.replace("“", '"').replace("”", '"').replace("’", "'")
    normalized = re.sub(r"\s+", " ", normalized.strip().lower())
    return normalized


def _excuse_false_absence_for_target(
    target_character: str, scene_state: dict[str, Any]
) -> bool:
    """Gating only: continuity says target may plausibly not be in the focal space."""
    off = scene_state.get("offstage_characters")
    if isinstance(off, list):
        for item in off:
            if str(item) == target_character:
                return True
    statuses = scene_state.get("character_presence_status")
    if isinstance(statuses, dict):
        raw = statuses.get(target_character)
        st = str(raw or "").strip().lower().replace("-", "_")
        if st in ("temporary_offstage", "departed"):
            return True
    return False


def _present_list_for_audibility(scene_state: dict[str, Any]) -> list[str]:
    raw = scene_state.get("present_characters")
    if not isinstance(raw, list):
        return []
    return [str(p).strip() for p in raw if str(p).strip()]


def _detect_prior_dialogue_perception_leak(
    *,
    speaker: str,
    combined_raw: str,
    scene_state: dict[str, Any],
    chat_history: list[dict[str, Any]],
) -> tuple[bool, str]:
    present = _present_list_for_audibility(scene_state)
    haystack = _normalize_dialogue_for_scan(combined_raw)
    if not haystack:
        return False, ""

    tail = chat_history[-PERCEPTION_CHAT_WINDOW:]
    for msg in reversed(tail):
        if str(msg.get("role") or "") != "assistant":
            continue
        prior_actor = str(msg.get("actor") or "").strip()
        if not prior_actor or prior_actor == speaker:
            continue
        move = msg.get("move")
        if not isinstance(move, dict):
            continue
        norm_move = normalize_move_audibility(dict(move), prior_actor, present)
        if viewer_may_perceive_dialogue(
            norm_move,
            acting_character=prior_actor,
            viewer_character=speaker,
        ):
            continue
        dialogue = str(norm_move.get("dialogue") or "").strip()
        if len(dialogue) < PERCEPTION_LEAK_MIN_DIALOGUE_LEN:
            continue
        needle = _normalize_dialogue_for_scan(dialogue)
        if len(needle) < PERCEPTION_LEAK_MIN_DIALOGUE_LEN:
            continue
        if needle in haystack:
            return (
                True,
                f"[PERCEPTION] Reused non-perceptible dialogue from {prior_actor}",
            )
    return False, ""


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
    *,
    chat_history: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    if not isinstance(scene_state, dict):
        return False, ""

    must_remain = get_must_remain_characters(scene_state)
    if not must_remain:
        return False, ""

    move_action = str((move or {}).get("action", "") or "")
    move_dialogue = str((move or {}).get("dialogue", "") or "")
    combined_raw = " ".join([content, move_action, move_dialogue])
    combined_text = combined_raw.lower()

    # Another must_remain character: only flag explicit false absence near their name,
    # not normal offstage positioning (e.g. "left the room" / "went to the hall").
    for character_name in must_remain:
        if character_name == speaker:
            continue
        character_pattern = re.escape(character_name.lower())
        false_absence_near_name = re.compile(
            rf"\b{character_pattern}\b.{{0,240}}?(?:"
            r"not\s+here(?:\s+anymore)?|isn'?t\s+here|is\s+not\s+here|"
            r"wasn'?t\s+here|was\s+not\s+here|"
            r"nowhere\s+(?:to\s+be\s+)?found|"
            r"never\s+(?:showed|arrived|came)|didn'?t\s+come"
            r")\b",
            re.DOTALL,
        )
        if false_absence_near_name.search(combined_text):
            if not _excuse_false_absence_for_target(character_name, scene_state):
                return True, f"Move contradicts must_remain presence for {character_name}"
        if re.search(
            rf"\b{character_pattern}\b.*\blives?\s+alone\b",
            combined_text,
        ):
            return True, f"Move contradicts must_remain presence for {character_name}"

    if chat_history is not None:
        has_leak, leak_reason = _detect_prior_dialogue_perception_leak(
            speaker=speaker,
            combined_raw=combined_raw,
            scene_state=scene_state,
            chat_history=chat_history,
        )
        if has_leak:
            return True, leak_reason

    return False, ""

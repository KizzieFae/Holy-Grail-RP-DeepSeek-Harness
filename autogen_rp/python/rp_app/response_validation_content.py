import re
from typing import Any

from character_state import CharacterState
from response_validation_drift import detect_character_drift
from response_validation_presence import detect_scene_presence_violation


def contains_user_speech(content: str, user_name: str) -> tuple[bool, str]:
    content_lower = content.lower()
    user_name_lower = user_name.lower()

    problematic_patterns = [
        rf"^\s*{re.escape(user_name_lower)}\s*[:\-\s]\s*['\"]",
        rf"^\s*['\"]\s*{re.escape(user_name_lower)}\s*[:\-\s]",
        rf"\b{re.escape(user_name_lower)}\s+(?:says?|said|replies?|responded|asks?|asked|exclaims?|exclaimed|mutters?|muttered)",
        rf"\b{re.escape(user_name_lower)}\s+(?:nods?|shrugs?|sighs?|laughs?|smiles?|frowns?|looks?|turns?|walks?|steps?)",
        # Only flag "you say/said" at start or after sentence boundary (user control), not mid-dialogue
        r"(?:^|[.!?]\s+|\n)\s*you\s+(?:says?|said|replies?|responded|asks?|asked)\s*(?:[:\-]|['\"])",
    ]

    for pattern in problematic_patterns:
        match = re.search(pattern, content_lower)
        if match:
            return True, f"Detected user control: '{match.group(0)}'"

    if "{{user}}" in content_lower or "{{user_name}}" in content_lower:
        return True, "Unresolved user placeholder"

    return False, ""


def _normalize_speaker_name(value: str) -> str:
    normalized = re.sub(r"[_\s]+", " ", str(value or "")).strip().lower()
    return normalized


def _normalize_dialogue_text(value: str) -> str:
    normalized = str(value or "")
    normalized = normalized.replace("“", '"').replace("”", '"').replace("’", "'")
    normalized = re.sub(r"\s+", " ", normalized.strip().lower())
    return normalized


def is_duplicate_dialogue(
    *,
    speaker: str,
    dialogue: str,
    chat_history: list[dict],
    window_size: int = 8,
) -> tuple[bool, str]:
    normalized_dialogue = _normalize_dialogue_text(dialogue)
    if len(normalized_dialogue) < 20:
        return False, ""

    speaker_normalized = _normalize_speaker_name(speaker)
    recent_messages = [
        msg for msg in chat_history[-window_size:] if msg.get("role") == "assistant"
    ]

    for msg in recent_messages:
        msg_speaker = _normalize_speaker_name(str(msg.get("speaker", "") or ""))
        if msg_speaker and msg_speaker != speaker_normalized:
            continue

        move = msg.get("move", {})
        if not isinstance(move, dict):
            continue

        prev_dialogue = _normalize_dialogue_text(str(move.get("dialogue", "") or ""))
        if not prev_dialogue:
            continue

        if normalized_dialogue == prev_dialogue:
            return True, "Exact duplicate dialogue detected"

        if len(normalized_dialogue) > 60 and len(prev_dialogue) > 60:
            if normalized_dialogue[:60] == prev_dialogue[:60]:
                return True, "Substantial dialogue overlap detected"

            if (
                normalized_dialogue in prev_dialogue
                or prev_dialogue in normalized_dialogue
            ):
                return True, "Repeated dialogue structure detected"

    return False, ""


def is_duplicate_content(
    content: str, chat_history: list[dict], window_size: int = 5
) -> tuple[bool, str]:
    normalized = re.sub(r"\s+", " ", content.strip().lower())
    if len(normalized) < 10:
        return False, ""

    recent_messages = [
        msg for msg in chat_history[-window_size:] if msg.get("role") == "assistant"
    ]

    for msg in recent_messages:
        prev_content = re.sub(r"\s+", " ", msg.get("content", "").strip().lower())

        if normalized == prev_content:
            return True, "Exact duplicate of previous message"

        if len(normalized) > 50 and len(prev_content) > 50:
            if normalized[:50] == prev_content[:50]:
                return True, "Substantial content overlap detected"

            if normalized in prev_content or prev_content in normalized:
                return True, "Repeated content structure"

    return False, ""


def validate_bot_response(
    content: str,
    speaker: str,
    user_name: str,
    chat_history: list[dict],
    state: CharacterState | None = None,
    move: dict[str, Any] | None = None,
    canon_anchors: list[Any] | None = None,
    scene_state: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    has_user_speech, user_reason = contains_user_speech(content, user_name)
    if has_user_speech:
        return False, f"[USER_SPEECH] {user_reason}"

    is_dup, dup_reason = is_duplicate_content(content, chat_history)
    if is_dup:
        return False, f"[DUPLICATE] {dup_reason}"

    dialogue = str((move or {}).get("dialogue", "") or "")
    is_dup_dialogue, dup_dialogue_reason = is_duplicate_dialogue(
        speaker=speaker,
        dialogue=dialogue,
        chat_history=chat_history,
    )
    if is_dup_dialogue:
        return False, f"[DUPLICATE] {dup_dialogue_reason}"

    has_drift, drift_reason = detect_character_drift(
        content,
        speaker,
        state,
        move,
        canon_anchors,
        scene_state=scene_state,
    )
    if has_drift:
        return False, f"[CHARACTER_DRIFT] {drift_reason}"

    has_presence_violation, presence_reason = detect_scene_presence_violation(
        content,
        speaker,
        move,
        scene_state,
    )
    if has_presence_violation:
        return False, f"[SCENE_PRESENCE] {presence_reason}"

    return True, ""

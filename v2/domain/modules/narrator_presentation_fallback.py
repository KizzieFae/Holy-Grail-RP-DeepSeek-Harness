"""Deterministic degraded Narrator presentation from committed structured moves (#29)."""

from __future__ import annotations

import re
from typing import Any, Mapping

from character_move_adapters import is_canonical_v2_move, iter_speech_beats


def _ensure_terminal_punctuation(clause: str) -> str:
    text = clause.strip()
    if not text:
        return ""
    if text[-1] not in ".!?":
        return f"{text}."
    return text


def _third_person_subject(name: str) -> str:
    return name.strip() or "They"


def _render_action_clause(character_name: str, action: str) -> str:
    text = action.strip()
    if not text:
        return ""
    subject = _third_person_subject(character_name)
    lowered = text[0].lower() + text[1:] if len(text) > 1 else text.lower()
    if re.match(r'^(he|she|they)\b', lowered, flags=re.IGNORECASE):
        return _ensure_terminal_punctuation(text[0].upper() + text[1:] if text else text)
    if lowered.startswith(character_name.lower()):
        return _ensure_terminal_punctuation(text[0].upper() + text[1:] if text else text)
    return _ensure_terminal_punctuation(f"{subject} {lowered}")


def _render_speech_clause(character_name: str, dialogue: str, *, first: bool) -> str:
    d = dialogue.strip()
    if not d:
        return ""
    subject = _third_person_subject(character_name)
    if first:
        return f'{subject} said, "{d}"'
    return f'"{d}"'


def render_degraded_player_presentation(
    structured_move: Mapping[str, Any] | None,
    *,
    character_name: str,
) -> str:
    """
    Authority-safe deterministic player-facing fallback prose.

    Preserves committed speech beats and observable action text; does not invent
    facts beyond the structured move. Public transcript path (no per-character
  perception filtering).
    """
    if not isinstance(structured_move, Mapping):
        return f"{_third_person_subject(character_name)} acted."

    if is_canonical_v2_move(structured_move):
        parts: list[str] = []
        first_speech = True
        beats = structured_move.get("beats")
        if not isinstance(beats, list):
            return f"{_third_person_subject(character_name)} acted."
        for beat in beats:
            if not isinstance(beat, dict):
                continue
            beat_type = beat.get("type")
            if beat_type == "action":
                clause = _render_action_clause(character_name, str(beat.get("action", "") or ""))
                if clause:
                    parts.append(clause)
            elif beat_type == "speech":
                clause = _render_speech_clause(
                    character_name,
                    str(beat.get("dialogue", "") or ""),
                    first=first_speech,
                )
                if clause:
                    parts.append(clause)
                    first_speech = False
        if parts:
            return " ".join(parts)
        return f"{_third_person_subject(character_name)} acted."

    # Legacy flat move shape
    action = str(structured_move.get("action", "") or "").strip()
    dialogue = ""
    for _, beat in iter_speech_beats(structured_move):
        dialogue = str(beat.get("dialogue", "") or "").strip()
        if dialogue:
            break
    parts = []
    if action:
        parts.append(_render_action_clause(character_name, action))
    if dialogue:
        parts.append(_render_speech_clause(character_name, dialogue, first=True))
    if parts:
        return " ".join(parts)
    return f"{_third_person_subject(character_name)} acted."

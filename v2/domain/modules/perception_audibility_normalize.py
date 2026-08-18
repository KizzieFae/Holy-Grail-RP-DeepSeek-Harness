"""Normalize ``audibility`` / ``audience`` on structured moves (v1 root and v2 speech beats)."""

from __future__ import annotations

import re
from typing import Any

from character_move_adapters import is_canonical_v2_move

from perception_audibility_constants import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    AUDIBILITY_PUBLIC,
    _VALID_AUDIBILITY,
)


def _clean_audience(raw: Any, acting_character: str) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        name = str(item or "").strip()
        if not name or name == acting_character or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def infer_audience_from_text(
    action: str, dialogue: str, present_characters: list[str], acting_character: str
) -> list[str]:
    """Heuristic audience for whisper / private speech (structured text only)."""
    text = f"{action} {dialogue}".lower()
    if not any(
        token in text
        for token in (
            "whisper",
            "mutter",
            "under breath",
            "quietly",
            "low voice",
            "aside",
            "private",
            "only ",
            "into ",
            "ear",
        )
    ):
        return []
    found: list[str] = []
    for name in present_characters:
        if name == acting_character:
            continue
        nlow = name.lower()
        if len(nlow) < 2:
            continue
        # "to Marlene", "toward Marlene", "into Marlene's ear"
        if re.search(
            rf"(?:\bto\b|\btoward\b|\bfor\b)\s+{re.escape(nlow)}\b", text
        ) or re.search(rf"{re.escape(nlow)}(?:'s)?\s+ear", text):
            found.append(name)
    return list(dict.fromkeys(found))


def normalize_speech_beat_audibility(
    beat: dict[str, Any],
    acting_character: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Return a copy of a ``type: speech`` beat with ``audibility`` / ``audience`` set.

    Omitted or invalid audibility → **public** with empty audience.
    """
    out = dict(beat)
    raw_aud = str(out.get("audibility", "") or "").strip().lower()
    if raw_aud not in _VALID_AUDIBILITY:
        raw_aud = ""

    audience = _clean_audience(out.get("audience"), acting_character)
    dialogue = str(out.get("dialogue", "") or "")

    if raw_aud == AUDIBILITY_PUBLIC or not raw_aud:
        out["audibility"] = AUDIBILITY_PUBLIC
        out["audience"] = []
    else:
        out["audibility"] = raw_aud
        if raw_aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE) and not audience:
            inferred = infer_audience_from_text(
                "",
                dialogue,
                present_characters,
                acting_character,
            )
            out["audience"] = inferred
        else:
            out["audience"] = audience
    return out


def normalize_move_audibility(
    move: dict[str, Any],
    acting_character: str,
    present_characters: list[str],
) -> dict[str, Any]:
    """Return a copy of ``move`` with audibility normalized (v1 root or v2 per speech beat)."""
    if is_canonical_v2_move(move):
        out = dict(move)
        beats = out.get("beats")
        if not isinstance(beats, list):
            return out
        new_beats: list[Any] = []
        for b in beats:
            if not isinstance(b, dict):
                new_beats.append(b)
                continue
            if b.get("type") == "speech":
                new_beats.append(
                    normalize_speech_beat_audibility(
                        dict(b), acting_character, present_characters
                    )
                )
            else:
                new_beats.append(dict(b))
        out["beats"] = new_beats
        return out

    out = dict(move)
    raw_aud = str(out.get("audibility", "") or "").strip().lower()
    if raw_aud not in _VALID_AUDIBILITY:
        raw_aud = ""

    audience = _clean_audience(out.get("audience"), acting_character)

    if raw_aud == AUDIBILITY_PUBLIC or not raw_aud:
        combined = (
            f"{out.get('action', '')} {out.get('dialogue', '')}".lower()
        )
        if raw_aud == "" and any(
            marker in combined
            for marker in (
                "whisper",
                "mutter",
                "under breath",
                "into ",
                " ear",
                "aside",
                "quietly to ",
            )
        ):
            inferred = infer_audience_from_text(
                str(out.get("action", "") or ""),
                str(out.get("dialogue", "") or ""),
                present_characters,
                acting_character,
            )
            out["audibility"] = (
                AUDIBILITY_DIRECTED if inferred else AUDIBILITY_PRIVATE
            )
            out["audience"] = inferred
        else:
            out["audibility"] = AUDIBILITY_PUBLIC
            out["audience"] = []
    else:
        out["audibility"] = raw_aud
        if raw_aud in (AUDIBILITY_DIRECTED, AUDIBILITY_PRIVATE) and not audience:
            inferred = infer_audience_from_text(
                str(out.get("action", "") or ""),
                str(out.get("dialogue", "") or ""),
                present_characters,
                acting_character,
            )
            out["audience"] = inferred
        else:
            out["audience"] = audience

    return out

"""Continuity-facing public events: knower sets and safe global summaries."""

from __future__ import annotations

import re
from typing import Any

from character_move_adapters import is_canonical_v2_move

from perception_audibility_constants import (
    AUDIBILITY_DIRECTED,
    AUDIBILITY_PRIVATE,
    AUDIBILITY_PUBLIC,
)
from perception_audibility_normalize import _clean_audience, normalize_move_audibility


def event_knowledge_recipients(
    move: dict[str, Any],
    *,
    acting_character: str,
    present_characters: list[str],
) -> list[str]:
    """Return canonical names who may know a continuity event tied to this move."""
    present = [str(p).strip() for p in present_characters if str(p).strip()]
    if is_canonical_v2_move(move):
        move_norm = normalize_move_audibility(dict(move), acting_character, present)
        recipients: set[str] = set()
        beats = move_norm.get("beats")
        if not isinstance(beats, list):
            return list(dict.fromkeys(present))
        for b in beats:
            if not isinstance(b, dict) or b.get("type") != "speech":
                continue
            aud = str(b.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
            if aud == AUDIBILITY_PUBLIC:
                recipients.update(present)
            else:
                recipients.add(acting_character)
                recipients.update(
                    _clean_audience(b.get("audience"), acting_character)
                )
        if not recipients:
            return list(dict.fromkeys(present))
        out = [n for n in recipients if n in present or n == acting_character]
        return list(dict.fromkeys(out))

    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    if aud == AUDIBILITY_PUBLIC:
        return list(dict.fromkeys(present))
    audience = _clean_audience(move.get("audience"), acting_character)
    core = [acting_character] + audience
    return list(dict.fromkeys([n for n in core if n in present or n == acting_character]))


def strip_dialogue_from_summary(summary: str, dialogue: str) -> str:
    """Remove verbatim dialogue from a summary string when dialogue must stay private."""
    d = str(dialogue or "").strip()
    if not d:
        return summary
    s = str(summary or "")
    if d in s:
        return s.replace(d, "").replace('""', "").replace("''", "").strip(" ;:")
    low = d.lower()
    if low and low in s.lower():
        pattern = re.compile(re.escape(d), re.IGNORECASE)
        return pattern.sub("", s).strip(" ;:")
    return s


def public_safe_event_summary(
    *,
    acting_character: str,
    move: dict[str, Any],
    provisional_summary: str,
) -> str:
    """PublicEventExtraction: ensure ``PublicEvent.summary`` never embeds private/directed verbatim dialogue.

    Canonical turn facts + provisional narrative pass through this layer before global public-event prose.
    Issue #140: not a raw copy of structured move text into ``summary``.
    """
    if is_canonical_v2_move(move):
        # Callers (e.g. continuity) normalize moves with full ``present_characters``
        # before summary; do not re-normalize here with an incomplete roster.
        base = str(provisional_summary or "")
        beats = move.get("beats")
        has_non_public_speech = False
        if isinstance(beats, list):
            for b in beats:
                if not isinstance(b, dict) or b.get("type") != "speech":
                    continue
                aud = str(
                    b.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC
                ).lower()
                if aud == AUDIBILITY_PUBLIC:
                    continue
                has_non_public_speech = True
                dialogue = str(b.get("dialogue", "") or "").strip()
                base = strip_dialogue_from_summary(base, dialogue)
        if base.strip():
            return base.strip()
        if has_non_public_speech:
            return (
                f"{acting_character} spoke (non-public speech; words not globally knowable in summary)."
            )
        return f"{acting_character} took action"

    aud = str(move.get("audibility", AUDIBILITY_PUBLIC) or AUDIBILITY_PUBLIC).lower()
    dialogue = str(move.get("dialogue", "") or "").strip()
    action = str(move.get("action", "") or "").strip()
    if aud == AUDIBILITY_PUBLIC:
        return provisional_summary
    base = strip_dialogue_from_summary(provisional_summary, dialogue)
    if dialogue and dialogue.lower() in base.lower():
        base = strip_dialogue_from_summary(base, dialogue)
    if base.strip():
        return base.strip()
    audience = _clean_audience(move.get("audience"), acting_character)
    if aud == AUDIBILITY_DIRECTED and audience:
        names = ", ".join(audience)
        return f"{acting_character} addressed {names} in a low or private voice (words not globally knowable)."
    if aud == AUDIBILITY_PRIVATE:
        return f"{acting_character} spoke privately (words not globally knowable)."
    return f"{acting_character} {action}".strip() or f"{acting_character} took action"


# Explicit name for continuity / governance (Issue #140); same implementation as ``public_safe_event_summary``.
public_event_extraction = public_safe_event_summary

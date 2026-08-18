"""Token helpers for issue pressure matching (moves, events, text)."""

from __future__ import annotations

import re
from typing import Any

from continuity_state import PublicEvent


def issue_tokens(*, text: str, stopwords: set[str]) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= 4 and token not in stopwords
    }


def turn_tokens(*, move: dict[str, Any], issue_tokens_fn) -> set[str]:
    from character_move_adapters import (
        is_canonical_v2_move,
        legacy_flat_action_text,
        legacy_flat_dialogue_text,
    )

    motivation = move.get("motivation", {}) if isinstance(move, dict) else {}
    if not isinstance(motivation, dict):
        motivation = {}
    if is_canonical_v2_move(move):
        a = legacy_flat_action_text(move)
        d = legacy_flat_dialogue_text(move)
    else:
        a = str(move.get("action", "") or "")
        d = str(move.get("dialogue", "") or "")
    text = " ".join(
        [
            a,
            d,
            str(motivation.get("goal", "") or ""),
            str(motivation.get("tactic", "") or ""),
        ]
    )
    return issue_tokens_fn(text)


def event_tokens(*, event: PublicEvent, issue_tokens_fn) -> set[str]:
    return issue_tokens_fn(event.summary)

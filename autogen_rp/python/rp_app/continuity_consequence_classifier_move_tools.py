"""V2 flat text helper for exit/grounding/classifier tools (Issue #159)."""

from typing import Any

from character_move_adapters import (
    is_canonical_v2_move,
    legacy_flat_action_text,
    legacy_flat_dialogue_text,
)


def move_with_flat_text_for_deterministic_tools(move: dict[str, Any]) -> dict[str, Any]:
    """Augment v2 moves with root ``action``/``dialogue`` for exit/grounding helpers (canonical text, Issue #140)."""
    if not is_canonical_v2_move(move):
        return move
    out = dict(move)
    out["action"] = legacy_flat_action_text(move)
    out["dialogue"] = legacy_flat_dialogue_text(move)
    return out

"""Character turn: `state_context` string for `prompt_builders.build_character_turn_prompt`."""

from __future__ import annotations

from typing import Any

from memory_layer.retrieval import build_character_state_context_for_prompt


def build_state_context_for_character_prompt(
    *,
    state: Any | None,
    relationship_focus_names: list[str],
    relationship_secondary_names: list[str],
) -> str:
    """Build the single `state_context` string (memory_layer + identity); passed unchanged downstream."""
    if not state:
        return "No private state available."
    return build_character_state_context_for_prompt(
        state=state,
        relationship_focus_names=relationship_focus_names,
        relationship_secondary_names=relationship_secondary_names,
    )

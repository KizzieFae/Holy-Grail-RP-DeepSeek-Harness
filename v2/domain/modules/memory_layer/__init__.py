"""Scene memory layer: episodic writes (Phase A); read/format for prompts (Phase B)."""

from memory_layer.facade import (
    commit_character_turn_memory,
    commit_user_message_memory,
    resolve_present_characters,
)
from memory_layer.retrieval import (
    EpisodicPromptSnapshot,
    build_character_state_context_for_prompt,
    build_episodic_prompt_snapshot,
    format_episodic_prompt_sections,
)

__all__ = [
    "EpisodicPromptSnapshot",
    "build_character_state_context_for_prompt",
    "build_episodic_prompt_snapshot",
    "commit_character_turn_memory",
    "commit_user_message_memory",
    "format_episodic_prompt_sections",
    "resolve_present_characters",
]

"""Character turn: scene grounding + binding constraint sections (read-only projection)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from scene_grounding import (
    format_character_binding_constraints_section,
    format_character_grounding_section,
)


def build_scene_grounding_sections_for_character_prompt(
    *, session_state: Mapping[str, Any]
) -> tuple[str, str]:
    _sg = session_state.get("scene_grounding")
    grounding_section = format_character_grounding_section(_sg)
    binding_constraints_section = format_character_binding_constraints_section(_sg)
    return grounding_section, binding_constraints_section

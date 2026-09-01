"""Project Character committed history entries for Character-facing consumers (#92)."""

from __future__ import annotations

from typing import Any

from perceptual_visibility_projection import (
    PerceptualVisibilityAssemblyResult,
    assemble_perceptual_history_entry_for_viewer,
)


def assemble_character_committed_entry_for_viewer(
    entry: dict[str, Any],
    *,
    viewer_character: str,
    present_characters: list[str],
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
) -> PerceptualVisibilityAssemblyResult:
    return assemble_perceptual_history_entry_for_viewer(
        entry,
        viewer_character=viewer_character,
        present_characters=present_characters,
        structured_move=structured_move,
        acting_character=acting_character,
        source_kind="character",
    )

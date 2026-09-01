"""Project player user history entries for Character-facing consumers (#91)."""

from __future__ import annotations

from typing import Any

from perceptual_visibility_projection import (
    PerceptualVisibilityAssemblyResult,
    assemble_perceptual_history_entry_for_viewer,
)


def assemble_player_user_entry_for_viewer(
    entry: dict[str, Any],
    *,
    viewer_character: str,
    present_characters: list[str],
) -> PerceptualVisibilityAssemblyResult:
    return assemble_perceptual_history_entry_for_viewer(
        entry,
        viewer_character=viewer_character,
        present_characters=present_characters,
        source_kind="player",
    )

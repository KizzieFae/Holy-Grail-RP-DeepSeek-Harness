"""Shared viewer-specific Player perception assembly (#155)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from perceptual_scene_context import (  # noqa: E402
    PerceptualSceneContextV1,
    perceptual_scene_context_from_scene_state,
)
from perceptual_visibility_projection import (  # noqa: E402
    PerceptualVisibilityAssemblyResult,
    assemble_perceptual_history_entry_for_viewer,
)
from player_perceptual_projection import assemble_player_user_entry_for_viewer  # noqa: E402

from .player_identity import player_character_file_id  # noqa: E402
from .session_state import LiveSession  # noqa: E402


def resolve_player_character_name(fixture: LiveSession) -> str | None:
    """Resolve the cast display name controlled by the human player."""
    file_id = player_character_file_id(fixture.setup_snapshot)
    if not file_id:
        for name, mode in (fixture.setup_snapshot.get("control_modes") or {}).items():
            if str(mode) == "player":
                return str(name)
        return None
    names_by_file = fixture.setup_snapshot.get("character_file_ids") or {}
    if isinstance(names_by_file, dict):
        mapped = names_by_file.get(file_id)
        if mapped:
            return str(mapped)
    for name in fixture.cast:
        if name.lower() == str(file_id).lower():
            return name
    return str(file_id)


def resolve_perceptual_scene_context(fixture: LiveSession) -> PerceptualSceneContextV1 | None:
    manager = fixture.manager
    scene_state = getattr(manager, "scene_state", None) if manager is not None else None
    return perceptual_scene_context_from_scene_state(scene_state)


def assemble_viewer_player_perception(
    user_entry: dict[str, Any],
    *,
    viewer_character: str,
    present_characters: list[str],
    perceptual_scene_context: PerceptualSceneContextV1 | None = None,
    player_character: str | None = None,
) -> PerceptualVisibilityAssemblyResult:
    """Single source of truth for entitled Player units projected to one viewer."""
    return assemble_player_user_entry_for_viewer(
        user_entry,
        viewer_character=viewer_character,
        present_characters=present_characters,
        perceptual_scene_context=perceptual_scene_context,
        player_character=player_character,
    )


def assemble_viewer_player_history_entry(
    entry: dict[str, Any],
    *,
    viewer_character: str,
    present_characters: list[str],
    source_kind: str,
    perceptual_scene_context: PerceptualSceneContextV1 | None = None,
    player_character: str | None = None,
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
) -> PerceptualVisibilityAssemblyResult:
    return assemble_perceptual_history_entry_for_viewer(
        entry,
        viewer_character=viewer_character,
        present_characters=present_characters,
        source_kind=source_kind,
        perceptual_scene_context=perceptual_scene_context,
        player_character=player_character,
        structured_move=structured_move,
        acting_character=acting_character,
    )


def assemble_viewer_player_perception_for_session(
    fixture: LiveSession,
    user_entry: dict[str, Any],
    *,
    viewer_character: str,
    present_characters: list[str],
) -> PerceptualVisibilityAssemblyResult:
    return assemble_viewer_player_perception(
        user_entry,
        viewer_character=viewer_character,
        present_characters=present_characters,
        perceptual_scene_context=resolve_perceptual_scene_context(fixture),
        player_character=resolve_player_character_name(fixture),
    )

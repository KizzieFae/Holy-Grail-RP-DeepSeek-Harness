"""Issue #77 — shared continuity-backed scene projection for prompt assembly.

Single canonical snapshot per build; read-only projection (no new authority).

See GitHub #77: Director parity, focal context as pure function of continuity at boundary *B*.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ContinuityPromptProjectionV77:
    """Scene-facing slice derived from continuity for Director and character prompts."""

    scene_state_dict: dict[str, Any]
    """``SceneState.to_dict()`` when ``continuity_manager`` is present; else orchestration fallback."""
    continuity_turn_index: int
    """``ContinuityManager.turn_counter`` when manager is present, else ``0``."""


def build_continuity_prompt_projection_v77(
    continuity_manager: Optional[Any],
    *,
    orchestration_scene_state_fallback: Optional[dict[str, Any]] = None,
) -> ContinuityPromptProjectionV77:
    """Build one projection from continuity (one ``get_snapshot``) or orchestration fallback.

    When ``continuity_manager`` is ``None``, returns ``orchestration_scene_state_fallback``
    (or empty dict) for ``scene_state_dict`` — same non-authoritative fallback as legacy paths.
    """
    fallback = dict(orchestration_scene_state_fallback or {})
    if continuity_manager is None:
        return ContinuityPromptProjectionV77(
            scene_state_dict=fallback,
            continuity_turn_index=0,
        )
    snapshot = continuity_manager.get_snapshot()
    return ContinuityPromptProjectionV77(
        scene_state_dict=snapshot.scene_state.to_dict(),
        continuity_turn_index=int(
            getattr(continuity_manager, "turn_counter", 0) or 0
        ),
    )

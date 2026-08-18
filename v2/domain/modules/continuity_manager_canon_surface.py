"""Canon anchor surface for ContinuityManager (mechanical extraction)."""

from __future__ import annotations

from typing import Any, Optional

from continuity_canon_anchors import (
    get_relevant_canon_anchors as get_relevant_canon_anchors_impl,
    get_scene_canon_anchors as get_scene_canon_anchors_impl,
    seed_character_canon_anchors as seed_character_canon_anchors_impl,
    upsert_canon_anchor as upsert_canon_anchor_impl,
)

from continuity_state import CanonAnchor


def upsert_canon_anchor(manager: Any, anchor: CanonAnchor) -> None:
    upsert_canon_anchor_impl(manager, anchor)


def seed_character_canon_anchors(
    manager: Any, character_states: dict[str, Any]
) -> None:
    seed_character_canon_anchors_impl(manager, character_states)


def get_relevant_canon_anchors(
    manager: Any,
    character_name: str,
    participants: Optional[list[str]] = None,
    limit: int = 6,
) -> list[CanonAnchor]:
    return get_relevant_canon_anchors_impl(
        manager, character_name, participants=participants, limit=limit
    )


def get_scene_canon_anchors(manager: Any, limit: int = 10) -> list[CanonAnchor]:
    return get_scene_canon_anchors_impl(manager, limit)

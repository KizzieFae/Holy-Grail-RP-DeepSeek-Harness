"""Canon anchor helpers for ContinuityManager (Issue #155 Slice B)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from continuity_state import CanonAnchor


def upsert_canon_anchor(manager: Any, anchor: CanonAnchor) -> None:
    """Insert or replace a canon anchor by ID."""
    for index, existing in enumerate(manager.canon_anchors):
        if existing.anchor_id == anchor.anchor_id:
            manager.canon_anchors[index] = anchor
            return
    manager.canon_anchors.append(anchor)


def seed_character_canon_anchors(
    manager: Any, character_states: dict[str, Any]
) -> None:
    """Seed protected canon anchors from current character state data."""
    timestamp = datetime.now(timezone.utc)
    for name, state in character_states.items():
        core_goals = list(getattr(state, "core_goals", []) or [])
        long_term_goal = str(getattr(state, "long_term_goal", "") or "").strip()
        if not core_goals and long_term_goal:
            core_goals = [long_term_goal]
        if core_goals:
            upsert_canon_anchor(
                manager,
                CanonAnchor(
                    anchor_id=f"canon_{name.lower()}_goals",
                    category="character_trait",
                    subject=name,
                    statement=f"{name} consistently pursues: {', '.join(core_goals)}.",
                    source="character_state.core_goals",
                    established_at=timestamp,
                ),
            )

        voice_profile = getattr(state, "voice_profile", {}) or {}
        speech_fingerprint = getattr(state, "speech_fingerprint", {}) or {}
        voice_parts: list[str] = []
        if voice_profile:
            voice_parts.append(
                "voice profile: "
                + ", ".join(f"{key}={value}" for key, value in voice_profile.items())
            )
        if speech_fingerprint:
            voice_parts.append(
                "speech fingerprint: "
                + ", ".join(
                    f"{key}={value}" for key, value in speech_fingerprint.items()
                )
            )
        if voice_parts:
            upsert_canon_anchor(
                manager,
                CanonAnchor(
                    anchor_id=f"canon_{name.lower()}_voice",
                    category="character_voice",
                    subject=name,
                    statement=f"{name}'s expression remains distinct: {'; '.join(voice_parts)}.",
                    source="character_state.voice_profile",
                    established_at=timestamp,
                ),
            )

        reaction_profile = getattr(state, "reaction_profile", {}) or {}
        if reaction_profile:
            upsert_canon_anchor(
                manager,
                CanonAnchor(
                    anchor_id=f"canon_{name.lower()}_reaction",
                    category="character_trait",
                    subject=name,
                    statement=(
                        f"{name} tends to react in consistent ways: "
                        + ", ".join(
                            f"{key}={value}" for key, value in reaction_profile.items()
                        )
                        + "."
                    ),
                    source="character_state.reaction_profile",
                    established_at=timestamp,
                ),
            )


def get_relevant_canon_anchors(
    manager: Any,
    character_name: str,
    participants: Optional[list[str]] = None,
    limit: int = 6,
) -> list[CanonAnchor]:
    """Return canon anchors most relevant to the named character in this scene."""
    participant_set = set(
        participants
        or (
            manager.scene_state.present_characters
            if manager.scene_state
            else []
        )
    )
    relevant: list[CanonAnchor] = []
    for anchor in manager.canon_anchors:
        if anchor.subject == character_name:
            relevant.append(anchor)
            continue
        if anchor.category == "world_fact":
            relevant.append(anchor)
            continue
        if (
            participant_set
            and anchor.subject in participant_set
            and anchor.category == "relationship"
        ):
            relevant.append(anchor)
    return relevant[:limit]


def get_scene_canon_anchors(manager: Any, limit: int = 10) -> list[CanonAnchor]:
    """Return canon anchors broadly relevant to the current scene."""
    participants = set(
        manager.scene_state.present_characters if manager.scene_state else []
    )
    anchors = [
        anchor
        for anchor in manager.canon_anchors
        if anchor.subject in participants or anchor.category == "world_fact"
    ]
    return anchors[:limit]

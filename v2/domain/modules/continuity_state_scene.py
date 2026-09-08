"""Scene phase and shared scene payload (+ presence migration)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ScenePhase(Enum):
    """Phases of scene progression."""

    OPENING = "opening"
    RISING = "rising"
    CLIMAX = "climax"
    FALLING = "falling"
    RESOLUTION = "resolution"


def _migrate_character_presence_status(
    raw: Optional[Any],
    offstage_characters: Optional[list],
    present_characters: Optional[list] = None,
) -> dict[str, str]:
    """Load presence status; default legacy offstage rows to temporary_offstage."""
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            k = str(key or "").strip()
            v = str(value or "").strip()
            if k and v in ("onstage", "temporary_offstage", "departed"):
                out[k] = v
    legacy_off = offstage_characters if isinstance(offstage_characters, list) else []
    for item in legacy_off:
        name = str(item or "").strip()
        if name and name not in out:
            out[name] = "temporary_offstage"
    present = present_characters if isinstance(present_characters, list) else []
    for item in present:
        name = str(item or "").strip()
        if name and name not in out:
            out[name] = "onstage"
    return out


def _scene_anchor_role_name_from_dict(data: dict) -> Optional[str]:
    raw = data.get("anchor_role_name")
    if raw is None or not str(raw or "").strip():
        return None
    return str(raw).strip()


@dataclass
class SceneState:
    """The current state of the scene including setting, participants, and active pressures.

    Scene state is shared context that all characters can observe,
    distinct from their private interpretations.
    """

    # Setting
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    environment_description: Optional[str] = None
    scene_template_id: Optional[str] = None
    scene_premise: str = ""
    anchor_role_name: Optional[str] = None
    role_assignments: dict[str, str] = field(default_factory=dict)
    character_presence_constraints: dict[str, str] = field(default_factory=dict)
    character_authority_labels: dict[str, str] = field(default_factory=dict)
    sleeping_surface_slots: list[str] = field(default_factory=list)
    location_entry_slots: list[str] = field(default_factory=list)

    # Participants
    present_characters: list[str] = field(default_factory=list)
    absent_but_relevant: list[str] = field(default_factory=list)
    # Still in cast / present_characters but not in the immediate shared space (hallway, garage, etc.)
    offstage_characters: list[str] = field(default_factory=list)
    # Annotation only: refines offstage / presence meaning. Keys are character ids.
    # Values: onstage | temporary_offstage | departed
    character_presence_status: dict[str, str] = field(default_factory=dict)

    # Scene progression
    phase: ScenePhase = field(default=ScenePhase.OPENING)
    opening_description: str = ""
    recent_delta: str = ""  # what just changed in the scene

    # Active state references (IDs into continuity stores)
    active_issue_ids: list[str] = field(default_factory=list)
    recent_event_ids: list[str] = field(default_factory=list)

    # Environment tracking
    current_tension_level: str = "low"  # 'low', 'moderate', 'high', 'extreme'
    recent_environment_events: list[str] = field(default_factory=list)

    # Optional authoritative spatial/perceptual substrate (#155)
    perceptual_scene_context: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        """Serialize the scene state for persistence."""
        payload = {
            "location": self.location,
            "time_of_day": self.time_of_day,
            "environment_description": self.environment_description,
            "scene_template_id": self.scene_template_id,
            "scene_premise": self.scene_premise,
            "anchor_role_name": self.anchor_role_name,
            "role_assignments": self.role_assignments,
            "character_presence_constraints": self.character_presence_constraints,
            "character_authority_labels": self.character_authority_labels,
            "sleeping_surface_slots": self.sleeping_surface_slots,
            "location_entry_slots": self.location_entry_slots,
            "present_characters": self.present_characters,
            "absent_but_relevant": self.absent_but_relevant,
            "offstage_characters": self.offstage_characters,
            "character_presence_status": dict(self.character_presence_status),
            "phase": self.phase.value,
            "opening_description": self.opening_description,
            "recent_delta": self.recent_delta,
            "active_issue_ids": self.active_issue_ids,
            "recent_event_ids": self.recent_event_ids,
            "current_tension_level": self.current_tension_level,
            "recent_environment_events": self.recent_environment_events,
        }
        if isinstance(self.perceptual_scene_context, dict) and self.perceptual_scene_context:
            payload["perceptual_scene_context"] = dict(self.perceptual_scene_context)
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> "SceneState":
        """Restore scene state from persisted data."""
        return cls(
            location=(str(data.get("location")) if data.get("location") else None),
            time_of_day=(
                str(data.get("time_of_day")) if data.get("time_of_day") else None
            ),
            environment_description=(
                str(data.get("environment_description"))
                if data.get("environment_description")
                else None
            ),
            scene_template_id=(
                str(data.get("scene_template_id"))
                if data.get("scene_template_id")
                else None
            ),
            scene_premise=str(data.get("scene_premise", "") or ""),
            anchor_role_name=_scene_anchor_role_name_from_dict(data),
            role_assignments=(
                {
                    str(key): str(value)
                    for key, value in data.get("role_assignments", {}).items()
                }
                if isinstance(data.get("role_assignments", {}), dict)
                else {}
            ),
            character_presence_constraints=(
                {
                    str(key): str(value)
                    for key, value in data.get(
                        "character_presence_constraints", {}
                    ).items()
                }
                if isinstance(data.get("character_presence_constraints", {}), dict)
                else {}
            ),
            character_authority_labels=(
                {
                    str(key): str(value)
                    for key, value in data.get("character_authority_labels", {}).items()
                }
                if isinstance(data.get("character_authority_labels", {}), dict)
                else {}
            ),
            sleeping_surface_slots=[
                str(item) for item in data.get("sleeping_surface_slots", []) if str(item or "").strip()
            ],
            location_entry_slots=[
                str(item)
                for item in data.get("location_entry_slots", [])
                if str(item or "").strip()
            ],
            present_characters=[
                str(item) for item in data.get("present_characters", [])
            ],
            absent_but_relevant=[
                str(item) for item in data.get("absent_but_relevant", [])
            ],
            offstage_characters=[
                str(item) for item in data.get("offstage_characters", [])
            ],
            character_presence_status=_migrate_character_presence_status(
                data.get("character_presence_status"),
                data.get("offstage_characters", []),
                data.get("present_characters", []),
            ),
            phase=ScenePhase(str(data.get("phase", ScenePhase.OPENING.value))),
            opening_description=str(data.get("opening_description", "")),
            recent_delta=str(data.get("recent_delta", "")),
            active_issue_ids=[str(item) for item in data.get("active_issue_ids", [])],
            recent_event_ids=[str(item) for item in data.get("recent_event_ids", [])],
            current_tension_level=str(data.get("current_tension_level", "low")),
            recent_environment_events=[
                str(item) for item in data.get("recent_environment_events", [])
            ],
            perceptual_scene_context=(
                dict(data.get("perceptual_scene_context"))
                if isinstance(data.get("perceptual_scene_context"), dict)
                else None
            ),
        )


def create_fresh_scene_state(
    location: Optional[str] = None,
    opening_description: str = "",
    present_characters: Optional[list[str]] = None,
) -> SceneState:
    """Create initial scene state for a new scene."""
    return SceneState(
        location=location,
        opening_description=opening_description,
        present_characters=present_characters or [],
        phase=ScenePhase.OPENING,
        current_tension_level="low",
    )

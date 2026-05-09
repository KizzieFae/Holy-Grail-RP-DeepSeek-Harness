"""Orchestration default state and ensure/initialize (Issue #164)."""

from typing import Any

from beat_shift_state import default_pending_beat_shift, ensure_beat_shift_fields


def build_default_orchestration_state() -> dict[str, Any]:
    return {
        "scene_state": {
            "opening_description": "",
            "present_characters": [],
            "scene_phase": "",
            "current_tension_level": "",
            "recent_delta": "",
            "recent_environment_events": [],
            "tension_history": [],
            "resolved_events": [],
            "location": "",
            "time_of_day": "",
            "environment_description": "",
            "scene_template_id": "",
            "scene_premise": "",
            "role_assignments": {},
            "character_presence_constraints": {},
            "character_authority_labels": {},
            "location_entry_slots": [],
            "offstage_characters": [],
        },
        "spotlight_history": [],
        "recent_structured_moves": [],
        "director_decisions": [],
        "pending_beat_shift": default_pending_beat_shift(),
        "beat_shift_scene_snapshots": [],
    }


def ensure_orchestration_state(team_state: dict[str, Any] | None) -> dict[str, Any]:
    state = (
        team_state
        if isinstance(team_state, dict)
        else build_default_orchestration_state()
    )
    state.setdefault("spotlight_history", [])
    state.setdefault("recent_structured_moves", [])
    state.setdefault("director_decisions", [])
    state.setdefault("scene_state", build_default_orchestration_state()["scene_state"])
    ensure_beat_shift_fields(state)
    return state

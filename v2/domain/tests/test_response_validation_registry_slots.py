"""Registry-slot structured validation (no narrative checks)."""

import sys
from pathlib import Path


from response_validation_registry_slots import validate_registry_scene_state_updates


def test_accepts_empty_scene_state_updates() -> None:
    ok, msg = validate_registry_scene_state_updates(
        {"action": "x", "dialogue": ""},
        scene_state={},
        _continuity_manager=None,
    )
    assert ok and msg == ""


def test_rejects_invalid_sleeping_surface_id() -> None:
    move = {
        "scene_state_updates": {
            "sleeping_surface_assignment": {
                "assignee_id": "willow",
                "surface_id": "not_a_real_slot",
            }
        }
    }
    scene_state = {"sleeping_surface_slots": ["bed_a"]}
    ok, msg = validate_registry_scene_state_updates(
        move, scene_state=scene_state, _continuity_manager=None
    )
    assert ok is False
    assert "[REGISTRY_SLOT]" in msg
    assert "invalid_surface_id" in msg


def test_rejects_invalid_housing_call_status() -> None:
    move = {
        "scene_state_updates": {
            "housing_call_outcome": {"status": "dialing"},
        }
    }
    ok, msg = validate_registry_scene_state_updates(
        move, scene_state={}, _continuity_manager=None
    )
    assert ok is False
    assert "invalid_status" in msg

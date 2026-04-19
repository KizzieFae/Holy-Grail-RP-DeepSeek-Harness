"""Issue #77 — shared continuity prompt projection (Director / character parity)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_prompt_projection_v77 import (
    ContinuityPromptProjectionV77,
    build_continuity_prompt_projection_v77,
)


def test_projection_none_manager_uses_fallback() -> None:
    fb = {"location": "Hall", "tension_history": ["orch_only"]}
    p = build_continuity_prompt_projection_v77(
        None, orchestration_scene_state_fallback=fb
    )
    assert p.scene_state_dict == fb
    assert p.continuity_turn_index == 0


def test_projection_calls_get_snapshot_once_and_prefers_continuity_scene_fields() -> None:
    """Director must not mix orchestration mirror for tension_history when CM exists."""

    class _Scene:
        def to_dict(self) -> dict:
            return {
                "location": "ContinuityRoom",
                "tension_history": ["from_continuity"],
                "resolved_events": [{"id": "r1"}],
                "recent_environment_events": ["e1"],
                "opening_description": "od",
                "phase": "p",
                "current_tension_level": "low",
                "recent_delta": "",
                "present_characters": ["A"],
                "offstage_characters": [],
            }

    class _Snap:
        scene_state = _Scene()

    cm = MagicMock()
    cm.get_snapshot.return_value = _Snap()
    cm.turn_counter = 7

    orch = {
        "tension_history": ["stale_orchestration"],
        "resolved_events": [],
    }

    p = build_continuity_prompt_projection_v77(
        cm, orchestration_scene_state_fallback=orch
    )

    assert p.continuity_turn_index == 7
    assert p.scene_state_dict["tension_history"] == ["from_continuity"]
    assert p.scene_state_dict["resolved_events"] == [{"id": "r1"}]
    cm.get_snapshot.assert_called_once()


def test_projection_dataclass_frozen() -> None:
    p = ContinuityPromptProjectionV77(scene_state_dict={}, continuity_turn_index=0)
    try:
        p.continuity_turn_index = 1  # type: ignore[misc]
        raise AssertionError("expected frozen dataclass")
    except AttributeError:
        pass

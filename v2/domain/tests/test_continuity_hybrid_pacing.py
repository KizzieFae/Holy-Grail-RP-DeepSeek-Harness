"""ContinuityManager hybrid tension pacing integration tests."""

import sys
from pathlib import Path
from unittest.mock import patch


from continuity_manager import ContinuityManager
from continuity_state import ScenePhase


def _minimal_turn_consequences() -> dict:
    return {
        "tags": [],
        "state_changes": [],
        "should_create_event": False,
    }


def test_update_scene_state_director_escalate_one_step() -> None:
    m = ContinuityManager()
    m.initialize_scene(
        location="X",
        opening_description="Test",
        present_characters=["A"],
    )
    assert m.scene_state
    m.scene_state.current_tension_level = "low"
    tc = _minimal_turn_consequences()
    m._update_scene_state(
        "A",
        {"action": "acts", "dialogue": "", "motivation": {}},
        {"tension_shift": "escalate", "environment_event": ""},
        None,
        tc,
    )
    assert m.scene_state.current_tension_level == "moderate"
    assert tc["hybrid_pacing"]["pacing_source"] == "director"
    assert tc["hybrid_pacing"]["pacing_direction"] == "up"
    assert tc["hybrid_pacing"]["director_neutral"] is False


def test_update_scene_state_boundary_extreme_no_op_on_escalate() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "extreme"
    tc = _minimal_turn_consequences()
    m._update_scene_state(
        "A",
        {"action": "acts", "dialogue": "", "motivation": {}},
        {"tension_shift": "escalate", "environment_event": ""},
        None,
        tc,
    )
    assert m.scene_state.current_tension_level == "extreme"


def test_update_scene_state_boundary_low_no_op_on_soften() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "low"
    tc = _minimal_turn_consequences()
    m._update_scene_state(
        "A",
        {"action": "acts", "dialogue": "", "motivation": {}},
        {"tension_shift": "soften", "environment_event": ""},
        None,
        tc,
    )
    assert m.scene_state.current_tension_level == "low"
    assert tc["hybrid_pacing"]["pacing_direction"] == "down"


def test_update_scene_state_neutral_consequence_down_stubbed() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "high"
    m.scene_state.phase = ScenePhase.CLIMAX
    tc = _minimal_turn_consequences()
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="down",
    ):
        m._update_scene_state(
            "A",
            {"action": "acts", "dialogue": "", "motivation": {}},
            {"tension_shift": "steady", "environment_event": ""},
            None,
            tc,
        )
    assert m.scene_state.current_tension_level == "moderate"
    assert tc["hybrid_pacing"]["pacing_source"] == "consequence"
    assert tc["hybrid_pacing"]["pacing_direction"] == "down"
    assert tc["hybrid_pacing"]["director_neutral"] is True


def test_phase_derived_climax_to_falling_after_consequence_down() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "extreme"
    m.scene_state.phase = ScenePhase.CLIMAX
    tc = _minimal_turn_consequences()
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="down",
    ):
        m._update_scene_state(
            "A",
            {"action": "acts", "dialogue": "", "motivation": {}},
            {"tension_shift": ""},
            None,
            tc,
        )
    assert m.scene_state.current_tension_level == "high"
    assert m.scene_state.phase == ScenePhase.CLIMAX

    tc2 = _minimal_turn_consequences()
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="down",
    ):
        m._update_scene_state(
            "A",
            {"action": "acts", "dialogue": "", "motivation": {}},
            {"tension_shift": ""},
            None,
            tc2,
        )
    assert m.scene_state.current_tension_level == "moderate"
    assert m.scene_state.phase == ScenePhase.FALLING


def test_update_scene_state_consequence_up_at_high_applies_normally() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "high"
    tc = _minimal_turn_consequences()
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="up",
    ):
        m._update_scene_state(
            "A",
            {"action": "acts", "dialogue": "", "motivation": {}},
            {"tension_shift": "", "environment_event": ""},
            None,
            tc,
        )
    assert m.scene_state.current_tension_level == "extreme"
    assert tc["hybrid_pacing"]["pacing_source"] == "consequence"
    assert tc["hybrid_pacing"]["pacing_direction"] == "up"
    assert tc["hybrid_pacing"].get("consequence_up_suppressed_saturation") is None


def test_update_scene_state_consequence_up_at_extreme_suppressed() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "extreme"
    tc = _minimal_turn_consequences()
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="up",
    ):
        m._update_scene_state(
            "A",
            {"action": "acts", "dialogue": "", "motivation": {}},
            {"tension_shift": "", "environment_event": ""},
            None,
            tc,
        )
    assert m.scene_state.current_tension_level == "extreme"
    assert tc["hybrid_pacing"]["pacing_source"] == "none"
    assert tc["hybrid_pacing"]["pacing_direction"] == "hold"
    assert tc["hybrid_pacing"]["director_neutral"] is True
    assert tc["hybrid_pacing"]["consequence_up_suppressed_saturation"] is True


def test_update_scene_state_consequence_down_at_extreme_unchanged() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "extreme"
    m.scene_state.phase = ScenePhase.CLIMAX
    tc = _minimal_turn_consequences()
    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="down",
    ):
        m._update_scene_state(
            "A",
            {"action": "acts", "dialogue": "", "motivation": {}},
            {"tension_shift": ""},
            None,
            tc,
        )
    assert m.scene_state.current_tension_level == "high"
    assert tc["hybrid_pacing"]["pacing_source"] == "consequence"
    assert tc["hybrid_pacing"]["pacing_direction"] == "down"
    assert tc["hybrid_pacing"].get("consequence_up_suppressed_saturation") is None


def test_update_scene_state_director_escalate_at_extreme_no_suppression_flag() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "extreme"
    tc = _minimal_turn_consequences()
    m._update_scene_state(
        "A",
        {"action": "acts", "dialogue": "", "motivation": {}},
        {"tension_shift": "escalate", "environment_event": ""},
        None,
        tc,
    )
    assert m.scene_state.current_tension_level == "extreme"
    assert tc["hybrid_pacing"]["pacing_source"] == "director"
    assert tc["hybrid_pacing"]["pacing_direction"] == "up"
    assert tc["hybrid_pacing"].get("consequence_up_suppressed_saturation") is None


def test_malformed_director_decision_treated_as_neutral() -> None:
    m = ContinuityManager()
    m.initialize_scene(location="X", opening_description="T", present_characters=["A"])
    assert m.scene_state
    m.scene_state.current_tension_level = "moderate"
    tc = _minimal_turn_consequences()
    m._update_scene_state(
        "A",
        {"action": "acts", "dialogue": "", "motivation": {}},
        None,  # type: ignore[arg-type]
        None,
        tc,
    )
    assert m.scene_state.current_tension_level == "moderate"
    assert tc["hybrid_pacing"]["director_neutral"] is True
    assert tc["hybrid_pacing"]["pacing_source"] == "none"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from scene_exit_detection import detect_exit_from_scene, has_hard_scene_departure_evidence


def test_has_hard_scene_departure_explicit_action() -> None:
    move = {
        "action": "turned on her heel and left the room",
        "dialogue": "",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
    }
    assert has_hard_scene_departure_evidence(move, None) is True
    assert detect_exit_from_scene(move, None) is True


def test_has_hard_scene_departure_storms_out() -> None:
    move = {
        "action": "storms out",
        "dialogue": "",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
    }
    assert has_hard_scene_departure_evidence(move, None) is True
    assert detect_exit_from_scene(move, None) is True


def test_has_hard_scene_departure_not_spun_internal_motion() -> None:
    move = {
        "action": "spun away toward the doorway with a laugh, bouncing toward the hall",
        "dialogue": "Tick-tock!",
        "motivation": {
            "goal": "escalate chaos",
            "tactic": "pressure others",
            "emotional_driver": "glee",
            "risk_level": "high",
        },
    }
    assert has_hard_scene_departure_evidence(move, None) is False
    assert detect_exit_from_scene(move, None) is False


def test_structured_presence_exit_not_hard_evidence() -> None:
    """LLM or downstream lists must not bypass safeguards as hard departure."""
    move = {
        "action": "nods",
        "dialogue": "",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
        "presence_changes": [{"change": "exit", "character": "Test_Char"}],
    }
    assert has_hard_scene_departure_evidence(move, None) is False
    assert detect_exit_from_scene(move, None) is False


def test_state_change_echo_does_not_trigger_exit() -> None:
    move = {
        "action": "grins and pokes a cheek",
        "dialogue": "C'mon, Sunshine!",
        "motivation": {
            "goal": "escalate",
            "tactic": "pressure",
            "emotional_driver": "glee",
            "risk_level": "high",
        },
        "state_changes": [
            'Some_Char left the immediate scene.',
            "The targeted character must exit, challenge back, or submit.",
        ],
    }
    assert detect_exit_from_scene(move, None) is False


def test_soft_path_requires_completion_for_movement_and_boundary() -> None:
    move = {
        "action": "walked into the hallway yelling",
        "dialogue": "",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
    }
    assert detect_exit_from_scene(move, None) is False


def test_soft_path_true_with_completion() -> None:
    move = {
        "action": "walked out of the room without looking back",
        "dialogue": "",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
    }
    assert detect_exit_from_scene(move, None) is True


def test_threat_get_out_without_departure_cues() -> None:
    move = {
        "action": "steps closer",
        "dialogue": "Get out of my face before I lose it.",
        "motivation": {
            "goal": "intimidate",
            "tactic": "verbal threat",
            "emotional_driver": "anger",
            "risk_level": "medium",
        },
    }
    assert has_hard_scene_departure_evidence(move, None) is False
    assert detect_exit_from_scene(move, None) is False


def test_motivation_only_leave_does_not_trigger_soft_exit() -> None:
    move = {
        "action": "",
        "dialogue": "",
        "motivation": {
            "goal": "leave the dorm and go home",
            "tactic": "",
            "emotional_driver": "",
            "risk_level": "low",
        },
    }
    assert detect_exit_from_scene(move, None) is False

import sys
from pathlib import Path


from scene_exit_detection import (
    authored_prose_suppresses_physical_departure,
    detect_exit_from_scene,
    has_hard_scene_departure_evidence,
)


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


def test_ultimatum_walk_out_or_is_not_hard_departure() -> None:
    move = {
        "action": "plants herself in the doorway",
        "dialogue": "Walk out, or I carry you.",
        "motivation": {
            "goal": "force compliance",
            "tactic": "ultimatum",
            "emotional_driver": "resolve",
            "risk_level": "medium",
        },
    }
    assert has_hard_scene_departure_evidence(move, None) is False
    assert detect_exit_from_scene(move, None) is False


def test_directed_you_better_walk_out_not_hard_departure() -> None:
    move = {
        "action": "points at the door",
        "dialogue": "You better walk out before I call security.",
        "motivation": {
            "goal": "eject the other party",
            "tactic": "threat",
            "emotional_driver": "anger",
            "risk_level": "medium",
        },
    }
    assert has_hard_scene_departure_evidence(move, None) is False


def test_self_exit_still_hard_when_coupled_with_ultimatum_clause() -> None:
    move = {
        "action": "grabs her bag",
        "dialogue": "I'm leaving. Walk out, or stay and watch the door close.",
        "motivation": {
            "goal": "exit on her terms",
            "tactic": "parting shot",
            "emotional_driver": "hurt",
            "risk_level": "medium",
        },
    }
    assert has_hard_scene_departure_evidence(move, None) is True
    assert detect_exit_from_scene(move, None) is True


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


def test_negated_no_walking_out_mid_sentence_no_hard_exit() -> None:
    move = {
        "action": "tapped the table once",
        "dialogue": "We keep going until this is settled—no walking out mid-sentence.",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
    }
    assert has_hard_scene_departure_evidence(move, None) is False


def test_negated_no_walking_out_on_me_no_hard_exit() -> None:
    move = {
        "action": "held her ground",
        "dialogue": "There's no walking out on me, not tonight.",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
    }
    assert has_hard_scene_departure_evidence(move, None) is False


def test_issue18_rhetorical_walking_out_conditional_not_hard_departure() -> None:
    """Session 475 turn 7 pattern: exit language toward others; speaker stays on stage."""
    move = {
        "action": "kept her hand on the doorframe, her eyes locked on Hannah, then cut a sharp glance toward Ayame before returning her focus to Hannah",
        "dialogue": (
            "You think walking out is a punishment? Fine. Walk. But you're not taking your 'protection' with you—you're leaving it here, with me. "
            "And you're leaving her with me. So if you want to withdraw, withdraw. But don't pretend it's a fucking prize."
        ),
        "motivation": {
            "goal": "call Hannah's bluff and reassert territorial control",
            "tactic": "reframe Hannah's exit as abandonment",
            "emotional_driver": "cold, territorial anger and protective urgency",
            "risk_level": "high",
        },
    }
    assert authored_prose_suppresses_physical_departure(move) is True
    assert has_hard_scene_departure_evidence(move, None) is False


def test_negated_walking_out_plus_first_person_still_hard_exit() -> None:
    move = {
        "action": "stood",
        "dialogue": "No walking out mid-sentence—but I'm leaving anyway.",
        "motivation": {"goal": "", "tactic": "", "emotional_driver": "", "risk_level": "low"},
    }
    assert has_hard_scene_departure_evidence(move, None) is True
    assert detect_exit_from_scene(move, None) is True

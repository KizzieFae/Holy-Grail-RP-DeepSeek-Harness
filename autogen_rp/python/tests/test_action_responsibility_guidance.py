from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_director import _compute_action_responsibility_hint


def test_compute_action_responsibility_hint_high_for_grant_or_withhold_controlled_action() -> None:
    hint = _compute_action_responsibility_hint(
        last_structured_move={
            "speaker": "Celina",
            "action": "holds out her hand for the key",
            "dialogue": "Ayame, give me the key.",
            "audibility": "directed",
            "audience": ["Ayame"],
        },
        available_actors=["Ayame", "Celina"],
        responder_obligation={"active": False},
    )

    assert hint["active"] is True
    assert hint["confidence"] == "high"
    assert hint["primary_actor"] == "Ayame"
    assert hint["responsibility_mode"] == "grant_or_withhold_controlled_action"
    assert hint["candidates"] == [
        {
            "actor": "Ayame",
            "signals": ["controls_bounded_next_step", "must_grant_or_refuse"],
        }
    ]


def test_compute_action_responsibility_hint_high_for_comply_or_refuse_concrete_directive() -> None:
    hint = _compute_action_responsibility_hint(
        last_structured_move={
            "speaker": "Ayame",
            "action": "points toward the couch",
            "dialogue": "Celina, take the couch tonight.",
            "audibility": "directed",
            "audience": ["Celina"],
        },
        available_actors=["Ayame", "Celina"],
        responder_obligation={"active": False},
    )

    assert hint["active"] is True
    assert hint["confidence"] == "high"
    assert hint["primary_actor"] == "Celina"
    assert hint["responsibility_mode"] == "comply_or_refuse_concrete_directive"
    assert hint["candidates"] == [
        {
            "actor": "Celina",
            "signals": ["concrete_directive_target", "must_comply_or_refuse"],
        }
    ]


def test_compute_action_responsibility_hint_medium_without_primary_when_ambiguous() -> None:
    hint = _compute_action_responsibility_hint(
        last_structured_move={
            "speaker": "Mira",
            "action": "points at both of them",
            "dialogue": "Ayame, Celina, stay here until I say otherwise.",
            "audibility": "directed",
            "audience": ["Ayame", "Celina"],
        },
        available_actors=["Ayame", "Celina", "Mira"],
        responder_obligation={"active": False},
    )

    assert hint["active"] is True
    assert hint["confidence"] == "medium"
    assert "primary_actor" not in hint
    assert hint["responsibility_mode"] == "comply_or_refuse_concrete_directive"
    assert hint["candidates"] == [
        {
            "actor": "Ayame",
            "signals": ["concrete_directive_target", "must_comply_or_refuse"],
        },
        {
            "actor": "Celina",
            "signals": ["concrete_directive_target", "must_comply_or_refuse"],
        },
    ]


def test_compute_action_responsibility_hint_none_when_no_clear_bounded_action_owner() -> None:
    hint = _compute_action_responsibility_hint(
        last_structured_move={
            "speaker": "Ayame",
            "action": "glances toward the window",
            "dialogue": "The rain is getting worse.",
            "audibility": "public",
            "audience": [],
        },
        available_actors=["Ayame", "Celina"],
        responder_obligation={"active": False},
    )

    assert hint == {
        "active": False,
        "soft_priority": True,
        "confidence": "none",
        "candidates": [],
        "instruction": "No clear bounded action owner detected from the immediately prior move.",
    }


def test_compute_action_responsibility_hint_is_blocked_when_responder_obligation_is_active() -> None:
    hint = _compute_action_responsibility_hint(
        last_structured_move={
            "speaker": "Celina",
            "action": "holds out her hand for the key",
            "dialogue": "Ayame, give me the key.",
            "audibility": "directed",
            "audience": ["Ayame"],
        },
        available_actors=["Ayame", "Celina"],
        responder_obligation={
            "active": True,
            "confidence": "high",
            "primary_actor": "Ayame",
        },
    )

    assert hint == {
        "active": False,
        "soft_priority": True,
        "confidence": "none",
        "candidates": [],
        "instruction": "No clear bounded action owner detected from the immediately prior move.",
    }

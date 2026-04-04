from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_turn_director import _compute_responder_obligation_hint


def test_compute_responder_obligation_hint_high_for_directed_question() -> None:
    hint = _compute_responder_obligation_hint(
        last_structured_move={
            "speaker": "Ayame",
            "action": "turns to Celina",
            "dialogue": "Celina, answer me now?",
            "audibility": "directed",
            "audience": ["Celina"],
        },
        available_actors=["Ayame", "Celina"],
        present_characters=["Ayame", "Celina"],
    )

    assert hint["active"] is True
    assert hint["confidence"] == "high"
    assert hint["primary_actor"] == "Celina"
    assert hint["candidates"] == [
        {
            "actor": "Celina",
            "signals": [
                "direct_address",
                "explicit_question",
                "accusation_or_challenge",
                "required_response_to_prior_move",
            ],
        }
    ]


def test_compute_responder_obligation_hint_medium_without_primary_when_ambiguous() -> None:
    hint = _compute_responder_obligation_hint(
        last_structured_move={
            "speaker": "Mira",
            "action": "faces both of them",
            "dialogue": "Explain yourselves.",
            "audibility": "directed",
            "audience": ["Ayame", "Celina"],
        },
        available_actors=["Ayame", "Celina", "Mira"],
        present_characters=["Ayame", "Celina", "Mira"],
    )

    assert hint["active"] is True
    assert hint["confidence"] == "medium"
    assert "primary_actor" not in hint
    assert hint["candidates"] == [
        {
            "actor": "Ayame",
            "signals": [
                "accusation_or_challenge",
                "required_response_to_prior_move",
            ],
        },
        {
            "actor": "Celina",
            "signals": [
                "accusation_or_challenge",
                "required_response_to_prior_move",
            ],
        },
    ]


def test_compute_responder_obligation_hint_none_when_no_clear_obligation() -> None:
    hint = _compute_responder_obligation_hint(
        last_structured_move={
            "speaker": "Ayame",
            "action": "glances at the room",
            "dialogue": "The forge is still hot.",
            "audibility": "public",
            "audience": [],
        },
        available_actors=["Ayame", "Celina"],
        present_characters=["Ayame", "Celina"],
    )

    assert hint == {
        "active": False,
        "soft_priority": True,
        "confidence": "none",
        "candidates": [],
        "instruction": "No clear immediate responder obligation detected.",
    }


def test_compute_responder_obligation_hint_inactive_for_pure_physical_directive() -> None:
    """Concrete comply/refuse directives use action_responsibility, not reply obligation."""
    hint = _compute_responder_obligation_hint(
        last_structured_move={
            "speaker": "Ayame",
            "action": "points to the couch",
            "dialogue": "Celina, take the couch tonight.",
            "audibility": "directed",
            "audience": ["Celina"],
        },
        available_actors=["Ayame", "Celina"],
        present_characters=["Ayame", "Celina"],
    )

    assert hint["active"] is False
    assert hint["confidence"] == "none"
    assert hint["candidates"] == []

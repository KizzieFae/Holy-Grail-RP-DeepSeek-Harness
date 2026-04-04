from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from director_low_pressure_guidance import (
    all_available_have_spoken_this_cycle,
    build_director_selection_metrics,
    compute_responder_hint,
    consecutive_trailing_same_speaker,
    low_pressure_turn_guidance_active,
)


def test_consecutive_trailing_same_speaker() -> None:
    assert consecutive_trailing_same_speaker([]) == 0
    assert consecutive_trailing_same_speaker(["A"]) == 1
    assert consecutive_trailing_same_speaker(["A", "B", "B", "B"]) == 3
    assert consecutive_trailing_same_speaker(["A", "A", "B"]) == 1


def test_all_available_have_spoken_this_cycle() -> None:
    assert not all_available_have_spoken_this_cycle(
        available_actors=["A", "B"],
        actors_used_this_round=["A"],
    )
    assert all_available_have_spoken_this_cycle(
        available_actors=["A", "B"],
        actors_used_this_round=["A", "B"],
    )


def test_low_pressure_turn_guidance_active_conditions() -> None:
    base = dict(
        beat_shift_active=False,
        progression_pressure="low",
        available_actors=["A", "B"],
        continuation_override_actor=None,
        anti_regression_director_hints_active=False,
    )
    assert low_pressure_turn_guidance_active(**base) is True

    assert low_pressure_turn_guidance_active(**{**base, "beat_shift_active": True}) is False
    assert (
        low_pressure_turn_guidance_active(**{**base, "progression_pressure": "high"})
        is False
    )
    assert low_pressure_turn_guidance_active(**{**base, "available_actors": ["A"]}) is False
    assert (
        low_pressure_turn_guidance_active(
            **{**base, "continuation_override_actor": "A"}
        )
        is False
    )
    assert (
        low_pressure_turn_guidance_active(
            **{**base, "anti_regression_director_hints_active": True}
        )
        is False
    )


def test_compute_responder_hint_high_directed_single_audience() -> None:
    move = {
        "speaker": "Ayame",
        "action": "leans in",
        "dialogue": "Only for you.",
        "audibility": "directed",
        "audience": ["Celina"],
    }
    hint = compute_responder_hint(
        last_structured_move=move,
        available_actors=["Ayame", "Celina"],
        present_characters=["Ayame", "Celina"],
    )
    assert hint["confidence"] == "high"
    assert hint["suggested_actor"] == "Celina"
    assert hint["reason"] == "directed_audience_single"


def test_compute_responder_hint_none_public() -> None:
    move = {
        "speaker": "Ayame",
        "action": "says",
        "dialogue": "Hello everyone.",
        "audibility": "public",
        "audience": [],
    }
    hint = compute_responder_hint(
        last_structured_move=move,
        available_actors=["Ayame", "Celina"],
        present_characters=["Ayame", "Celina"],
    )
    assert hint["confidence"] == "none"


def test_compute_responder_hint_none_multiple_audience() -> None:
    move = {
        "speaker": "Ayame",
        "action": "whispers",
        "dialogue": "Hey.",
        "audibility": "directed",
        "audience": ["Celina", "Hannah"],
    }
    hint = compute_responder_hint(
        last_structured_move=move,
        available_actors=["Ayame", "Celina", "Hannah"],
        present_characters=["Ayame", "Celina", "Hannah"],
    )
    assert hint["confidence"] == "none"


def test_build_director_selection_metrics_compliance_and_repeat() -> None:
    m = build_director_selection_metrics(
        low_pressure_regime=True,
        consecutive_spotlight_same=2,
        all_available_have_spoken=True,
        responder_hint={
            "confidence": "high",
            "suggested_actor": "Celina",
            "reason": "directed_audience_single",
        },
        director_pick="Celina",
        spotlight_last_before_pick="Ayame",
        end_round=False,
    )
    assert m["responder_hint_compliance"] is True
    assert m["repeat_after_all_heard"] is False

    m2 = build_director_selection_metrics(
        low_pressure_regime=True,
        consecutive_spotlight_same=1,
        all_available_have_spoken=True,
        responder_hint={"confidence": "high", "suggested_actor": "Celina"},
        director_pick="Ayame",
        spotlight_last_before_pick="Ayame",
        end_round=False,
    )
    assert m2["responder_hint_compliance"] is False
    assert m2["repeat_after_all_heard"] is True

    m3 = build_director_selection_metrics(
        low_pressure_regime=False,
        consecutive_spotlight_same=0,
        all_available_have_spoken=False,
        responder_hint={"confidence": "none"},
        director_pick="Ayame",
        spotlight_last_before_pick=None,
        end_round=True,
    )
    assert "responder_hint_compliance" not in m3

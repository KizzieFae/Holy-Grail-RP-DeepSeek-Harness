"""Anti-regression advisory: ping-pong, post-break window, low player agency (option A trigger)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from anti_regression_advisory import (
    arm_post_break_window,
    build_anti_regression_director_prefix,
    detect_ping_pong_pair,
    low_player_agency,
    player_speaker_labels,
    refresh_anti_regression_advisory_cache,
    sync_anti_regression_advisory_for_prompts,
)
from prompt_builders import build_director_selection_prompt


def test_detect_ping_pong_pair_positive() -> None:
    d = [
        {"next_actor": "X"},
        {"next_actor": "Y"},
        {"next_actor": "X"},
        {"next_actor": "Y"},
    ]
    ok, a, b = detect_ping_pong_pair(d)
    assert ok and a == "X" and b == "Y"


def test_detect_ping_pong_pair_reject_same_actor() -> None:
    d = [{"next_actor": "A"}] * 4
    ok, _, _ = detect_ping_pong_pair(d)
    assert not ok


def test_low_player_agency() -> None:
    moves = [{"speaker": "Willow"}] * 8
    assert low_player_agency(moves, {"Kizzie"}) is True
    moves2 = [{"speaker": "Kizzie"}, {"speaker": "Kizzie"}] + [{"speaker": "W"}] * 6
    assert low_player_agency(moves2, {"Kizzie"}) is False


def test_player_speaker_labels_intersection() -> None:
    ss = {"player_character": "Kizzie", "user_name": "nope"}
    assert player_speaker_labels(ss, ["Kizzie", "Willow"]) == {"Kizzie"}


def test_trigger_ping_pong_and_post_break() -> None:
    orch: dict = {
        "director_decisions": [
            {"next_actor": "A"},
            {"next_actor": "B"},
            {"next_actor": "A"},
            {"next_actor": "B"},
        ],
        "recent_structured_moves": [{"speaker": "A", "action": "x"}] * 8,
    }
    arm_post_break_window(orch)
    out = refresh_anti_regression_advisory_cache(
        orchestration_state=orch,
        progression_advisory={"stall_score": 0.5},
        session_state={},
        participant_names=["A", "B", "C"],
    )
    assert "ANTI-REGRESSION" in out["prompt_prefix"]
    assert out["advisory_blob"]["active"] is True
    assert out["advisory_blob"]["ping_pong_detected"] is True


def test_no_trigger_without_post_break_or_agency() -> None:
    orch: dict = {
        "director_decisions": [
            {"next_actor": "A"},
            {"next_actor": "B"},
            {"next_actor": "A"},
            {"next_actor": "B"},
        ],
        "recent_structured_moves": [{"speaker": "A"}] * 8,
    }
    out = refresh_anti_regression_advisory_cache(
        orchestration_state=orch,
        progression_advisory={"stall_score": 0.5},
        session_state={},
        participant_names=["A", "B"],
    )
    assert out["prompt_prefix"] == ""
    assert out["advisory_blob"]["active"] is False


def test_trigger_ping_pong_and_low_agency() -> None:
    orch: dict = {
        "director_decisions": [
            {"next_actor": "A"},
            {"next_actor": "B"},
            {"next_actor": "A"},
            {"next_actor": "B"},
        ],
        "recent_structured_moves": [{"speaker": "A"}] * 8,
    }
    out = refresh_anti_regression_advisory_cache(
        orchestration_state=orch,
        progression_advisory={"stall_score": 0.9},
        session_state={"player_character": "Kizzie"},
        participant_names=["A", "B", "Kizzie"],
    )
    assert "ANTI-REGRESSION" in out["prompt_prefix"]
    assert out["advisory_blob"]["low_player_agency"] is True


def test_high_stall_alone_not_enough_without_ping_pong_other_disjuncts() -> None:
    """Option A: high stall does not OR into trigger; need post_break or low_agency too."""
    orch: dict = {
        "director_decisions": [
            {"next_actor": "A"},
            {"next_actor": "A"},
            {"next_actor": "B"},
            {"next_actor": "B"},
        ],
        "recent_structured_moves": [{"speaker": "A"}] * 8,
    }
    out = refresh_anti_regression_advisory_cache(
        orchestration_state=orch,
        progression_advisory={"stall_score": 0.95},
        session_state={"player_character": "Kizzie"},
        participant_names=["A", "B", "Kizzie"],
    )
    assert out["prompt_prefix"] == ""


def test_stall_cross_arms_post_break_next_refresh() -> None:
    orch: dict = {
        "director_decisions": [
            {"next_actor": "W"},
            {"next_actor": "M"},
            {"next_actor": "W"},
            {"next_actor": "M"},
        ],
        "recent_structured_moves": [{"speaker": "W"}] * 8,
        "_anti_regression_prev_stall_score": 0.85,
    }
    out = refresh_anti_regression_advisory_cache(
        orchestration_state=orch,
        progression_advisory={"stall_score": 0.2},
        session_state={},
        participant_names=["W", "M", "K"],
    )
    assert out["advisory_blob"]["post_break_window_active"] is True
    assert "ANTI-REGRESSION" in out["prompt_prefix"]


def test_build_director_prompt_strips_anti_regression_hints() -> None:
    prefix = build_anti_regression_director_prefix(
        actor_a="A",
        actor_b="B",
        player_labels=set(),
        low_agency=False,
    )
    p = build_director_selection_prompt(
        {
            "participants": ["A", "B"],
            "available_next_actors": ["A", "B"],
            "anti_regression_director_hints": {"active": True, "prompt_prefix": prefix},
        }
    )
    assert "ANTI-REGRESSION" in p
    assert "anti_regression_director_hints" not in p


def test_sync_wrapper() -> None:
    orch: dict = {"director_decisions": [], "recent_structured_moves": []}
    sync_anti_regression_advisory_for_prompts(
        orchestration_state=orch,
        progression_advisory={},
        session_state={},
        participant_names=[],
    )

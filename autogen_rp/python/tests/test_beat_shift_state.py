"""Phase 2: pending beat-shift detection and lifecycle helpers."""

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from beat_shift_state import (
    append_scene_snapshot_after_turn,
    build_character_beat_shift_suffix,
    build_narrator_beat_shift_suffix,
    consume_pending_beat_shift_if_active,
    default_pending_beat_shift,
    is_pending_beat_shift_active,
    maybe_activate_pending_beat_shift,
    plateau_snapshots_suggest_beat_shift,
    user_message_suggests_beat_shift,
)


def test_user_message_short_triggers() -> None:
    ok, reason = user_message_suggests_beat_shift("Knot! Knot! Knot! Knot!")
    assert ok is True
    assert reason == "short_user_message"


def test_user_message_repeated_words_triggers() -> None:
    ok, reason = user_message_suggests_beat_shift(
        "This is a much longer line that still has Knot Knot in the middle"
    )
    assert ok is True
    assert reason == "repeated_words_user_message"


def test_user_message_long_no_repeat_no_trigger() -> None:
    ok, _ = user_message_suggests_beat_shift(
        "One two three four five six seven eight nine ten eleven"
    )
    assert ok is False


def test_plateau_two_climax_extreme_triggers() -> None:
    snaps = [
        {"phase": "climax", "tension": "extreme"},
        {"phase": "climax", "tension": "extreme"},
    ]
    ok, reason = plateau_snapshots_suggest_beat_shift(snaps)
    assert ok is True
    assert reason == "plateau_same_phase_high_tension"


def test_plateau_mismatch_phase_no_trigger() -> None:
    snaps = [
        {"phase": "climax", "tension": "extreme"},
        {"phase": "rising", "tension": "extreme"},
    ]
    ok, _ = plateau_snapshots_suggest_beat_shift(snaps)
    assert ok is False


def test_phase3_writer_suffixes_include_concrete_change_language() -> None:
    ch = build_character_beat_shift_suffix(trigger_text="Knot!")
    assert "BEAT SHIFT (ACTIVE)" in ch
    assert "concrete change" in ch.lower()
    assert "Knot!" in ch
    nr = build_narrator_beat_shift_suffix()
    assert "BEAT SHIFT (ACTIVE)" in nr
    assert "observable" in nr.lower()


def test_is_pending_beat_shift_active() -> None:
    assert is_pending_beat_shift_active({}) is False
    assert is_pending_beat_shift_active({"pending_beat_shift": {"active": True}}) is True


def test_lifecycle_activate_and_consume(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="rp_app.beat_shift")
    orch: dict = {
        "scene_state": {
            "scene_phase": "climax",
            "current_tension_level": "extreme",
        },
        "beat_shift_scene_snapshots": [
            {"phase": "climax", "tension": "extreme"},
            {"phase": "climax", "tension": "extreme"},
        ],
        "pending_beat_shift": default_pending_beat_shift(),
    }
    maybe_activate_pending_beat_shift(
        orch,
        trigger_text="alpha beta gamma delta epsilon zeta eta theta",
        source_turn_id="user_round_1",
        active_issues=[{"status": "escalating"}, {"status": "active"}],
        recent_structured_moves=[],
    )
    assert orch["pending_beat_shift"]["active"] is True
    assert orch["pending_beat_shift"]["reason"] == "progression_stall"
    assert "set active" in caplog.text

    orch["scene_state"] = {"scene_phase": "climax", "current_tension_level": "extreme"}
    consume_pending_beat_shift_if_active(orch)
    assert orch["pending_beat_shift"]["active"] is False
    assert "consumed and cleared" in caplog.text

    append_scene_snapshot_after_turn(orch)
    assert orch["beat_shift_scene_snapshots"][-1]["phase"] == "climax"

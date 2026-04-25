"""Progression advisory MVP: stall score, pressure, template profile, beat-shift hook."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from beat_shift_state import default_pending_beat_shift, maybe_activate_pending_beat_shift
from progression_advisory import (
    STALL_BEAT_SHIFT_THRESHOLD,
    build_progression_advisory,
    build_progression_director_prompt_prefix,
    compute_stall_score,
    default_progression_profile,
    load_progression_profile_for_template_id,
    normalize_progression_profile,
    should_append_progression_character_suffix,
    stall_score_to_pressure,
    sync_progression_advisory_for_prompts,
)


def test_stall_score_weights_plateau_high_tension_issues() -> None:
    score, comp = compute_stall_score(
        scene_state={"current_tension_level": "extreme"},
        recent_structured_moves=[],
        active_issues=[{"status": "active"}, {"status": "escalating"}],
        beat_shift_snapshots=[
            {"phase": "climax", "tension": "extreme"},
            {"phase": "climax", "tension": "extreme"},
        ],
    )
    assert comp["same_phase"] is True
    assert comp["high_tension"] is True
    assert comp["issue_stability"] is True
    assert score >= STALL_BEAT_SHIFT_THRESHOLD


def test_stall_score_low_when_no_signals() -> None:
    score, comp = compute_stall_score(
        scene_state={"current_tension_level": "low"},
        recent_structured_moves=[],
        active_issues=[],
        beat_shift_snapshots=[],
    )
    assert score < 0.3
    assert stall_score_to_pressure(score) == "low"
    assert comp["same_phase"] is False


def test_exact_structural_repetition_component() -> None:
    prev = {
        "speaker": "A",
        "action": "nods",
        "dialogue": "Yes.",
        "motivation": {"goal": "agree", "tactic": "nod"},
    }
    cur_move = {
        "action": "nods",
        "dialogue": "Yes.",
        "motivation": {"goal": "agree", "tactic": "nod"},
    }
    _, comp = compute_stall_score(
        scene_state={"current_tension_level": "low"},
        recent_structured_moves=[prev],
        active_issues=[],
        beat_shift_snapshots=[],
        current_actor="A",
        current_move=cur_move,
    )
    assert comp["exact_structural_repetition"] is True


def test_exact_repetition_false_when_immediate_prior_is_other_actor() -> None:
    prev = {
        "speaker": "B",
        "action": "nods",
        "dialogue": "Yes.",
        "motivation": {},
    }
    cur_move = {"action": "nods", "dialogue": "Yes.", "motivation": {}}
    _, comp = compute_stall_score(
        scene_state={"current_tension_level": "low"},
        recent_structured_moves=[prev],
        active_issues=[],
        beat_shift_snapshots=[],
        current_actor="A",
        current_move=cur_move,
    )
    assert comp["exact_structural_repetition"] is False


def test_pressure_buckets() -> None:
    assert stall_score_to_pressure(0.0) == "low"
    assert stall_score_to_pressure(0.29) == "low"
    assert stall_score_to_pressure(0.3) == "medium"
    assert stall_score_to_pressure(0.59) == "medium"
    assert stall_score_to_pressure(0.6) == "high"


def test_build_progression_advisory_note_and_channels() -> None:
    adv = build_progression_advisory(
        stall_score=0.85,
        stall_components={"same_phase": True, "high_tension": True},
        progression_profile=default_progression_profile(),
    )
    assert adv["progression_pressure"] == "high"
    assert "recommended_channels" in adv
    assert adv["stall_components"]["same_phase"] is True
    assert "verbal escalation" in adv["note"].lower() or "pattern" in adv["note"].lower()


def test_director_prefix_only_high_pressure() -> None:
    assert build_progression_director_prompt_prefix({"progression_pressure": "low"}) == ""
    hi = build_progression_director_prompt_prefix(
        {
            "progression_pressure": "high",
            "recommended_channels": ["physical_action", "spatial_shift"],
        }
    )
    assert "PROGRESSION ADVISORY" in hi
    assert "physical action" in hi.lower()


def test_character_suffix_gate() -> None:
    assert should_append_progression_character_suffix(
        progression_pressure="high", beat_shift_active=False
    )
    assert should_append_progression_character_suffix(
        progression_pressure="medium", beat_shift_active=True
    )
    assert not should_append_progression_character_suffix(
        progression_pressure="medium", beat_shift_active=False
    )


def test_maybe_activate_uses_progression_stall_from_stall_score_only() -> None:
    orch = {
        "scene_state": {"scene_phase": "climax", "current_tension_level": "extreme"},
        "beat_shift_scene_snapshots": [
            {"phase": "climax", "tension": "extreme"},
            {"phase": "climax", "tension": "extreme"},
        ],
        "pending_beat_shift": default_pending_beat_shift(),
        "recent_structured_moves": [],
    }
    maybe_activate_pending_beat_shift(
        orch,
        trigger_text="one two three four five six seven eight nine",
        source_turn_id="r1",
        active_issues=[{"status": "escalating"}],
        recent_structured_moves=orch["recent_structured_moves"],
    )
    assert orch["pending_beat_shift"]["active"] is True
    assert orch["pending_beat_shift"]["reason"] == "progression_stall"


def test_load_profile_dorm_template() -> None:
    prof = load_progression_profile_for_template_id("marlene_willow_dorm_omega_misassignment")
    assert "physical_action" in prof["advancement_channels"]
    assert "stall" in prof["common_stall_pattern"].lower() or "verbal" in prof[
        "common_stall_pattern"
    ].lower()
    # Loader reads only {template_id}_progression.json; should match the authored support file shape.
    assert prof == normalize_progression_profile(
        {
            "advancement_channels": [
                "physical_action",
                "spatial_shift",
                "bureaucratic_followthrough",
                "social_reconfiguration",
                "consequence",
            ],
            "common_stall_pattern": "verbal escalation loop without state change",
        }
    )


def test_normalize_profile_invalid_channels_fallback() -> None:
    p = normalize_progression_profile({"advancement_channels": "nope"})
    assert p["advancement_channels"] == default_progression_profile()["advancement_channels"]


def test_sync_cache_sets_orchestration_key() -> None:
    orch: dict = {
        "scene_state": {
            "scene_template_id": "",
            "current_tension_level": "low",
        },
        "recent_structured_moves": [],
        "beat_shift_scene_snapshots": [],
    }
    sync_progression_advisory_for_prompts(
        orchestration_state=orch,
        continuity_manager=None,
    )
    assert "_progression_advisory_cache" in orch
    assert "stall_score" in orch["_progression_advisory_cache"]

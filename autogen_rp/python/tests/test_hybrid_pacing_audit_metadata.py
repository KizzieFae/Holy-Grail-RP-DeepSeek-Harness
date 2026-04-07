"""Validate hybrid_pacing is copied into persisted character audit metadata."""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_manager import ContinuityManager
from tension_pacing_policy import consequence_tension_recommendation
from turn_runner_audit import log_character_turn_audit


def _summary_audit_stub() -> dict:
    return {
        "summary_generation_eligible": True,
        "summary_blocks_generated_total": 0,
        "generated_summary_block_ids": [],
        "summary_blocks_available_count": 0,
        "available_summary_block_ids": [],
        "summary_blocks_selected_count": 0,
        "selected_summary_block_ids": [],
        "excluded_summary_block_ids": [],
        "selection_reason": "",
        "skipped_reason": "",
        "fallback_used": False,
        "summary_limit": None,
        "has_binding_constraints": False,
        "scene_binding_constraints_section": "",
    }


def test_log_character_turn_audit_metadata_contains_hybrid_pacing_director() -> None:
    captured: dict = {}

    class _Logger:
        def create_entry(self, **kwargs):
            captured.clear()
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry) -> None:
            pass

    m = ContinuityManager()
    m.initialize_scene(
        location="Lab",
        opening_description="Test",
        present_characters=["Alice"],
    )
    m.process_turn(
        acting_character="Alice",
        move={
            "action": "steps forward",
            "dialogue": "Hello.",
            "motivation": {
                "goal": "greet",
                "tactic": "speak",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        },
        director_decision={
            "next_actor": "Alice",
            "environment_event": "",
            "tension_shift": "escalate",
            "reason": "test",
        },
        other_characters=[],
        timestamp=datetime.fromisoformat("2026-04-06T12:00:00"),
    )

    log_character_turn_audit(
        next_actor="Alice",
        move={"action": "steps forward", "dialogue": "Hello."},
        task_prompt="sys",
        char_raw_response="{}",
        decision={"tension_shift": "escalate"},
        char_names=["Alice"],
        continuity_manager=m,
        round_number=1,
        turn_number=1,
        character_summary_block_audit=_summary_audit_stub(),
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
    )
    hp = (captured.get("metadata") or {}).get("hybrid_pacing") or {}
    assert hp.get("pacing_source") == "director"
    assert hp.get("pacing_direction") == "up"
    assert hp.get("director_neutral") is False


def test_log_character_turn_audit_metadata_contains_hybrid_pacing_neutral_none() -> None:
    captured: dict = {}

    class _Logger:
        def create_entry(self, **kwargs):
            captured.clear()
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry) -> None:
            pass

    m = ContinuityManager()
    m.initialize_scene(
        location="Lab",
        opening_description="Test",
        present_characters=["Bob"],
    )
    m.process_turn(
        acting_character="Bob",
        move={
            "action": "nods",
            "dialogue": "Okay.",
            "motivation": {
                "goal": "ack",
                "tactic": "nod",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
        },
        director_decision={
            "next_actor": "Bob",
            "environment_event": "",
            "tension_shift": "steady",
            "reason": "test",
        },
        other_characters=[],
        timestamp=datetime.fromisoformat("2026-04-06T12:00:01"),
    )

    log_character_turn_audit(
        next_actor="Bob",
        move={"action": "nods", "dialogue": "Okay."},
        task_prompt="sys",
        char_raw_response="{}",
        decision={"tension_shift": "steady"},
        char_names=["Bob"],
        continuity_manager=m,
        round_number=1,
        turn_number=1,
        character_summary_block_audit=_summary_audit_stub(),
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
    )
    hp = (captured.get("metadata") or {}).get("hybrid_pacing") or {}
    turn_bucket = m.turn_metadata_by_index[m.turn_counter]
    rec = consequence_tension_recommendation(turn_bucket)
    assert hp.get("director_neutral") is True
    assert hp.get("pacing_direction") == rec
    if rec == "hold":
        assert hp.get("pacing_source") == "none"
    else:
        assert hp.get("pacing_source") == "consequence"


def test_log_character_turn_audit_metadata_consequence_up_suppressed_at_extreme() -> None:
    captured: dict = {}

    class _Logger:
        def create_entry(self, **kwargs):
            captured.clear()
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry) -> None:
            pass

    m = ContinuityManager()
    m.initialize_scene(
        location="Lab",
        opening_description="Test",
        present_characters=["Zed"],
    )
    assert m.scene_state
    m.scene_state.current_tension_level = "extreme"

    with patch(
        "tension_pacing_policy.consequence_tension_recommendation",
        return_value="up",
    ):
        m.process_turn(
            acting_character="Zed",
            move={
                "action": "confronts",
                "dialogue": "No.",
                "motivation": {
                    "goal": "refuse",
                    "tactic": "push back",
                    "emotional_driver": "tense",
                    "risk_level": "high",
                },
            },
            director_decision={
                "next_actor": "Zed",
                "environment_event": "",
                "tension_shift": "",
                "reason": "test",
            },
            other_characters=[],
            timestamp=datetime.fromisoformat("2026-04-06T12:00:02"),
        )

    log_character_turn_audit(
        next_actor="Zed",
        move={"action": "confronts", "dialogue": "No."},
        task_prompt="sys",
        char_raw_response="{}",
        decision={"tension_shift": ""},
        char_names=["Zed"],
        continuity_manager=m,
        round_number=1,
        turn_number=1,
        character_summary_block_audit=_summary_audit_stub(),
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
    )
    hp = (captured.get("metadata") or {}).get("hybrid_pacing") or {}
    assert hp.get("pacing_source") == "none"
    assert hp.get("pacing_direction") == "hold"
    assert hp.get("consequence_up_suppressed_saturation") is True

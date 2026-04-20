"""Issue #79 Slice 1 — CTAR projection and ``continuity_mutation_resolution`` audit export."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from audit_ctar import (
    build_ctar_projection_for_audit,
    canonicalize_continuity_mutation_resolution_for_audit,
)
from continuity_manager import ContinuityManager
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager
from turn_runner_audit import log_character_turn_audit


def test_canonicalize_mutation_resolution_sorts_slot_and_inner_keys() -> None:
    raw = {
        "location": {
            "source": "M",
            "mutation_type": "SPATIAL_TRANSITION",
            "payload": {"location": "Z", "extra": "y"},
        }
    }
    out = canonicalize_continuity_mutation_resolution_for_audit(raw)
    assert list(out.keys()) == ["location"]
    inner = out["location"]
    assert list(inner.keys()) == ["mutation_type", "payload", "source"]
    assert list(inner["payload"].keys()) == ["extra", "location"]


def test_build_ctar_none_without_scene_state() -> None:
    m = SimpleNamespace(scene_state=None)
    assert build_ctar_projection_for_audit(m) is None


def test_build_ctar_minimal_turn_index_only() -> None:
    m = SimpleNamespace(
        scene_state=object(),
        turn_counter=3,
        turn_metadata_by_index={3: {}},
    )
    out = build_ctar_projection_for_audit(m)
    assert out == {"continuity_turn_index": 3}


def test_build_ctar_includes_sorted_consequences() -> None:
    m = SimpleNamespace(
        scene_state=object(),
        turn_counter=1,
        turn_metadata_by_index={
            1: {"consequences": ["zeta", "alpha", "alpha"]},
        },
    )
    out = build_ctar_projection_for_audit(m)
    assert out["continuity_turn_index"] == 1
    assert out["consequences"] == ["alpha", "alpha", "zeta"]


def test_log_character_turn_audit_metadata_includes_ctar_with_mutation_resolution() -> None:
    captured: dict = {}

    class _Logger:
        def create_entry(self, **kwargs):
            captured.clear()
            captured.update(kwargs)
            return object()

        def log_bot_interaction(self, _entry) -> None:
            pass

    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test",
        present_characters=["A", "B"],
    )
    assert mgr.scene_state is not None
    mgr.scene_state.role_assignments = {"A": "guest", "B": "staff"}
    complete_setup_seam_for_test_manager(mgr, cast=["A", "B"])

    mgr.process_turn(
        acting_character="A",
        move={
            "action": "walks",
            "dialogue": "",
            "motivation": {
                "goal": "g",
                "tactic": "t",
                "emotional_driver": "calm",
                "risk_level": "low",
            },
            "spatial_transition": {"location": "Hallway"},
        },
        director_decision={
            "next_actor": "B",
            "environment_event": "",
            "tension_shift": "none",
            "reason": "test",
        },
        other_characters=["B"],
        timestamp=datetime.now(timezone.utc),
    )

    log_character_turn_audit(
        next_actor="A",
        move={"action": "walks", "dialogue": ""},
        task_prompt="sys",
        char_raw_response="{}",
        decision={"next_actor": "B"},
        char_names=["A", "B"],
        continuity_manager=mgr,
        round_number=1,
        turn_number=1,
        character_summary_block_audit={
            "summary_generation_eligible": False,
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
        },
        is_audit_enabled_fn=lambda: True,
        get_audit_logger_fn=lambda: _Logger(),
        get_audit_context_fn=lambda: ("o", 1, 0, 0),
        get_scene_audit_logging_kwargs_fn=lambda *_a, **_k: {},
        get_character_scene_audit_context_fn=lambda *_a, **_k: {},
        effective_user_trigger="",
    )

    meta = captured.get("metadata") or {}
    assert "ctar" in meta
    ctar = meta["ctar"]
    assert ctar["continuity_turn_index"] == mgr.turn_counter
    assert "continuity_mutation_resolution" in ctar
    assert "location" in ctar["continuity_mutation_resolution"]
    loc = ctar["continuity_mutation_resolution"]["location"]
    assert loc["mutation_type"] == "SPATIAL_TRANSITION"
    assert loc["source"] == "M"
    assert "payload" in loc
    snap = captured.get("context_snapshot") or {}
    assert "ctar" not in snap

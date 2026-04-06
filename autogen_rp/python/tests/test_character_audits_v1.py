"""Invariants for character_audit_v1 builder and audit metadata."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_audits_v1 import build_character_audit_v1
from turn_runner_audit import _merge_character_audit_metadata


def test_build_character_audit_v1_single_active_issues_digest_in_observed() -> None:
    move = {"action": "nods", "dialogue": "Hello.", "motivation": {"goal": "greet"}}
    decision = {"next_actor": "A", "tension_shift": "", "environment_event": "", "reason": "r"}
    orch = {
        "scene_state": {
            "location": "here",
            "present_characters": ["a"],
        },
        "recent_structured_moves": [],
        "continuity_active_issues": [],
    }
    audit = build_character_audit_v1(
        move=move,
        decision=decision,
        next_actor="A",
        char_names=["A"],
        trigger_text="t",
        attempt_index=0,
        orchestration_state=orch,
        continuity_scope="orchestration_only",
        scene_state_pre_source_dict=orch["scene_state"],
        issues_before_signatures=None,
        cm_exec=None,
    )
    obs = audit["observed"]
    keys = [k for k in obs if k == "active_issues_digest"]
    assert keys == ["active_issues_digest"]
    assert isinstance(obs["active_issues_digest"], list)


def test_ca5_limitations_imperfect_informational_not_correctness() -> None:
    move = {"action": "mentions Bob", "dialogue": ""}
    decision = {"next_actor": "A", "tension_shift": "", "environment_event": "", "reason": ""}
    orch: dict = {"scene_state": {"present_characters": []}, "recent_structured_moves": []}
    audit = build_character_audit_v1(
        move=move,
        decision=decision,
        next_actor="A",
        char_names=["A"],
        trigger_text="",
        attempt_index=0,
        orchestration_state=orch,
        continuity_scope="orchestration_only",
        scene_state_pre_source_dict=orch["scene_state"],
        issues_before_signatures=None,
        cm_exec=None,
    )
    lim = audit["derived"]["scene_plausibility_flags"]["limitations"]
    assert "imperfect" in lim.lower()
    assert "informational" in lim.lower()
    assert "correctness" in lim.lower()


def test_merge_character_audit_metadata_passes_through_character_audit_v1() -> None:
    stub = {"schema_version": 2, "observed": {}}
    merged = _merge_character_audit_metadata(
        base={"character_audit_v1": stub},
        progression_advisory=None,
        anti_regression_advisory=None,
    )
    assert merged.get("character_audit_v1") is stub

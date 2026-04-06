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


def test_ca4_repetition_no_prior_same_speaker() -> None:
    """CA4 quiet path: no recent_structured_moves entries for this speaker."""
    move = {"action": "nods once", "dialogue": "Ok.", "motivation": {"goal": "x"}}
    decision = {
        "next_actor": "Celina",
        "tension_shift": "",
        "environment_event": "",
        "reason": "",
    }
    orch = {
        "scene_state": {"present_characters": ["celina"]},
        "recent_structured_moves": [
            {
                "speaker": "Bob",
                "action": "waved",
                "dialogue": "Hi there.",
            }
        ],
        "continuity_active_issues": [],
    }
    audit = build_character_audit_v1(
        move=move,
        decision=decision,
        next_actor="Celina",
        char_names=["Celina"],
        trigger_text="",
        attempt_index=0,
        orchestration_state=orch,
        continuity_scope="orchestration_only",
        scene_state_pre_source_dict=orch["scene_state"],
        issues_before_signatures=None,
        cm_exec=None,
    )
    ca4 = audit["derived"]["repetition_vs_prior_self"]
    assert ca4["prior_turns_compared"] == 0
    assert ca4["similarity_metric"] is None
    assert ca4["band"] == "low"


def test_ca4_repetition_prior_same_speaker_dissimilar_wording() -> None:
    """CA4 runs when history includes same speaker; dissimilar tokens → low band."""
    move = {
        "action": "nods once",
        "dialogue": "Ok.",
        "motivation": {"goal": "x"},
    }
    decision = {
        "next_actor": "Celina",
        "tension_shift": "",
        "environment_event": "",
        "reason": "",
    }
    orch = {
        "scene_state": {"present_characters": ["celina"]},
        "recent_structured_moves": [
            {
                "speaker": "Celina",
                "action": "vaulted northward urgently",
                "dialogue": "Cryptic glyphs mesmerizing quartz.",
            }
        ],
        "continuity_active_issues": [],
    }
    audit = build_character_audit_v1(
        move=move,
        decision=decision,
        next_actor="Celina",
        char_names=["Celina"],
        trigger_text="",
        attempt_index=0,
        orchestration_state=orch,
        continuity_scope="orchestration_only",
        scene_state_pre_source_dict=orch["scene_state"],
        issues_before_signatures=None,
        cm_exec=None,
    )
    ca4 = audit["derived"]["repetition_vs_prior_self"]
    assert ca4["prior_turns_compared"] >= 1
    assert ca4["similarity_metric"] is not None
    assert ca4["band"] in {"low", "moderate", "high"}
    assert ca4["band"] == "low"


def test_ca4_repetition_high_similarity_identical_action_dialogue() -> None:
    """Nearly identical prior move → strong Jaccard → high repetition band."""
    shared_action = "stepped forward slowly scanning"
    shared_dialogue = "Wait quietly please everyone listening"
    move = {
        "action": shared_action,
        "dialogue": shared_dialogue,
        "motivation": {"goal": "x"},
    }
    decision = {
        "next_actor": "Celina",
        "tension_shift": "",
        "environment_event": "",
        "reason": "",
    }
    orch = {
        "scene_state": {"present_characters": ["celina"]},
        "recent_structured_moves": [
            {
                "speaker": "Celina",
                "action": shared_action,
                "dialogue": shared_dialogue,
            }
        ],
        "continuity_active_issues": [],
    }
    audit = build_character_audit_v1(
        move=move,
        decision=decision,
        next_actor="Celina",
        char_names=["Celina"],
        trigger_text="",
        attempt_index=0,
        orchestration_state=orch,
        continuity_scope="orchestration_only",
        scene_state_pre_source_dict=orch["scene_state"],
        issues_before_signatures=None,
        cm_exec=None,
    )
    ca4 = audit["derived"]["repetition_vs_prior_self"]
    assert ca4["prior_turns_compared"] >= 1
    assert ca4["similarity_metric"] is not None
    assert ca4["similarity_metric"] >= 0.55
    assert ca4["band"] == "high"


def test_merge_character_audit_metadata_passes_through_character_audit_v1() -> None:
    stub = {"schema_version": 2, "observed": {}}
    merged = _merge_character_audit_metadata(
        base={"character_audit_v1": stub},
        progression_advisory=None,
        anti_regression_advisory=None,
    )
    assert merged.get("character_audit_v1") is stub

"""GitHub #225 — Willow-class must_remain (v2 beat-aware exit / proposal authority)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from app_state_scene import enforce_must_remain_presence  # noqa: E402
from character_move_adapters import is_canonical_v2_move  # noqa: E402
from continuity_consequence_classifier_move_tools import (  # noqa: E402
    move_with_flat_text_for_deterministic_tools,
)
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_presence_helpers import PresenceAuthorityScratch  # noqa: E402
from continuity_presence_pipeline import (  # noqa: E402
    manager_apply_must_remain_presence_from_fn,
)
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402
from progression_simulation_scenarios import load_scenario  # noqa: E402
from response_validation_presence import get_must_remain_characters  # noqa: E402
from response_validation_selection import get_available_actors  # noqa: E402
from scene_exit_detection import (  # noqa: E402
    detect_exit_from_scene,
    has_hard_scene_departure_evidence,
    has_scene_reentry_evidence,
)


def _v2_exit_beat_move_hard(*, action: str) -> dict:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": action}],
        "motivation": {
            "goal": "",
            "tactic": "",
            "emotional_driver": "resolve",
            "risk_level": "medium",
        },
    }


def _scene_dict_for(scratch: PresenceAuthorityScratch, location: str = "Dorm") -> dict:
    return {
        "location": location,
        "present_characters": list(scratch.present_characters),
        "offstage_characters": list(scratch.offstage_characters),
        "character_presence_status": dict(scratch.character_presence_status),
        "absent_but_relevant": list(scratch.absent_but_relevant),
        "character_presence_constraints": {},
    }


def test_issue_225_raw_v2_beats_miss_exit_on_raw_move_detect_on_flatten() -> None:
    """Exit signal lives in flattened beat text; raw v2 has no root action for detection."""
    move = _v2_exit_beat_move_hard(action="She left the room and shut the door.")
    assert is_canonical_v2_move(move)
    assert not (str(move.get("action") or "").strip())
    sc = {"location": "Dorm", "present_characters": ["Willow_Reeves", "Marlene_Fletcher"]}
    assert not detect_exit_from_scene(move, sc, "Willow_Reeves")
    flat = move_with_flat_text_for_deterministic_tools(move)
    assert detect_exit_from_scene(flat, sc, "Willow_Reeves")


def test_issue_225_proposal_off_focal_commits_temporary_offstage() -> None:
    """Off-focal via accepted semantic_proposals (#232), not reconstruction detect."""
    actor = "Willow_Reeves"
    other = "Marlene_Fletcher"
    move = _v2_exit_beat_move_hard(action="She left the room and shut the door.")
    move["semantic_proposals"] = [{"kind": "off_focal", "character": actor}]
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=[actor, other],
    )
    complete_setup_seam_for_test_manager(mgr)
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": other},
        other_characters=[other],
    )
    assert mgr.scene_state is not None
    assert mgr.scene_state.character_presence_status.get(actor) == "temporary_offstage"
    assert actor not in mgr.scene_state.present_characters
    assert actor in mgr.scene_state.offstage_characters


def test_issue_225_soft_beat_detect_is_observational_only() -> None:
    """scene_exit_detection is observational; covered commit requires proposal (#235/#236)."""
    actor = "Willow_Reeves"
    action = (
        "She crossed to the door, turned the handle, and slipped out into the corridor "
        "without looking back."
    )
    move = _v2_exit_beat_move_hard(action=action)
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm room",
        opening_description="Test.",
        present_characters=[actor, "Marlene_Fletcher"],
    )
    scene_dict = mgr.scene_state.to_dict() if mgr.scene_state else {}
    flat = move_with_flat_text_for_deterministic_tools(move)
    assert not has_hard_scene_departure_evidence(flat, scene_dict)
    assert detect_exit_from_scene(flat, scene_dict, actor)
    complete_setup_seam_for_test_manager(mgr)
    before = list(mgr.scene_state.present_characters)
    mgr.process_turn(
        acting_character=actor,
        move=move,
        director_decision={"next_actor": "Marlene_Fletcher"},
        other_characters=["Marlene_Fletcher"],
    )
    assert list(mgr.scene_state.present_characters) == before


def test_issue_225_apply_must_remain_does_not_force_reentry_when_temporary_offstage() -> None:
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Willow_Reeves", "Marlene_Fletcher"],
    )
    assert mgr.scene_state is not None
    w = "Willow_Reeves"
    mgr.scene_state.character_presence_constraints = {w: "must_remain"}
    complete_setup_seam_for_test_manager(mgr)
    mgr.scene_state.present_characters = ["Marlene_Fletcher"]
    mgr.scene_state.offstage_characters = [w]
    mgr.scene_state.character_presence_status[w] = "temporary_offstage"
    mgr.scene_state.absent_but_relevant = [w]

    manager_apply_must_remain_presence_from_fn(mgr, get_must_remain_characters)
    assert mgr.scene_state.character_presence_status.get(w) == "temporary_offstage"
    assert w not in mgr.scene_state.present_characters


def test_issue_225_enforce_must_remain_orchestration_skips_temporary_offstage() -> None:
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm",
        opening_description="Test.",
        present_characters=["Marlene_Fletcher"],
    )
    assert mgr.scene_state is not None
    w = "Willow_Reeves"
    mgr.scene_state.character_presence_constraints = {w: "must_remain"}
    mgr.scene_state.offstage_characters = [w]
    mgr.scene_state.character_presence_status[w] = "temporary_offstage"

    orch: dict = {
        "scene_state": {
            "present_characters": ["Marlene_Fletcher"],
            "character_presence_constraints": {w: "must_remain"},
        }
    }

    enforce_must_remain_presence(
        st_module=None,
        get_continuity_manager_fn=lambda: mgr,
        get_must_remain_characters_fn=get_must_remain_characters,
        get_orchestration_state_fn=lambda: orch,
    )
    assert w not in orch["scene_state"]["present_characters"]


def test_issue_225_update_scene_state_v2_reentry_uses_flat_beats() -> None:
    """Symmetry: reentry evidence reads v2 flattened action (beats-only return)."""
    move = {
        "move_schema_version": 2,
        "beats": [
            {
                "type": "action",
                "action": "She walked back into the dorm room and shut the door behind her.",
            }
        ],
        "motivation": {
            "goal": "",
            "tactic": "",
            "emotional_driver": "resolve",
            "risk_level": "medium",
        },
    }
    assert not has_scene_reentry_evidence(move)
    flat = move_with_flat_text_for_deterministic_tools(move)
    assert has_scene_reentry_evidence(flat)


def test_issue_225_full_turn_beta_then_reentry_repeated_cycles() -> None:
    w, m = "Willow_Reeves", "Marlene_Fletcher"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Dorm suite",
        opening_description="Roommates.",
        present_characters=[w, m],
    )
    assert mgr.scene_state is not None
    complete_setup_seam_for_test_manager(mgr)
    ts = datetime.fromisoformat("2026-03-27T12:00:00+00:00")

    def exit_mv() -> dict:
        mv = _v2_exit_beat_move_hard(action="She left the room and shut the door.")
        mv["semantic_proposals"] = [{"kind": "off_focal", "character": w}]
        return mv

    def entry_mv() -> dict:
        return {
            "move_schema_version": 2,
            "beats": [
                {
                    "type": "action",
                    "action": (
                        "She walked back into the dorm room and shut the door behind her."
                    ),
                }
            ],
            "motivation": {
                "goal": "rejoin",
                "tactic": "return",
                "emotional_driver": "resolve",
                "risk_level": "medium",
            },
            "semantic_proposals": [{"kind": "reentry", "character": w}],
        }

    for cycle in range(2):
        mgr.process_turn(
            acting_character=w,
            move=exit_mv(),
            director_decision={
                "next_actor": m,
                "environment_event": "",
                "tension_shift": "steady",
                "reason": f"exit cycle {cycle}",
            },
            other_characters=[m],
            timestamp=ts,
        )
        assert mgr.scene_state is not None
        assert mgr.scene_state.character_presence_status.get(w) == "temporary_offstage"
        assert w not in mgr.scene_state.present_characters
        eligible = [n for n in mgr.scene_state.present_characters or []]
        avail = get_available_actors(
            participant_names=[w, m],
            used_actors=[],
            eligible_participants=eligible,
            offstage_characters=list(mgr.scene_state.offstage_characters or []),
        )
        assert w not in avail

        mgr.process_turn(
            acting_character=w,
            move=entry_mv(),
            director_decision={
                "next_actor": m,
                "environment_event": "",
                "tension_shift": "steady",
                "reason": f"reentry cycle {cycle}",
            },
            other_characters=[m],
            timestamp=ts,
        )
        assert w in mgr.scene_state.present_characters
        assert mgr.scene_state.character_presence_status.get(w) == "onstage"


def test_issue_225_audit_scenario_manifest_loads() -> None:
    raw = load_scenario("audit_i225_willow_must_remain_v2_offstage_cycles")
    assert raw["id"] == "audit_i225_willow_must_remain_v2_offstage_cycles"
    assert raw.get("beat_shift_active") is True

"""Phase 0.5 packet seam: split/merge and prompt-input bundle reconstruction."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_state_model import CharacterState
from memory_layer.retrieval import build_character_state_context_for_prompt
from prompt_derivations import build_priority_ladder, select_relationship_prompt_names
from prompt_builders import build_scene_role_prompt_context
from runtime_packets import (
    build_live_character_prompt_input_bundle,
    build_runtime_character_packet,
    build_runtime_scene_packet,
    compare_character_prompt_bundles,
    merge_scene_state_from_packets,
    reconstruct_character_prompt_input_bundle,
    split_scene_state,
)


def test_split_merge_roundtrip_preserves_scene_state() -> None:
    scene_state = {
        "location": "Lab",
        "time_of_day": "night",
        "environment_description": "Quiet",
        "scene_template_id": "tpl",
        "scene_premise": "Test premise",
        "role_assignments": {"A": "host", "B": "guest"},
        "character_presence_constraints": {"A": "must_remain", "B": ""},
        "character_authority_labels": {"A": "lead", "B": ""},
        "sleeping_surface_slots": [],
        "location_entry_slots": ["door"],
        "opening_description": "The door opens.",
        "present_characters": ["A", "B"],
        "absent_but_relevant": [],
        "offstage_characters": [],
        "character_presence_status": {},
        "phase": "opening",
        "recent_delta": "",
        "active_issue_ids": [],
        "recent_event_ids": [],
        "current_tension_level": "low",
        "recent_environment_events": [],
    }
    stable, dynamic = split_scene_state(scene_state)
    assert set(stable) | set(dynamic) == set(scene_state)
    assert not (set(stable) & set(dynamic))
    scene_packet = build_runtime_scene_packet(scene_state, None)
    proj = build_runtime_character_packet(
        scene_state=scene_state,
        char_name="A",
        user_name="Traveler",
        trigger_text="Hello",
        director_decision={"next_actor": "A"},
        session_agent_names=["A", "B"],
        recent_moves=[],
        recent_dialogue=[],
        active_issues=[],
        summary_blocks=[],
        recent_public_events=[],
        cross_session_user_memories=[],
        cross_session_world_facts=[],
        user_preferences=[],
        my_interpretations=[],
        canon_anchors=[],
        scene_grounding_section="",
    ).projection
    merged = merge_scene_state_from_packets(scene_packet, proj)
    assert merged == scene_state


def test_reconstruct_bundle_matches_coherent_live_inputs() -> None:
    scene_state = {
        "location": "Lab",
        "time_of_day": "night",
        "environment_description": "",
        "scene_template_id": "tpl",
        "scene_premise": "Premise",
        "role_assignments": {"A": "host", "B": "guest"},
        "character_presence_constraints": {"A": "", "B": ""},
        "character_authority_labels": {"A": "", "B": ""},
        "sleeping_surface_slots": [],
        "location_entry_slots": [],
        "opening_description": "Start",
        "present_characters": ["A", "B"],
        "absent_but_relevant": [],
        "offstage_characters": [],
        "character_presence_status": {},
        "phase": "opening",
        "recent_delta": "",
        "active_issue_ids": [],
        "recent_event_ids": [],
        "current_tension_level": "low",
        "recent_environment_events": [],
    }
    char_name = "A"
    state = CharacterState(name=char_name, current_objective="Observe")
    present_for_moves = scene_state.get("present_characters") or ["A", "B"]
    cast = [n for n in present_for_moves if n != char_name]
    scene_template_context = {
        "template_id": str(scene_state.get("scene_template_id", "") or ""),
        "premise": str(scene_state.get("scene_premise", "") or ""),
        "location_entry_slots": [
            str(x) for x in scene_state.get("location_entry_slots", []) if str(x or "").strip()
        ],
    }
    scene_roles = build_scene_role_prompt_context(
        scene_state,
        [char_name] + cast,
    )
    my_scene_role = next(
        (
            item
            for item in scene_roles
            if str(item.get("character", "") or "").strip() == char_name
        ),
        {},
    )
    active_issues: list[dict] = [
        {"status": "active", "description": "Watch the door"},
    ]
    actionable_statuses = {"active", "escalating", ""}
    actionable_issues = [
        i
        for i in active_issues
        if isinstance(i, dict)
        and str(i.get("status", "") or "").strip().lower() in actionable_statuses
    ]
    priority_ladder = build_priority_ladder(
        state=state,
        active_issues=actionable_issues,
    )
    rf, rs = select_relationship_prompt_names(
        char_name=char_name,
        cast=cast,
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
    )
    state_context = build_character_state_context_for_prompt(
        state=state,
        relationship_focus_names=rf,
        relationship_secondary_names=rs,
    )
    live = build_live_character_prompt_input_bundle(
        char_name=char_name,
        user_name="Traveler",
        trigger_text="Knock knock",
        director_decision={"foo": 1},
        scene_state=scene_state,
        scene_template_context=scene_template_context,
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
        recent_moves=[{"speaker": "Traveler", "kind": "speech"}],
        recent_dialogue=[{"role": "user", "content": "Hi"}],
        active_issues=active_issues,
        priority_ladder=priority_ladder,
        summary_blocks=[],
        recent_public_events=[],
        cross_session_user_memories=[],
        cross_session_world_facts=[],
        user_preferences=[],
        my_interpretations=[],
        canon_anchors=[],
        state_context=state_context,
        cast=cast,
        scene_grounding_section="GROUND",
    )
    scene_packet = build_runtime_scene_packet(scene_state, None)
    char_packet = build_runtime_character_packet(
        scene_state=scene_state,
        char_name=char_name,
        user_name="Traveler",
        trigger_text="Knock knock",
        director_decision={"foo": 1},
        session_agent_names=["A", "B"],
        recent_moves=[{"speaker": "Traveler", "kind": "speech"}],
        recent_dialogue=[{"role": "user", "content": "Hi"}],
        active_issues=active_issues,
        summary_blocks=[],
        recent_public_events=[],
        cross_session_user_memories=[],
        cross_session_world_facts=[],
        user_preferences=[],
        my_interpretations=[],
        canon_anchors=[],
        scene_grounding_section="GROUND",
    )
    recon = reconstruct_character_prompt_input_bundle(
        scene_packet,
        char_packet,
        state=state,
    )
    ok, msg = compare_character_prompt_bundles(live, recon)
    assert ok, msg


def test_compare_detects_bundle_mismatch() -> None:
    a = build_live_character_prompt_input_bundle(
        char_name="A",
        user_name="U",
        trigger_text="t",
        director_decision={},
        scene_state={"location": "X"},
        scene_template_context={"template_id": "", "premise": "", "location_entry_slots": []},
        my_scene_role={},
        scene_roles=[],
        recent_moves=[],
        recent_dialogue=[],
        active_issues=[],
        priority_ladder=[],
        summary_blocks=[],
        recent_public_events=[],
        cross_session_user_memories=[],
        cross_session_world_facts=[],
        user_preferences=[],
        my_interpretations=[],
        canon_anchors=[],
        state_context="",
        cast=[],
    )
    b = dict(a)
    b["char_name"] = "B"
    ok, _ = compare_character_prompt_bundles(a, b)
    assert not ok

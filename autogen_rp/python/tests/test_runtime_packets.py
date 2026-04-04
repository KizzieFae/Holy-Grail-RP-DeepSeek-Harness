"""Phase 0.5 packet seam: split/merge and prompt-input bundle reconstruction."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_state_model import CharacterState
from memory_layer.retrieval import build_character_state_context_for_prompt
from prompt_derivations import build_priority_ladder, select_relationship_prompt_names
from prompt_builders import build_character_turn_prompt, build_scene_role_prompt_context
from runtime_packets import (
    CharacterPromptInputAssembly,
    RetrievedContextBundle,
    RetrievedItem,
    build_live_character_prompt_input_bundle,
    build_runtime_character_packet,
    build_runtime_scene_packet,
    compare_character_prompt_bundles,
    live_bundle_from_character_prompt_assembly,
    merge_scene_state_from_packets,
    reconstruct_character_prompt_input_bundle,
    runtime_packets_from_character_prompt_assembly,
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


def _scene_state_base(**overrides: Any) -> dict[str, Any]:
    d: dict[str, Any] = {
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
    d.update(overrides)
    return d


def _assembly_from_scene_inputs(
    *,
    scene_state: dict[str, Any],
    char_name: str,
    state: CharacterState | None,
    user_name: str = "Traveler",
    trigger_text: str = "Knock knock",
    director_decision: dict[str, Any] | None = None,
    active_issues: list[dict[str, Any]] | None = None,
    recent_moves: list[dict[str, Any]] | None = None,
    recent_dialogue: list[dict[str, Any]] | None = None,
    summary_blocks: list[dict[str, Any]] | None = None,
    recent_public_events: list[dict[str, Any]] | None = None,
    my_interpretations: list[dict[str, Any]] | None = None,
    canon_anchors: list[dict[str, Any]] | None = None,
    cross_session_user_memories: list[Any] | None = None,
    cross_session_world_facts: list[Any] | None = None,
    user_preferences: list[Any] | None = None,
    retrieved_bundle: RetrievedContextBundle | None = None,
    session_agent_names: list[str] | None = None,
    scene_grounding_section: str = "",
    scene_binding_constraints_section: str = "",
    session_state: Any = None,
) -> CharacterPromptInputAssembly:
    director_decision = dict(director_decision or {})
    active_issues = list(active_issues if active_issues is not None else [])
    recent_moves = list(recent_moves if recent_moves is not None else [])
    recent_dialogue = list(recent_dialogue if recent_dialogue is not None else [])
    summary_blocks = list(summary_blocks if summary_blocks is not None else [])
    recent_public_events = list(
        recent_public_events if recent_public_events is not None else []
    )
    my_interpretations = list(
        my_interpretations if my_interpretations is not None else []
    )
    canon_anchors = list(canon_anchors if canon_anchors is not None else [])
    cross_session_user_memories = list(
        cross_session_user_memories if cross_session_user_memories is not None else []
    )
    cross_session_world_facts = list(
        cross_session_world_facts if cross_session_world_facts is not None else []
    )
    user_preferences = list(user_preferences if user_preferences is not None else [])
    retrieved_bundle = retrieved_bundle or RetrievedContextBundle()
    agents = list(
        session_agent_names
        or scene_state.get("present_characters")
        or ["A", "B"]
    )
    cast = [name for name in scene_state.get("present_characters", []) if name != char_name]
    if not cast:
        cast = [n for n in agents if n != char_name]
    scene_template_context = {
        "template_id": str(scene_state.get("scene_template_id", "") or ""),
        "premise": str(scene_state.get("scene_premise", "") or ""),
        "location_entry_slots": [
            str(item)
            for item in scene_state.get("location_entry_slots", [])
            if str(item or "").strip()
        ],
    }
    scene_roles = build_scene_role_prompt_context(scene_state, [char_name] + cast)
    my_scene_role = next(
        (
            item
            for item in scene_roles
            if str(item.get("character", "") or "").strip() == char_name
        ),
        {},
    )
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
    state_context = (
        build_character_state_context_for_prompt(
            state=state,
            relationship_focus_names=rf,
            relationship_secondary_names=rs,
        )
        if state
        else "No private state available."
    )
    return CharacterPromptInputAssembly(
        char_name=char_name,
        user_name=user_name,
        trigger_text=trigger_text,
        director_decision=director_decision,
        scene_state=scene_state,
        scene_template_context=scene_template_context,
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
        recent_moves=recent_moves,
        recent_dialogue=recent_dialogue,
        active_issues=active_issues,
        priority_ladder=priority_ladder,
        summary_blocks=summary_blocks,
        recent_public_events=recent_public_events,
        cross_session_user_memories=cross_session_user_memories,
        cross_session_world_facts=cross_session_world_facts,
        user_preferences=user_preferences,
        my_interpretations=my_interpretations,
        canon_anchors=canon_anchors,
        state_context=state_context,
        cast=cast,
        scene_grounding_section=scene_grounding_section,
        scene_binding_constraints_section=scene_binding_constraints_section,
        retrieved_bundle=retrieved_bundle,
        session_agent_names=agents,
        session_state=session_state if session_state is not None else {},
    )


def assert_assembly_bundle_parity(
    asm: CharacterPromptInputAssembly,
    state: CharacterState | None,
) -> None:
    live = live_bundle_from_character_prompt_assembly(asm)
    sp, cp = runtime_packets_from_character_prompt_assembly(asm)
    recon = reconstruct_character_prompt_input_bundle(sp, cp, state=state)
    ok, msg = compare_character_prompt_bundles(live, recon)
    assert ok, msg


@pytest.mark.parametrize(
    "scenario_id",
    [
        "baseline",
        "offstage_filtered_inputs",
        "no_present_characters_fallback_cast",
        "high_issue_pressure",
        "multi_source_retrieval_bundle",
        "four_character_cast",
        "grounding_and_binding_sections",
        "cross_session_memory_slices",
        "session_template_metadata_on_scene_packet",
        "stalled_and_active_issues_mixed",
    ],
)
def test_parity_corpus_bundle_equivalence(scenario_id: str) -> None:
    if scenario_id == "baseline":
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(),
            char_name="A",
            state=CharacterState(name="A", current_objective="Observe"),
            active_issues=[{"status": "active", "description": "Watch the door"}],
            recent_moves=[{"speaker": "Traveler", "kind": "speech"}],
            recent_dialogue=[{"role": "user", "content": "Hi"}],
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Observe"))

    elif scenario_id == "offstage_filtered_inputs":
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(
                offstage_characters=["A"],
                present_characters=["A", "B"],
            ),
            char_name="A",
            state=CharacterState(name="A", current_objective="Listen"),
            active_issues=[{"status": "active", "description": "Offstage"}],
            recent_moves=[],
            recent_dialogue=[],
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Listen"))

    elif scenario_id == "no_present_characters_fallback_cast":
        scene = _scene_state_base(present_characters=[])
        asm = _assembly_from_scene_inputs(
            scene_state=scene,
            char_name="A",
            state=CharacterState(name="A", current_objective="Wait"),
            session_agent_names=["A", "B", "C"],
            active_issues=[],
            recent_moves=[],
            recent_dialogue=[],
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Wait"))

    elif scenario_id == "high_issue_pressure":
        issues = [
            {"status": "active" if i % 3 else "stalled", "description": f"Issue {i}", "issue_id": str(i)}
            for i in range(14)
        ]
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(),
            char_name="A",
            state=CharacterState(name="A", current_objective="Endure"),
            active_issues=issues,
            recent_public_events=[{"event_id": "e1", "summary": "Public"}],
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Endure"))

    elif scenario_id == "multi_source_retrieval_bundle":
        bundle = RetrievedContextBundle(
            items=(
                RetrievedItem(
                    text="Authored line",
                    source_kind="world_lore",
                    source_ref="lore:1",
                    scope="global",
                    relevance_tags=frozenset({"tag"}),
                    priority=1,
                    non_authoritative=True,
                ),
                RetrievedItem(
                    text="Episodic-style line",
                    source_kind="episodic:public_event",
                    source_ref="e:1",
                    scope="character_local",
                    relevance_tags=frozenset(),
                    priority=2,
                    non_authoritative=True,
                ),
            )
        )
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(),
            char_name="A",
            state=CharacterState(name="A", current_objective="Recall"),
            retrieved_bundle=bundle,
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Recall"))

    elif scenario_id == "four_character_cast":
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(
                present_characters=["A", "B", "C", "D"],
                role_assignments={"A": "a", "B": "b", "C": "c", "D": "d"},
                character_presence_constraints={"A": "", "B": "", "C": "", "D": ""},
                character_authority_labels={"A": "", "B": "", "C": "", "D": ""},
            ),
            char_name="B",
            state=CharacterState(name="B", current_objective="Coordinate"),
            session_agent_names=["A", "B", "C", "D"],
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="B", current_objective="Coordinate"))

    elif scenario_id == "grounding_and_binding_sections":
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(),
            char_name="A",
            state=CharacterState(name="A", current_objective="Stay grounded"),
            scene_grounding_section="SETTLED FACTS (test): door locked.\n",
            scene_binding_constraints_section="BINDING: remain in room.\n",
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Stay grounded"))

    elif scenario_id == "cross_session_memory_slices":
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(),
            char_name="A",
            state=CharacterState(name="A", current_objective="Remember"),
            cross_session_user_memories=[{"text": "User likes tea"}],
            cross_session_world_facts=[{"text": "World fact"}],
            user_preferences=[{"text": "Quiet scenes"}],
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Remember"))

    elif scenario_id == "session_template_metadata_on_scene_packet":
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(scene_template_id="tpl_x"),
            char_name="A",
            state=CharacterState(name="A", current_objective="Open"),
            session_state={
                "selected_scene_template_id": "sidebar_tpl",
                "scene_owner": "owner1",
                "opening_mode": "default",
                "scene_initial_message_label": "L1",
                "scene_initial_message_prose": "Welcome.",
            },
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Open"))

    elif scenario_id == "stalled_and_active_issues_mixed":
        asm = _assembly_from_scene_inputs(
            scene_state=_scene_state_base(),
            char_name="A",
            state=CharacterState(name="A", current_objective="Prioritize"),
            active_issues=[
                {"status": "active", "description": "A1"},
                {"status": "stalled", "description": "S1"},
                {"status": "escalating", "description": "E1"},
                {"status": "resolved", "description": "R1"},
            ],
        )
        assert_assembly_bundle_parity(asm, CharacterState(name="A", current_objective="Prioritize"))
    else:
        raise AssertionError(f"unknown scenario {scenario_id}")


def test_parity_corpus_core_prompt_text_when_bundle_matches() -> None:
    """Optional Phase 0.5 check: deterministic prompt builder output matches on live vs recon."""
    asm = _assembly_from_scene_inputs(
        scene_state=_scene_state_base(),
        char_name="A",
        state=CharacterState(name="A", current_objective="Observe"),
        active_issues=[{"status": "active", "description": "Watch"}],
    )
    live = live_bundle_from_character_prompt_assembly(asm)
    sp, cp = runtime_packets_from_character_prompt_assembly(asm)
    recon = reconstruct_character_prompt_input_bundle(
        sp, cp, state=CharacterState(name="A", current_objective="Observe")
    )
    assert compare_character_prompt_bundles(live, recon)[0]
    t_live = build_character_turn_prompt(**live)
    t_recon = build_character_turn_prompt(**recon)
    assert t_live == t_recon


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
    asm = CharacterPromptInputAssembly(
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
        state_context=build_character_state_context_for_prompt(
            state=state,
            relationship_focus_names=rf,
            relationship_secondary_names=rs,
        ),
        cast=cast,
        scene_grounding_section="GROUND",
        scene_binding_constraints_section="",
        retrieved_bundle=RetrievedContextBundle(),
        session_agent_names=["A", "B"],
        session_state={},
    )
    assert_assembly_bundle_parity(asm, state)


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

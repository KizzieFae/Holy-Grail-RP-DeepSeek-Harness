"""Phase 1 — retrieval locked through character assembly seam (validation only, no new selector logic).

Inventory (static): The live character path builds ``RetrievedContextBundle`` only in
``prompt_retrieval_assembly.build_character_retrieved_context_bundle`` (``select_retrieved_context_bundle`` /
``merge_retrieved_context_with_episodic``), assigns it to ``CharacterPromptInputAssembly.retrieved_bundle``,
and derives ``retrieved_context_section`` solely via ``live_bundle_from_character_prompt_assembly`` →
``format_retrieved_context_for_prompt(asm.retrieved_bundle)``. No alternate formatting path for the
character prompt kwargs was found.

Golden snapshots below detect silent drift in bundle composition (refs, kinds, scopes, text).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from character_state_model import CharacterState
from prompt_builders import build_scene_role_prompt_context
from prompt_derivations import build_priority_ladder, select_relationship_prompt_names
from memory_layer.retrieval import build_character_state_context_for_prompt
from retrieved_context_select import load_authored_retrieval_index, select_retrieved_context_bundle
from runtime_packets import (
    CharacterPromptInputAssembly,
    RetrievedContextBundle,
    RetrievedItem,
    format_retrieved_context_for_prompt,
    live_bundle_from_character_prompt_assembly,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "retrieved_context_index_test.json"

_LORE_LONG = (
    "LORE_LONG_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
)


def _index():
    idx = load_authored_retrieval_index(str(FIXTURE))
    assert idx is not None
    return idx


def _item_signature(it: RetrievedItem) -> tuple:
    return (
        it.source_ref,
        it.source_kind,
        it.scope,
        it.priority,
        it.text,
        it.from_other_character,
    )


def test_phase1_assembly_invariant_section_is_pure_format_of_bundle() -> None:
    """``retrieved_context_section`` must equal ``format_retrieved_context_for_prompt(bundle)`` only."""
    bundle = RetrievedContextBundle(
        items=(
            RetrievedItem(
                text="Line one.",
                source_kind="world_lore",
                source_ref="snap:1",
                scope="world_lore",
                relevance_tags=frozenset(),
                priority=10,
                non_authoritative=True,
                from_other_character=None,
            ),
        )
    )
    scene_state = {
        "location": "L",
        "time_of_day": "d",
        "environment_description": "",
        "scene_template_id": "t",
        "scene_premise": "p",
        "role_assignments": {},
        "character_presence_constraints": {},
        "character_authority_labels": {},
        "sleeping_surface_slots": [],
        "location_entry_slots": [],
        "opening_description": "",
        "present_characters": ["A"],
        "absent_but_relevant": [],
        "offstage_characters": [],
        "character_presence_status": {},
        "phase": "x",
        "recent_delta": "",
        "active_issue_ids": [],
        "recent_event_ids": [],
        "current_tension_level": "low",
        "recent_environment_events": [],
    }
    char_name = "A"
    cast: list[str] = []
    scene_roles = build_scene_role_prompt_context(scene_state, [char_name])
    my_scene_role = next(
        (x for x in scene_roles if str(x.get("character", "")).strip() == char_name),
        {},
    )
    rf, rs = select_relationship_prompt_names(
        char_name=char_name,
        cast=cast,
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
    )
    state = CharacterState(name=char_name, current_objective="o")
    state_context = build_character_state_context_for_prompt(
        state=state,
        relationship_focus_names=rf,
        relationship_secondary_names=rs,
    )
    asm = CharacterPromptInputAssembly(
        char_name=char_name,
        user_name="U",
        trigger_text="t",
        director_decision={},
        scene_state=scene_state,
        scene_template_context={"template_id": "t", "premise": "p", "location_entry_slots": []},
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
        recent_moves=[],
        recent_dialogue=[],
        active_issues=[],
        priority_ladder=build_priority_ladder(state=state, active_issues=[]),
        summary_blocks=[],
        recent_public_events=[],
        cross_session_user_memories=[],
        cross_session_world_facts=[],
        user_preferences=[],
        my_interpretations=[],
        canon_anchors=[],
        state_context=state_context,
        cast=cast,
        scene_grounding_section="",
        scene_binding_constraints_section="",
        retrieved_bundle=bundle,
        session_agent_names=["A"],
        session_state={},
    )
    kwargs = live_bundle_from_character_prompt_assembly(asm)
    assert kwargs["retrieved_context_section"] == format_retrieved_context_for_prompt(bundle)
    assert kwargs["retrieved_context_section"] == format_retrieved_context_for_prompt(
        asm.retrieved_bundle
    )


def test_phase1_bundle_composition_golden_select_A_tpl1_with_relationship() -> None:
    """Snapshot: change selector ordering/caps/dedup → update intentionally or fix regression."""
    idx = _index()
    bundle = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=("B",),
        cast=("B",),
        dedup_against_texts=(),
    )
    signatures = tuple(_item_signature(it) for it in bundle.items)
    expected = (
        (
            "tpl1:atmosphere",
            "scene_template",
            "scene_shared",
            20,
            "Template atmosphere for tpl1.",
            None,
        ),
        (
            "setup:tpl1",
            "setup_note",
            "scene_shared",
            5,
            "Setup note for tpl1.",
            None,
        ),
        (
            "lore:fixture:long_trunc",
            "lore",
            "world_lore",
            16,
            _LORE_LONG,
            None,
        ),
        (
            "A:dup_hash",
            "character_card",
            "character_local",
            99,
            "Same text hash target.",
            None,
        ),
        (
            "A:self",
            "character_card",
            "character_local",
            10,
            "Self voice line for A.",
            None,
        ),
        (
            "B:rel",
            "character_card",
            "character_local",
            50,
            "Relationship blurb about A.",
            "B",
        ),
    )
    assert signatures == expected

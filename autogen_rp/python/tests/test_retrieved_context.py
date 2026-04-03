"""Phase 2 authored retrieval: selector, caps, dedup, determinism."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from retrieved_context_select import load_authored_retrieval_index, select_retrieved_context_bundle
from runtime_packets import (
    RetrievedContextBundle,
    RetrievedItem,
    build_live_character_prompt_input_bundle,
    build_runtime_character_packet,
    build_runtime_scene_packet,
    compare_character_prompt_bundles,
    format_retrieved_context_for_prompt,
    reconstruct_character_prompt_input_bundle,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "retrieved_context_index_test.json"


def _index() -> object:
    idx = load_authored_retrieval_index(str(FIXTURE))
    assert idx is not None
    return idx


def test_select_determinism() -> None:
    idx = _index()
    kwargs = dict(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=("B",),
        cast=("B",),
        dedup_against_texts=(),
    )
    a = select_retrieved_context_bundle(**kwargs)
    b = select_retrieved_context_bundle(**kwargs)
    assert a.items == b.items


def test_relationship_only_tagged_and_one_per_other() -> None:
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=("B",),
        cast=("B",),
        dedup_against_texts=(),
    )
    refs = [i.source_ref for i in b.items]
    assert "B:rel" in refs
    assert "B:general" not in refs
    assert refs.count("B:rel") == 1


def test_no_cross_character_without_relationship_focus() -> None:
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=(),
        cast=("B",),
        dedup_against_texts=(),
    )
    assert all(x.from_other_character is None for x in b.items)


def test_dedup_text_hash() -> None:
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
    )
    dup = RetrievedItem(
        text="Same text hash target.",
        source_kind="character_card",
        source_ref="other:ref",
        scope="character_local",
        relevance_tags=frozenset(),
        priority=100,
        non_authoritative=True,
        from_other_character=None,
    )
    from retrieved_context_select import _dedupe_items

    items = [
        RetrievedItem(
            text="Same text hash target.",
            source_kind="character_card",
            source_ref="first",
            scope="character_local",
            relevance_tags=frozenset(),
            priority=1,
            non_authoritative=True,
        ),
        dup,
    ]
    out = _dedupe_items(items)
    assert len(out) == 1
    assert out[0].source_ref == "first"


def test_dedup_against_premise() -> None:
    idx = _index()
    premise = "Template atmosphere for tpl1."
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(premise,),
    )
    refs = [i.source_ref for i in b.items]
    assert "tpl1:atmosphere" not in refs


def test_cap_drops_cross_before_self(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("retrieved_context_select.MAX_RETRIEVED_ITEMS", 2)
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=("B",),
        cast=("B",),
        dedup_against_texts=(),
    )
    assert len(b.items) == 2
    refs = {i.source_ref for i in b.items}
    assert "B:rel" not in refs


def test_format_non_authoritative_contract() -> None:
    b = RetrievedContextBundle(
        items=(
            RetrievedItem(
                text="Hello",
                source_kind="character_card",
                source_ref="x:1",
                scope="character_local",
                relevance_tags=frozenset(),
                priority=1,
                non_authoritative=True,
            ),
        )
    )
    s = format_retrieved_context_for_prompt(b)
    assert "NON-AUTHORITATIVE" in s
    assert "canon anchors" in s.lower()
    assert "continuity" in s.lower()
    assert "scene facts" in s.lower()
    assert "[x:1 | character_card]" in s


def test_shadow_bundle_parity_with_retrieved() -> None:
    from character_state_model import CharacterState

    scene_state = {
        "location": "Lab",
        "time_of_day": "night",
        "environment_description": "",
        "scene_template_id": "tpl1",
        "scene_premise": "P",
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
    idx = _index()
    bundle = select_retrieved_context_bundle(
        index=idx,
        char_name=char_name,
        scene_template_id="tpl1",
        relationship_focus_names=("B",),
        cast=("B",),
        dedup_against_texts=("P", "Start"),
    )
    section = format_retrieved_context_for_prompt(bundle)
    cast = ["B"]
    from prompt_builders import build_scene_role_prompt_context
    from prompt_derivations import (
        build_priority_ladder,
        select_relationship_prompt_names,
    )
    from memory_layer.retrieval import build_character_state_context_for_prompt

    scene_template_context = {
        "template_id": "tpl1",
        "premise": "P",
        "location_entry_slots": [],
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
    active_issues: list[dict] = []
    priority_ladder = build_priority_ladder(state=state, active_issues=active_issues)
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
        trigger_text="Hi",
        director_decision={},
        scene_state=scene_state,
        scene_template_context=scene_template_context,
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
        recent_moves=[],
        recent_dialogue=[],
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
        scene_grounding_section="",
        retrieved_context_section=section,
    )
    scene_packet = build_runtime_scene_packet(scene_state, None)
    char_packet = build_runtime_character_packet(
        scene_state=scene_state,
        char_name=char_name,
        user_name="Traveler",
        trigger_text="Hi",
        director_decision={},
        session_agent_names=["A", "B"],
        recent_moves=[],
        recent_dialogue=[],
        active_issues=active_issues,
        summary_blocks=[],
        recent_public_events=[],
        cross_session_user_memories=[],
        cross_session_world_facts=[],
        user_preferences=[],
        my_interpretations=[],
        canon_anchors=[],
        scene_grounding_section="",
        retrieved=bundle,
    )
    recon = reconstruct_character_prompt_input_bundle(
        scene_packet,
        char_packet,
        state=state,
    )
    ok, msg = compare_character_prompt_bundles(live, recon)
    assert ok, msg


def test_empty_index_path_returns_none() -> None:
    assert load_authored_retrieval_index(None) is None
    assert load_authored_retrieval_index("") is None


def test_primary_lane_ordering_tpl_setup_lore_self_cross() -> None:
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=("B",),
        cast=("B",),
        dedup_against_texts=(),
    )
    refs = [i.source_ref for i in b.items]
    assert refs == [
        "tpl1:atmosphere",
        "setup:tpl1",
        "lore:fixture:long_trunc",
        "A:dup_hash",
        "A:self",
        "B:rel",
    ]


def test_lore_excluded_when_template_mismatch() -> None:
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
    )
    refs = [i.source_ref for i in b.items]
    assert "lore:fixture:other_template" not in refs


def test_lore_subcap_keeps_highest_priority() -> None:
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
    )
    lore_refs = [i.source_ref for i in b.items if i.source_kind == "lore"]
    assert lore_refs == ["lore:fixture:long_trunc"]


def test_lore_truncated_at_selection_not_compile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("retrieved_context_select.MAX_KIND_LORE_CHARS", 40)
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
    )
    lore = next(i for i in b.items if i.source_kind == "lore")
    assert len(lore.text) <= 40
    assert lore.text.endswith("…")


def test_character_non_local_scope_excluded_from_self_lane() -> None:
    idx = _index()
    b = select_retrieved_context_bundle(
        index=idx,
        char_name="A",
        scene_template_id="tpl1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
    )
    assert "A:wrong_scope" not in [i.source_ref for i in b.items]

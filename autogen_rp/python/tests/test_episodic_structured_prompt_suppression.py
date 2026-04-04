"""ID-keyed suppression: episodic merge drops rows already in structured prompt sections."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from episodic_memory_compile import EpisodicCompiledItem, EpisodicOriginType
from retrieved_context_select import (
    filter_episodic_items_by_structured_prompt_overlap,
    merge_retrieved_context_with_episodic,
    structured_prompt_id_sets_for_episodic_suppression,
)


def _item(
    *,
    source_ref: str,
    memory_type: str,
    origin_type: str,
    summary: str = "body",
    sal: int = 50,
) -> EpisodicCompiledItem:
    return EpisodicCompiledItem(
        memory_id=f"m-{source_ref}",
        origin_type=cast(EpisodicOriginType, origin_type),
        source_ref=source_ref,
        memory_type=memory_type,
        visible_to=frozenset({"Alice"}),
        involved_characters=("Alice",),
        summary_text=summary,
        salience=sal,
        recency_key=1,
        non_authoritative=True,
    )


def test_issue_suppressed_when_id_in_active_issues():
    ep = _item(source_ref="iss_x", memory_type="issue", origin_type="issue")
    out = filter_episodic_items_by_structured_prompt_overlap(
        (ep,),
        prompt_issue_ids=frozenset({"iss_x"}),
        prompt_public_event_ids=frozenset(),
        prompt_interpretation_ids=frozenset(),
    )
    assert out == ()


def test_public_event_suppressed_when_id_in_recent_public_events():
    ep = _item(source_ref="evt_x", memory_type="public_event", origin_type="event")
    out = filter_episodic_items_by_structured_prompt_overlap(
        (ep,),
        prompt_issue_ids=frozenset(),
        prompt_public_event_ids=frozenset({"evt_x"}),
        prompt_interpretation_ids=frozenset(),
    )
    assert out == ()


def test_interpretation_suppressed_when_id_in_my_interpretations():
    ep = _item(source_ref="int_x", memory_type="interpretation", origin_type="interpretation")
    out = filter_episodic_items_by_structured_prompt_overlap(
        (ep,),
        prompt_issue_ids=frozenset(),
        prompt_public_event_ids=frozenset(),
        prompt_interpretation_ids=frozenset({"int_x"}),
    )
    assert out == ()


def test_no_suppression_when_id_absent_from_structured_sets():
    ep = _item(source_ref="evt_keep", memory_type="public_event", origin_type="event")
    out = filter_episodic_items_by_structured_prompt_overlap(
        (ep,),
        prompt_issue_ids=frozenset({"other_issue"}),
        prompt_public_event_ids=frozenset({"other_evt"}),
        prompt_interpretation_ids=frozenset({"other_int"}),
    )
    assert out == (ep,)


def test_character_scoping_event_not_suppressed_when_not_in_prompt_event_list():
    """Simulate: event exists in continuity globally but serialized prompt list omits its id."""
    ep = _item(source_ref="evt_global", memory_type="public_event", origin_type="event")
    sets = structured_prompt_id_sets_for_episodic_suppression(
        active_issues=[],
        recent_public_events=[{"summary": "seen but no event_id key"}],
        my_interpretations=[],
    )
    out = filter_episodic_items_by_structured_prompt_overlap(
        (ep,),
        prompt_issue_ids=sets[0],
        prompt_public_event_ids=sets[1],
        prompt_interpretation_ids=sets[2],
    )
    assert out == (ep,)


def test_structured_prompt_id_sets_extract_from_dict_rows():
    i, e, n = structured_prompt_id_sets_for_episodic_suppression(
        active_issues=[{"issue_id": " i1 ", "description": "d"}],
        recent_public_events=[{"event_id": "e1", "summary": "s"}],
        my_interpretations=[{"interpretation_id": "n1", "interpretation": "x"}],
    )
    assert i == frozenset({"i1"})
    assert e == frozenset({"e1"})
    assert n == frozenset({"n1"})


def test_merge_drops_episodic_public_event_when_id_in_structured_events():
    bundle = merge_retrieved_context_with_episodic(
        index=None,
        char_name="Alice",
        scene_template_id="",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
        episodic_items=(
            _item(source_ref="evt_dup", memory_type="public_event", origin_type="event", summary="dup line"),
        ),
        structured_prompt_public_event_ids=frozenset({"evt_dup"}),
    )
    assert bundle.items == ()

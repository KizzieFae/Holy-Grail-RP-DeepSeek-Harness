"""Phase 3.2 step 5: authored + episodic merge and global cap (deterministic)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from episodic_memory_compile import EpisodicCompiledItem
from retrieved_context_select import (
    AuthoredIndexChunk,
    AuthoredRetrievalIndex,
    episodic_compiled_to_retrieved_item,
    merge_retrieved_context_with_episodic,
)


def _chunk(
    *,
    ref: str,
    text: str,
    pri: int,
    kind: str = "scene_template",
    template_id: str = "t1",
) -> AuthoredIndexChunk:
    return AuthoredIndexChunk(
        source_ref=ref,
        text=text,
        priority=pri,
        source_kind=kind,
        scope="scene",
        relevance_tags=frozenset(),
        relationship_relevant=False,
        template_id=template_id,
    )


def _index_t1(*chunks: AuthoredIndexChunk) -> AuthoredRetrievalIndex:
    return AuthoredRetrievalIndex(
        version=1,
        schema_version=1,
        characters={},
        templates={"t1": tuple(chunks)},
        setup_notes=(),
        lore=(),
    )


def _ep(
    *,
    sid: str,
    summary: str,
    sal: int,
    mem: str = "public_event",
) -> EpisodicCompiledItem:
    return EpisodicCompiledItem(
        memory_id=f"m-{sid}",
        origin_type="event",
        source_ref=sid,
        memory_type=mem,
        visible_to=frozenset({"Alice"}),
        involved_characters=("Alice",),
        summary_text=summary,
        salience=sal,
        recency_key=1,
        non_authoritative=True,
    )


def test_merge_global_cap_tie_priority_drops_episodic_first():
    idx = _index_t1(_chunk(ref="auth_a", text="authored body", pri=50))
    ep = _ep(sid="e1", summary="episodic body", sal=50)
    with patch("retrieved_context_select.MAX_RETRIEVED_ITEMS", 1):
        bundle = merge_retrieved_context_with_episodic(
            index=idx,
            char_name="Alice",
            scene_template_id="t1",
            relationship_focus_names=(),
            cast=(),
            dedup_against_texts=(),
            episodic_items=(ep,),
        )
    assert len(bundle.items) == 1
    assert bundle.items[0].source_ref == "auth_a"
    assert not bundle.items[0].source_kind.startswith("episodic")


def test_merge_global_cap_drops_lower_priority_authored_before_higher_episodic():
    idx = _index_t1(_chunk(ref="low_auth", text="weak", pri=10))
    ep = _ep(sid="e_hi", summary="strong episodic", sal=80)
    with patch("retrieved_context_select.MAX_RETRIEVED_ITEMS", 1):
        bundle = merge_retrieved_context_with_episodic(
            index=idx,
            char_name="Alice",
            scene_template_id="t1",
            relationship_focus_names=(),
            cast=(),
            dedup_against_texts=(),
            episodic_items=(ep,),
        )
    assert len(bundle.items) == 1
    assert bundle.items[0].source_ref == "e_hi"


def test_merge_substring_dedupe_drops_episodic_on_priority_tie_with_authored():
    idx = _index_t1(
        _chunk(ref="auth_wrap", text="Before TOKEN After", pri=40),
    )
    ep = _ep(sid="e_sub", summary="TOKEN", sal=40)
    bundle = merge_retrieved_context_with_episodic(
        index=idx,
        char_name="Alice",
        scene_template_id="t1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
        episodic_items=(ep,),
    )
    refs = {it.source_ref for it in bundle.items}
    assert "auth_wrap" in refs
    assert "e_sub" not in refs


def test_episodic_compiled_to_retrieved_item_source_kind():
    it = episodic_compiled_to_retrieved_item(
        _ep(sid="x", summary="s", sal=33),
    )
    assert it.source_kind == "episodic:public_event"
    assert it.priority == 33
    assert it.scope == "session_episodic"


def test_merge_order_authored_segment_before_episodic_no_cap():
    idx = _index_t1(_chunk(ref="a1", text="first authored", pri=100))
    ep = _ep(sid="e1", summary="second episodic", sal=20)
    bundle = merge_retrieved_context_with_episodic(
        index=idx,
        char_name="Alice",
        scene_template_id="t1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
        episodic_items=(ep,),
    )
    refs = [it.source_ref for it in bundle.items]
    assert refs.index("a1") < refs.index("e1")


def test_phase1_merge_bundle_composition_snapshot_stable():
    """Golden snapshot for authored+episodic merge (detect silent selector/merge drift)."""
    idx = _index_t1(_chunk(ref="a1", text="first authored", pri=100))
    ep = _ep(sid="e1", summary="second episodic", sal=20)
    bundle = merge_retrieved_context_with_episodic(
        index=idx,
        char_name="Alice",
        scene_template_id="t1",
        relationship_focus_names=(),
        cast=(),
        dedup_against_texts=(),
        episodic_items=(ep,),
    )
    assert [(it.source_ref, it.source_kind, it.scope, it.priority, it.text) for it in bundle.items] == [
        ("a1", "scene_template", "scene", 100, "first authored"),
        ("e1", "episodic:public_event", "session_episodic", 20, "second episodic"),
    ]

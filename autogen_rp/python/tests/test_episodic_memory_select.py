"""Tests for episodic_memory_select (Phase 3.2 step 3)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from episodic_memory_compile import EpisodicCompiledItem
from episodic_memory_select import (
    DEFAULT_MAX_EPISODIC_CHARS,
    DEFAULT_MAX_EPISODIC_ITEMS,
    select_episodic_items_for_character,
)


def _item(
    *,
    sid: str,
    summary: str,
    visible: frozenset[str],
    salience: int = 50,
    rk: int = 1,
    origin: str = "event",
) -> EpisodicCompiledItem:
    return EpisodicCompiledItem(
        memory_id=f"id-{sid}",
        origin_type=origin,  # type: ignore[arg-type]
        source_ref=sid,
        memory_type="public_event",
        visible_to=visible,
        involved_characters=tuple(sorted(visible)),
        summary_text=summary,
        salience=salience,
        recency_key=rk,
        non_authoritative=True,
    )


def test_visibility_alice_only():
    pool = (
        _item(sid="e1", summary="A", visible=frozenset({"Alice"})),
        _item(sid="e2", summary="B", visible=frozenset({"Bob"})),
    )
    a = select_episodic_items_for_character(pool, "Alice", max_items=10, max_chars=9999)
    b = select_episodic_items_for_character(pool, "Bob", max_items=10, max_chars=9999)
    assert [x.source_ref for x in a] == ["e1"]
    assert [x.source_ref for x in b] == ["e2"]


def test_shared_event_both_see():
    pool = (_item(sid="e1", summary="Public", visible=frozenset({"Alice", "Bob"})),)
    a = select_episodic_items_for_character(pool, "Alice", max_items=10, max_chars=9999)
    b = select_episodic_items_for_character(pool, "Bob", max_items=10, max_chars=9999)
    assert len(a) == 1 and len(b) == 1
    assert a[0].source_ref == b[0].source_ref == "e1"


def test_viewer_name_is_stripped_for_membership():
    pool = (_item(sid="e1", summary="x", visible=frozenset({"Alice"})),)
    assert len(select_episodic_items_for_character(pool, "Alice ", max_items=10, max_chars=99)) == 1
    assert len(select_episodic_items_for_character(pool, "Alice", max_items=10, max_chars=99)) == 1


def test_empty_char_name_returns_empty():
    pool = (_item(sid="e1", summary="x", visible=frozenset({"Alice"})),)
    assert select_episodic_items_for_character(pool, "", max_items=10, max_chars=99) == ()
    assert select_episodic_items_for_character(pool, "   ", max_items=10, max_chars=99) == ()


def test_ordering_preserves_pool_order_among_visible():
    pool = (
        _item(sid="high", summary="a", visible=frozenset({"Alice"}), salience=90, rk=3),
        _item(sid="mid", summary="b", visible=frozenset({"Alice"}), salience=50, rk=2),
        _item(sid="low", summary="c", visible=frozenset({"Alice"}), salience=10, rk=1),
    )
    got = select_episodic_items_for_character(pool, "Alice", max_items=10, max_chars=9999)
    assert [x.source_ref for x in got] == ["high", "mid", "low"]


def test_max_items_trims_suffix():
    pool = (
        _item(sid="a", summary="1", visible=frozenset({"Alice"})),
        _item(sid="b", summary="2", visible=frozenset({"Alice"})),
        _item(sid="c", summary="3", visible=frozenset({"Alice"})),
    )
    got = select_episodic_items_for_character(pool, "Alice", max_items=2, max_chars=9999)
    assert [x.source_ref for x in got] == ["a", "b"]


def test_max_chars_stops_at_prefix():
    pool = (
        _item(sid="a", summary="aaa", visible=frozenset({"Alice"})),
        _item(sid="b", summary="bbb", visible=frozenset({"Alice"})),
    )
    got = select_episodic_items_for_character(pool, "Alice", max_items=10, max_chars=4)
    assert [x.source_ref for x in got] == ["a"]


def test_oversize_item_skipped_continues():
    pool = (
        _item(sid="huge", summary="x" * 100, visible=frozenset({"Alice"})),
        _item(sid="ok", summary="hi", visible=frozenset({"Alice"})),
    )
    got = select_episodic_items_for_character(pool, "Alice", max_items=10, max_chars=50)
    assert [x.source_ref for x in got] == ["ok"]


def test_zero_cap_returns_empty():
    pool = (_item(sid="a", summary="x", visible=frozenset({"Alice"})),)
    assert select_episodic_items_for_character(pool, "Alice", max_items=0, max_chars=99) == ()
    assert select_episodic_items_for_character(pool, "Alice", max_items=5, max_chars=0) == ()


def test_default_constants_are_positive():
    assert DEFAULT_MAX_EPISODIC_ITEMS > 0
    assert DEFAULT_MAX_EPISODIC_CHARS > 0

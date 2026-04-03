"""Tests for episodic_memory_cache (Phase 3.2 step 2)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_state import IssueState, IssueStatus, PublicEvent
from episodic_memory_cache import (
    EPISODIC_CANDIDATE_CACHE_STATE_KEY,
    build_episodic_snapshot_payload,
    clear_episodic_pool_cache,
    compute_episodic_snapshot_key,
    get_or_compile_episodic_candidate_pool,
)


def _dt() -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _sample_event(*, eid: str = "e1", summary: str = "Hello") -> PublicEvent:
    return PublicEvent(
        event_id=eid,
        timestamp=_dt(),
        event_type="action",
        participants=["Bob", "Alice"],
        summary=summary,
        turn_index=2,
        significance="minor",
        known_by=["Alice", "Bob"],
    )


def test_snapshot_key_stable_under_collection_order():
    a = _sample_event()
    b = _sample_event(eid="e2", summary="Other")
    k1 = compute_episodic_snapshot_key(
        public_events=(a, b),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    k2 = compute_episodic_snapshot_key(
        public_events=(b, a),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert k1 == k2


def test_snapshot_key_changes_when_compile_relevant_field_changes():
    ev1 = _sample_event(summary="A")
    ev2 = _sample_event(summary="B")
    k1 = compute_episodic_snapshot_key(
        public_events=(ev1,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    k2 = compute_episodic_snapshot_key(
        public_events=(ev2,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert k1 != k2


def test_snapshot_key_changes_when_issue_status_changes():
    i1 = IssueState(
        issue_id="i1",
        description="Pressure",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=_dt(),
    )
    i2 = IssueState(
        issue_id="i1",
        description="Pressure",
        participants=["Alice"],
        status=IssueStatus.RESOLVED,
        created_at=_dt(),
    )
    k1 = compute_episodic_snapshot_key(
        public_events=(), interpretations=(), issues=(i1,), canon_anchors=()
    )
    k2 = compute_episodic_snapshot_key(
        public_events=(), interpretations=(), issues=(i2,), canon_anchors=()
    )
    assert k1 != k2


def test_build_episodic_snapshot_payload_sort_keys():
    p = build_episodic_snapshot_payload(
        public_events=(_sample_event(),),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert list(p.keys()) == sorted(p.keys())
    assert p["events"][0]["known_by"] == ["Alice", "Bob"]


def test_get_or_compile_cache_hit_same_object():
    session: dict = {}
    ev = _sample_event()
    p1 = get_or_compile_episodic_candidate_pool(
        session,
        public_events=(ev,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    p2 = get_or_compile_episodic_candidate_pool(
        session,
        public_events=(ev,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert p1 is p2
    assert EPISODIC_CANDIDATE_CACHE_STATE_KEY in session


def test_get_or_compile_cache_miss_when_continuity_changes():
    session: dict = {}
    ev_a = _sample_event(summary="First")
    p1 = get_or_compile_episodic_candidate_pool(
        session,
        public_events=(ev_a,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    ev_b = _sample_event(summary="Second")
    p2 = get_or_compile_episodic_candidate_pool(
        session,
        public_events=(ev_b,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert p1 is not p2
    assert p1 != p2


def test_clear_episodic_pool_cache():
    session: dict = {}
    get_or_compile_episodic_candidate_pool(
        session,
        public_events=(_sample_event(),),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    clear_episodic_pool_cache(session)
    assert EPISODIC_CANDIDATE_CACHE_STATE_KEY not in session

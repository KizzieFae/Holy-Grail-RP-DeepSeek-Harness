"""Tests for episodic_memory_compile (Phase 3.2 step 1)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    IssueState,
    IssueStatus,
    PublicEvent,
)
from episodic_memory_compile import EpisodicCompiledItem, compile_episodic_candidates


def _dt() -> datetime:
    return datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_empty_inputs_yield_empty_tuple():
    assert compile_episodic_candidates(
        public_events=(),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    ) == ()


def test_public_event_known_by_and_template():
    ev = PublicEvent(
        event_id="e1",
        timestamp=_dt(),
        event_type="action",
        participants=["Alice", "Bob"],
        summary="They agreed to meet later.",
        turn_index=3,
        significance="major",
        known_by=["Alice", "Bob"],
    )
    pool = compile_episodic_candidates(
        public_events=(ev,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert len(pool) == 1
    it = pool[0]
    assert it.origin_type == "event"
    assert it.source_ref == "e1"
    assert it.visible_to == frozenset({"Alice", "Bob"})
    assert "Public event (action, major):" in it.summary_text
    assert "They agreed to meet later." in it.summary_text
    assert it.salience == 40
    assert it.non_authoritative is True


def test_public_event_skipped_when_canon_impact_nonempty():
    ev = PublicEvent(
        event_id="e2",
        timestamp=_dt(),
        event_type="revelation",
        participants=["Alice"],
        summary="Secret revealed.",
        known_by=["Alice"],
        canon_impact=["anchor_a"],
    )
    pool = compile_episodic_candidates(
        public_events=(ev,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert pool == ()


def test_public_event_skipped_when_known_by_empty():
    ev = PublicEvent(
        event_id="e3",
        timestamp=_dt(),
        event_type="action",
        participants=["Alice"],
        summary="Nobody knows yet.",
        known_by=[],
    )
    pool = compile_episodic_candidates(
        public_events=(ev,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert pool == ()


def test_interpretation_owner_visibility_only():
    interp = CharacterInterpretation(
        interpretation_id="i1",
        character_name="Alice",
        subject_type="event",
        subject_id="e1",
        interpretation="She thinks it was deliberate.",
        emotional_reaction="suspicious",
        formed_at=_dt(),
        confidence="confident",
    )
    pool = compile_episodic_candidates(
        public_events=(),
        interpretations=(interp,),
        issues=(),
        canon_anchors=(),
    )
    assert len(pool) == 1
    assert pool[0].visible_to == frozenset({"Alice"})
    assert pool[0].origin_type == "interpretation"
    assert "Interpretation (event e1):" in pool[0].summary_text


def test_interpretation_skipped_without_character_name():
    interp = CharacterInterpretation(
        interpretation_id="i2",
        character_name="",
        subject_type="event",
        subject_id="e1",
        interpretation="orphan",
        emotional_reaction="neutral",
        formed_at=_dt(),
    )
    pool = compile_episodic_candidates(
        public_events=(),
        interpretations=(interp,),
        issues=(),
        canon_anchors=(),
    )
    assert pool == ()


def test_issue_participants_and_blocked_visibility():
    issue = IssueState(
        issue_id="iss1",
        description="The debt must be settled.",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=_dt(),
        blocked_characters=["Bob"],
        last_turn_index=5,
    )
    pool = compile_episodic_candidates(
        public_events=(),
        interpretations=(),
        issues=(issue,),
        canon_anchors=(),
    )
    assert len(pool) == 1
    assert pool[0].visible_to == frozenset({"Alice", "Bob"})
    assert "Issue iss1 (active):" in pool[0].summary_text


def test_issue_skipped_when_no_participants_or_blocked():
    issue = IssueState(
        issue_id="iss2",
        description="Floating issue",
        participants=[],
        status=IssueStatus.ACTIVE,
        created_at=_dt(),
        blocked_characters=[],
    )
    pool = compile_episodic_candidates(
        public_events=(),
        interpretations=(),
        issues=(issue,),
        canon_anchors=(),
    )
    assert pool == ()


def test_anchor_character_trait_visibility():
    anchor = CanonAnchor(
        anchor_id="a1",
        category="character_trait",
        subject="Alice",
        statement="Alice is claustrophobic.",
        source="scene_1",
        established_at=_dt(),
    )
    pool = compile_episodic_candidates(
        public_events=(),
        interpretations=(),
        issues=(),
        canon_anchors=(anchor,),
    )
    assert len(pool) == 1
    assert pool[0].visible_to == frozenset({"Alice"})
    assert pool[0].origin_type == "anchor"
    assert "Canon (character_trait):" in pool[0].summary_text


def test_anchor_world_fact_excluded_unresolved_visibility():
    anchor = CanonAnchor(
        anchor_id="a2",
        category="world_fact",
        subject="The city",
        statement="It always rains.",
        source="lore",
        established_at=_dt(),
    )
    pool = compile_episodic_candidates(
        public_events=(),
        interpretations=(),
        issues=(),
        canon_anchors=(anchor,),
    )
    assert pool == ()


def test_determinism_same_inputs_same_pool():
    ev = PublicEvent(
        event_id="e10",
        timestamp=_dt(),
        event_type="action",
        participants=["Zed"],
        summary="Zed acted.",
        turn_index=1,
        known_by=["Zed"],
    )
    a = compile_episodic_candidates(
        public_events=(ev,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    b = compile_episodic_candidates(
        public_events=(ev,),
        interpretations=(),
        issues=(),
        canon_anchors=(),
    )
    assert a == b
    assert all(isinstance(x, EpisodicCompiledItem) for x in a)

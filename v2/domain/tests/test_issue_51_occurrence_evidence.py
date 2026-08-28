"""Issue #51 — bounded occurrence evidence on promoted PublicEvents."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_event_promotion_policy import compute_event_promotion_policy_fields  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402
from continuity_state import ConsequenceCategory, DetectedConsequence, PublicEvent  # noqa: E402
from continuity_state_occurrence_evidence import (  # noqa: E402
    OccurrenceEvidence,
    globally_embeddable_occurrence_text,
    parse_occurrence_evidence,
)
from continuity_consequence_phrase_maps import category_state_change_phrases  # noqa: E402
from domain_api.story_knowledge_projection import project_occurrence_from_public_event  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from perception_audibility_constants import AUDIBILITY_PRIVATE  # noqa: E402


def _det(cat: ConsequenceCategory) -> DetectedConsequence:
    return DetectedConsequence(
        category=cat,
        confidence="strong",
        source_fields=["action"],
        excerpt="x",
    )


def _motivation(**kwargs: str) -> dict:
    base = {
        "goal": "test",
        "tactic": "test",
        "emotional_driver": "calm",
        "risk_level": "low",
    }
    base.update(kwargs)
    return base


def _fresh_manager() -> ContinuityManager:
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Room",
        opening_description="open",
        present_characters=["Alice", "Bob"],
    )
    complete_setup_seam_for_test_manager(mgr, cast=["Alice", "Bob"])
    return mgr


def test_summary_prefers_move_specific_physical_action_over_template() -> None:
    move = {
        "action": "placed the gun on the table",
        "dialogue": "",
        "motivation": _motivation(),
    }
    templates = category_state_change_phrases("Alice")
    state_changes = [templates[ConsequenceCategory.PHYSICAL_STATE_SET]]
    promo = compute_event_promotion_policy_fields(
        acting_character="Alice",
        move=move,
        director_decision={},
        detected=[_det(ConsequenceCategory.PHYSICAL_STATE_SET)],
        state_changes=state_changes,
        actionable_implications=[],
    )
    assert "placed the gun on the table" in promo["summary"]
    assert "concrete physical detail" not in promo["summary"]


def test_summary_preserves_revelation_proposition() -> None:
    move = {
        "action": "",
        "dialogue": "The key is under the loose floorboard.",
        "motivation": _motivation(goal="reveal the truth", tactic="disclose"),
    }
    templates = category_state_change_phrases("Alice")
    state_changes = [templates[ConsequenceCategory.REVELATION]]
    promo = compute_event_promotion_policy_fields(
        acting_character="Alice",
        move=move,
        director_decision={},
        detected=[_det(ConsequenceCategory.REVELATION)],
        state_changes=state_changes,
        actionable_implications=[],
    )
    assert "floorboard" in promo["summary"]
    assert "revealed significant information" not in promo["summary"]


def test_summary_preserves_refusal_content() -> None:
    move = {
        "action": "",
        "dialogue": "I won't sign the contract.",
        "motivation": _motivation(goal="refuse the demand", tactic="hold boundary"),
    }
    templates = category_state_change_phrases("Alice")
    state_changes = [templates[ConsequenceCategory.REFUSAL]]
    promo = compute_event_promotion_policy_fields(
        acting_character="Alice",
        move=move,
        director_decision={},
        detected=[_det(ConsequenceCategory.REFUSAL)],
        state_changes=state_changes,
        actionable_implications=[],
    )
    assert "won't sign the contract" in promo["summary"]
    assert "refused the current demand" not in promo["summary"]


def test_process_turn_retains_director_and_character_contributions() -> None:
    mgr = _fresh_manager()
    move = {
        "action": "looks toward the window",
        "dialogue": "",
        "motivation": _motivation(goal="observe", tactic="look"),
    }
    director = {"environment_event": "Thunder rolls across the courtyard."}
    mgr.process_turn(
        acting_character="Alice",
        move=move,
        director_decision=director,
        other_characters=["Bob"],
    )
    event = mgr.public_events[-1]
    assert event.occurrence_evidence is not None
    kinds = {c.contribution_kind for c in event.occurrence_evidence.contributions}
    producers = {c.producer for c in event.occurrence_evidence.contributions}
    assert "action" in kinds
    assert "environment_event" in kinds
    assert producers == {"character", "director"}
    assert "Thunder rolls" in " ".join(
        c.content for c in event.occurrence_evidence.contributions
    )


def test_user_trigger_reference_and_bounded_excerpt() -> None:
    mgr = _fresh_manager()
    history = [
        {
            "entry_id": "hist-user-1",
            "sequence_index": 0,
            "kind": "user",
            "content": "Draw your weapon slowly.",
            "actor_id": "Player",
            "metadata": {"speaker": "Player"},
        }
    ]
    move = {
        "action": "draws her sidearm",
        "dialogue": "",
        "motivation": _motivation(goal="comply", tactic="draw", risk_level="high"),
    }
    mgr.process_turn(
        acting_character="Alice",
        move=move,
        director_decision={},
        other_characters=["Bob"],
        rp_history=history,
    )
    event = mgr.public_events[-1]
    assert event.occurrence_evidence is not None
    trigger = event.occurrence_evidence.triggering_user
    assert trigger is not None
    assert trigger.entry_id == "hist-user-1"
    assert trigger.content is not None
    assert "Draw your weapon" in trigger.content


def test_private_dialogue_scoped_not_in_global_embedding() -> None:
    move = {
        "move_schema_version": 2,
        "beats": [
            {
                "type": "speech",
                "dialogue": "Secret passphrase alpha.",
                "audibility": AUDIBILITY_PRIVATE,
                "audience": [],
            }
        ],
        "motivation": _motivation(goal="reveal the truth", tactic="whisper"),
    }
    mgr = _fresh_manager()
    mgr.process_turn(
        acting_character="Alice",
        move=move,
        director_decision={},
        other_characters=["Bob"],
    )
    event = mgr.public_events[-1]
    assert event.occurrence_evidence is not None
    assert event.occurrence_evidence.scoped_evidence
    global_text = globally_embeddable_occurrence_text(
        summary=event.summary,
        occurrence_evidence=event.occurrence_evidence,
    )
    assert "Secret passphrase alpha" not in global_text
    assert event.occurrence_evidence.scoped_evidence[0].content


def test_grounding_marker_refs_on_occurrence_evidence() -> None:
    move = {
        "action": "placed the knife on the table",
        "dialogue": "",
        "motivation": _motivation(),
    }
    mgr = _fresh_manager()
    mgr.process_turn(
        acting_character="Alice",
        move=move,
        director_decision={},
        other_characters=["Bob"],
    )
    event = mgr.public_events[-1]
    assert event.occurrence_evidence is not None
    refs = event.occurrence_evidence.structured_fact_refs
    assert any("object_state:weapon" in r.ref_id for r in refs)
    assert event.grounding_markers


def test_public_event_roundtrip_without_occurrence_evidence() -> None:
    event = PublicEvent(
        event_id="evt-old",
        timestamp=datetime.now(timezone.utc),
        event_type="action",
        participants=["Alice"],
        summary="Alice waved.",
        turn_index=1,
    )
    restored = PublicEvent.from_dict(event.to_dict())
    assert restored.occurrence_evidence is None
    assert restored.summary == "Alice waved."


def test_occurrence_evidence_serialization_roundtrip() -> None:
    from continuity_state_occurrence_evidence import OccurrenceContribution

    evidence = OccurrenceEvidence(
        contributions=[
            OccurrenceContribution(
                producer="character",
                contribution_kind="dialogue",
                content='Alice said: "Hello."',
            )
        ]
    )
    event = PublicEvent(
        event_id="evt-1",
        timestamp=datetime.now(timezone.utc),
        event_type="dialogue",
        participants=["Alice"],
        summary='Alice said: "Hello."',
        occurrence_evidence=evidence,
    )
    payload = event.to_dict()
    restored = PublicEvent.from_dict(payload)
    assert restored.occurrence_evidence is not None
    assert restored.occurrence_evidence.contributions[0].content == 'Alice said: "Hello."'


def test_story_knowledge_projection_uses_richer_committed_text() -> None:
    from continuity_state_occurrence_evidence import OccurrenceContribution, TriggeringUser

    evidence = OccurrenceEvidence(
        contributions=[
            OccurrenceContribution(
                producer="character",
                contribution_kind="dialogue",
                content='Alice said: "The bronze key is in the desk."',
            )
        ],
        triggering_user=TriggeringUser(
            entry_id="u-1",
            speaker="Player",
            content="Search the desk.",
        ),
    )
    event = PublicEvent(
        event_id="evt-rich",
        timestamp=datetime.now(timezone.utc),
        event_type="revelation",
        participants=["Alice"],
        summary="Alice revealed significant information.",
        turn_index=2,
        known_by=["Alice", "Bob"],
        occurrence_evidence=evidence,
    )
    fixture = initialize_live_session(cast=["Alice", "Bob"])
    fixture.memory_scope_id = "scope-51"
    fixture.manager.public_events.append(event)
    record = project_occurrence_from_public_event(
        fixture,
        event,
        source_domain_commit_id="commit-51",
    )
    assert record is not None
    assert "bronze key" in record.evidence.committed_text
    assert "Search the desk" in record.evidence.committed_text


def test_template_only_summary_when_no_specific_move_text() -> None:
    move = {"action": "", "dialogue": "", "motivation": _motivation()}
    templates = category_state_change_phrases("Alice")
    state_changes = [templates[ConsequenceCategory.PHYSICAL_STATE_SET]]
    promo = compute_event_promotion_policy_fields(
        acting_character="Alice",
        move=move,
        director_decision={},
        detected=[_det(ConsequenceCategory.PHYSICAL_STATE_SET)],
        state_changes=state_changes,
        actionable_implications=[],
    )
    assert "concrete physical detail" in promo["summary"]

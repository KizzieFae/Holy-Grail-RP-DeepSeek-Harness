"""Issue #51 — audit observability: summary selection + #50 projection provenance."""

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
from continuity_occurrence_evidence import build_move_specific_summary  # noqa: E402
from continuity_scene_helpers import serialize_manager_state  # noqa: E402
from continuity_seam_test_helpers import complete_setup_seam_for_test_manager  # noqa: E402
from continuity_state import ConsequenceCategory, DetectedConsequence, PublicEvent  # noqa: E402
from continuity_state_occurrence_evidence import (  # noqa: E402
    OccurrenceContribution,
    OccurrenceEvidence,
    ScopedEvidence,
    TriggeringUser,
    globally_projected_source_manifest,
)
from continuity_consequence_phrase_maps import category_state_change_phrases  # noqa: E402
from domain_api.story_knowledge_contract import StoryKnowledgeRecord  # noqa: E402
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


def test_summary_selection_source_action() -> None:
    _, source = build_move_specific_summary(
        acting_character="Alice",
        move={"action": "opens the door", "dialogue": "", "motivation": _motivation()},
        director_decision={},
        state_changes=["generic"],
        grounding_markers=[],
        base_promotion=True,
    )
    assert source == "character_action"


def test_summary_selection_source_action_and_dialogue() -> None:
    _, source = build_move_specific_summary(
        acting_character="Alice",
        move={
            "action": "steps forward",
            "dialogue": "Hello.",
            "motivation": _motivation(),
        },
        director_decision={},
        state_changes=[],
        grounding_markers=[],
        base_promotion=True,
    )
    assert source == "character_action_and_dialogue"


def test_summary_selection_source_director_environment() -> None:
    _, source = build_move_specific_summary(
        acting_character="Alice",
        move={"action": "", "dialogue": "", "motivation": _motivation()},
        director_decision={"environment_event": "Rain begins."},
        state_changes=[],
        grounding_markers=[],
        base_promotion=True,
    )
    assert source == "director_environment"


def test_summary_selection_source_state_change_fallback() -> None:
    templates = category_state_change_phrases("Alice")
    state_changes = [templates[ConsequenceCategory.PHYSICAL_STATE_SET]]
    _, source = build_move_specific_summary(
        acting_character="Alice",
        move={"action": "", "dialogue": "", "motivation": _motivation()},
        director_decision={},
        state_changes=state_changes,
        grounding_markers=[],
        base_promotion=True,
    )
    assert source == "state_change_fallback"


def test_summary_selection_source_in_turn_metadata_and_survives_persist() -> None:
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location="Room",
        opening_description="open",
        present_characters=["Alice", "Bob"],
    )
    complete_setup_seam_for_test_manager(mgr, cast=["Alice", "Bob"])
    move = {
        "action": "placed the gun on the table",
        "dialogue": "",
        "motivation": _motivation(),
    }
    mgr.process_turn(
        acting_character="Alice",
        move=move,
        director_decision={},
        other_characters=["Bob"],
    )
    meta = mgr.turn_metadata_by_index[mgr.turn_counter]
    assert meta.get("summary_selection_source") == "character_action"

    payload = serialize_manager_state(manager=mgr)
    stored_meta = payload.get("turn_metadata_by_index", {}).get(str(mgr.turn_counter), {})
    assert stored_meta.get("summary_selection_source") == "character_action"


def test_promotion_policy_exposes_summary_selection_source() -> None:
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
    assert promo["summary_selection_source"] == "character_action"
    assert "gun on the table" in promo["summary"]


def test_projection_manifest_records_included_components() -> None:
    evidence = OccurrenceEvidence(
        contributions=[
            OccurrenceContribution(
                producer="character",
                contribution_kind="dialogue",
                content='Alice said: "The key is here."',
            ),
            OccurrenceContribution(
                producer="director",
                contribution_kind="environment_event",
                content="Thunder rolls.",
            ),
        ],
        triggering_user=TriggeringUser(
            entry_id="user-42",
            speaker="Player",
            content="Search the desk.",
        ),
    )
    manifest = globally_projected_source_manifest(
        event_id="evt-rich",
        summary="Alice revealed significant information.",
        occurrence_evidence=evidence,
    )
    assert manifest["source_event_id"] == "evt-rich"
    sources = manifest["projection_sources"]
    assert "summary" in sources
    assert "occurrence_evidence.contribution:character:dialogue:0" in sources
    assert "occurrence_evidence.contribution:director:environment_event:1" in sources
    assert "triggering_user:user-42" in sources
    assert manifest["scoped_evidence_present"] is False
    assert manifest["scoped_evidence_projected"] is False


def test_projection_manifest_excludes_scoped_evidence_from_sources() -> None:
    evidence = OccurrenceEvidence(
        contributions=[],
        scoped_evidence=[
            ScopedEvidence(
                audibility=AUDIBILITY_PRIVATE,
                audience=[],
                content='Alice said: "Secret."',
            )
        ],
    )
    manifest = globally_projected_source_manifest(
        event_id="evt-private",
        summary="Alice acted.",
        occurrence_evidence=evidence,
    )
    assert manifest["scoped_evidence_present"] is True
    assert manifest["scoped_evidence_projected"] is False
    assert not any("scoped" in item for item in manifest["projection_sources"])
    assert "Secret" not in str(manifest)


def test_story_knowledge_record_carries_evidence_projection() -> None:
    evidence = OccurrenceEvidence(
        contributions=[
            OccurrenceContribution(
                producer="character",
                contribution_kind="dialogue",
                content='Alice said: "Bronze key."',
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
    fixture.memory_scope_id = "scope-audit"
    fixture.manager.public_events.append(event)
    record = project_occurrence_from_public_event(
        fixture,
        event,
        source_domain_commit_id="commit-audit",
    )
    assert record is not None
    assert record.evidence_projection is not None
    assert record.evidence_projection.source_event_id == "evt-rich"
    assert "summary" in record.evidence_projection.projection_sources
    assert record.source_domain_commit_id == "commit-audit"
    assert "bronze key" in record.evidence.committed_text.lower()


def test_legacy_story_record_without_evidence_projection_loads() -> None:
    payload = {
        "schema_version": 1,
        "record_kind": "occurrence",
        "memory_scope_id": "scope-legacy",
        "source_session_id": "sess-1",
        "source_domain_commit_id": "commit-legacy",
        "hg_scene_id": "scene-1",
        "turn_index": 1,
        "event_type": "action",
        "participants": ["Alice"],
        "evidence": {"committed_text": "Alice waved.", "summary": "Alice waved."},
        "event_id": "evt-legacy",
        "content_hash": "",
        "written_at": "2026-01-01T00:00:00+00:00",
    }
    record = StoryKnowledgeRecord.from_dict(payload)
    assert record.evidence_projection is None
    assert record.evidence.committed_text == "Alice waved."


def test_projection_idempotent_append_by_event_id() -> None:
    import shutil
    import tempfile

    from domain_api.story_knowledge_service import StoryKnowledgeService  # noqa: E402
    from domain_api.story_knowledge_repository import StoryKnowledgeRepository  # noqa: E402

    tmpdir = tempfile.mkdtemp()
    try:
        repo = StoryKnowledgeRepository(tmpdir)
        service = StoryKnowledgeService(repo)
        fixture = initialize_live_session(cast=["Alice"])
        fixture.memory_scope_id = "scope-idem"
        fixture.manager.public_events.append(
            PublicEvent(
                event_id="evt-idem",
                timestamp=datetime.now(timezone.utc),
                event_type="action",
                participants=["Alice"],
                summary="Alice waved.",
                turn_index=1,
                known_by=["Alice"],
            )
        )
        first = service.project_after_commit(fixture, source_domain_commit_id="c1")
        second = service.project_after_commit(fixture, source_domain_commit_id="c1")
        assert first["appended"] == 1
        assert second["appended"] == 0
        records = repo.list_records("scope-idem")
        assert len(records) == 1
        assert records[0].evidence_projection is not None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

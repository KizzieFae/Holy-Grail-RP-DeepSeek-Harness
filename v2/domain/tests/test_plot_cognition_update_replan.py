"""#61 Plot Cognition update and semantic replan domain contract tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import unittest
from copy import deepcopy
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_scene_pressure_projection import compute_issue_material_fingerprint  # noqa: E402
from continuity_state import IssueState, IssueStatus, PublicEvent  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

from domain_api.cognition_composition import CognitionComposition  # noqa: E402
from domain_api.librarian_contract import StableReference  # noqa: E402
from domain_api.narrator_environment_contract import (  # noqa: E402
    ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE,
    ENVIRONMENTAL_DESCRIPTOR_MARKER,
    environmental_descriptor_payload,
)
from domain_api.plot_cognition_initialization_contract import (  # noqa: E402
    INITIALIZATION_PROPOSAL_SCHEMA,
    PlotCognitionInitializationProposal,
    materialize_initial_overlay,
    new_proposal_id,
)
from domain_api.plot_cognition_initialization_sources import gather_initialization_sources  # noqa: E402
from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
    GLOBAL_PLOT_FRAME_SCHEMA,
    PLOT_GOAL_SCHEMA,
    UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
    CognitionApplicability,
    CreationProvenance,
    GlobalPlotFrame,
    GoalLineage,
    PlotGoal,
    UnresolvedNarrativePressure,
    global_plot_frame_to_dict,
    new_frame_id,
    new_goal_id,
    new_pressure_id,
    plot_goal_from_dict,
    plot_goal_to_dict,
    unresolved_narrative_pressure_to_dict,
)
from domain_api.plot_cognition_overlay_repository import PlotCognitionOverlayRepository  # noqa: E402
from domain_api.plot_cognition_overlay_service import PlotCognitionOverlayService  # noqa: E402
from domain_api.plot_cognition_overlay_store import (  # noqa: E402
    ASSIMILATED_AUTHORITY_SCHEMA,
    AssimilatedAuthority,
    AssimilatedSessionAuthority,
    BoundednessPolicy,
    LoadStatus,
    PlotCognitionOverlayStore,
    authority_freshness_status,
    empty_store,
    is_authority_fresh,
    sync_legacy_commit_lineage,
)
from domain_api.plot_cognition_scope_lock import PlotCognitionScopeLockRegistry  # noqa: E402
from domain_api.plot_cognition_update_contract import (  # noqa: E402
    REPLAN_EVALUATION_SCHEMA,
    REPLAN_PROPOSAL_SCHEMA,
    UPDATE_EVALUATION_SCHEMA,
    UPDATE_PROPOSAL_SCHEMA,
    PlotCognitionReplanEvaluation,
    PlotCognitionReplanProposal,
    PlotCognitionUpdateEvaluation,
    PlotCognitionUpdateProposal,
    UpdateForensicHandoff,
    cognition_identity_preserved,
    is_inactive,
    is_superseded,
    materialize_replan_overlay,
    materialize_update_overlay,
    new_evaluation_id,
    new_replan_evaluation_id,
    new_replan_proposal_id,
    validate_replan_proposal_objective,
    validate_update_proposal_objective,
)
from domain_api.plot_cognition_update_service import PlotCognitionUpdateService  # noqa: E402
from domain_api.plot_cognition_update_sources import (  # noqa: E402
    build_plot_cognition_authority_projection,
    compute_authority_source_fingerprint,
    gather_update_source_snapshot,
)
from domain_api.plot_cognition_semantic_authority import (  # noqa: E402
    DEFAULT_MAX_EVENT_SUMMARY_CHARS,
    build_semantic_authority_excerpts,
    extract_bounded_move_excerpt,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import (  # noqa: E402
    CharacterTurnRecord,
    LiveSession,
    RoundFixture,
    initialize_live_session,
)
from domain_api.story_knowledge_contract import (  # noqa: E402
    EpistemicAuthorityRef,
    StoryEvidence,
    StoryEvidenceProjectionProvenance,
    StoryKnowledgeRecord,
)

TEST_POLICY = BoundednessPolicy(max_active_goals=2, max_active_pressures=2)


def _session(*, scope_id: str = "scope-update-test") -> LiveSession:
    fixture = initialize_live_session(cast=["Alice"], plot_cognition_scope_id=scope_id)
    fixture.setup_snapshot = {
        "opening": {"mode": "minimal"},
        "scene_template_id": "tpl-test",
        "scene_template": {"template_id": "tpl-test", "premise": "Test premise."},
        "character_cards": {"alice": {"name": "Alice", "goals": "Find the key."}},
        "location": "Hall",
    }
    return fixture


def _goal_draft(*, goal_id: str | None = None, state: str = "active", direction: str | None = None) -> dict:
    gid = goal_id or new_goal_id()
    return plot_goal_to_dict(
        PlotGoal(
            schema=PLOT_GOAL_SCHEMA,
            goal_id=gid,
            intended_direction=direction or "Explore whether Alice finds the key.",
            basis_note="Authored context.",
            basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            planning_horizon="MEDIUM",
            creation_provenance=CreationProvenance(source="storyteller"),
            lineage=GoalLineage(),
            activity_state=state,  # type: ignore[arg-type]
        )
    )


def _pressure_draft(*, pressure_id: str | None = None, state: str = "active") -> dict:
    pid = pressure_id or new_pressure_id()
    return unresolved_narrative_pressure_to_dict(
        UnresolvedNarrativePressure(
            schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
            pressure_id=pid,
            pressure_text="The key remains missing.",
            dramatic_rationale="Creates tension.",
            basis_note=None,
            basis_refs=(),
            continuity_issue_refs=(),
            applicability=CognitionApplicability(
                applicability_kind="global",
                primary_character_id=None,
                involved_character_ids=(),
            ),
            creation_provenance=CreationProvenance(source="storyteller"),
            activity_state=state,  # type: ignore[arg-type]
        )
    )


def _frame_draft(*, frame_id: str | None = None) -> dict:
    fid = frame_id or new_frame_id()
    return global_plot_frame_to_dict(
        GlobalPlotFrame(
            schema=GLOBAL_PLOT_FRAME_SCHEMA,
            frame_id=fid,
            direction_sense="Slow-burn investigation.",
            pacing_note="Measured.",
            cross_character_note=None,
            opportunity_note=None,
            basis_refs=(),
            activity_state="active",
            superseded_by_frame_id=None,
            creation_provenance=CreationProvenance(source="storyteller"),
        )
    )


def _initialized_store(fixture: LiveSession, overlay: PlotCognitionOverlayService) -> PlotCognitionOverlayStore:
    sources = gather_initialization_sources(fixture)
    proposal = PlotCognitionInitializationProposal(
        schema=INITIALIZATION_PROPOSAL_SCHEMA,
        proposal_id=new_proposal_id(),
        source_snapshot_id=sources.snapshot_id,
        source_snapshot_fingerprint=sources.fingerprint,
        plot_cognition_scope_id=fixture.plot_cognition_scope_id,
        adoption_rationale="Initial pressure.",
        goals=(),
        pressures=(_pressure_draft(),),
        global_frame=None,
    )
    store, _ = materialize_initial_overlay(proposal, plot_cognition_scope_id=fixture.plot_cognition_scope_id)
    assert store is not None
    overlay.replace_snapshot(fixture.plot_cognition_scope_id, store, expected_revision=0, policy=TEST_POLICY)
    loaded = overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
    assert loaded.store is not None
    return loaded.store


def _b2_record(*, commit_id: str, record_id: str = "env-b2-test") -> StoryKnowledgeRecord:
    return StoryKnowledgeRecord(
        schema_version=1,
        record_kind="derived",
        memory_scope_id="scope-mem",
        source_session_id="sess",
        source_domain_commit_id=commit_id,
        hg_scene_id="scene",
        turn_index=1,
        event_type=ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE,
        grounding_markers=[ENVIRONMENTAL_DESCRIPTOR_MARKER],
        evidence=StoryEvidence(
            summary="door locked",
            committed_text=environmental_descriptor_payload(
                property_key="door_state",
                value="locked",
                stable_refs=("object:door",),
            ),
        ),
        story_record_id=record_id,
        epistemic_authority_ref=EpistemicAuthorityRef(
            ref_kind="establishment_decision",
            ref_payload={"decision_id": "dec-1"},
        ),
        submission_authority_ref="host-accepted",
    )


def _k2_occurrence_record(*, event_id: str) -> StoryKnowledgeRecord:
    return StoryKnowledgeRecord(
        schema_version=1,
        record_kind="occurrence",
        memory_scope_id="scope-mem",
        source_session_id="sess",
        source_domain_commit_id="commit-k2",
        hg_scene_id="scene",
        turn_index=1,
        event_type="action",
        evidence=StoryEvidence(summary="Alice acts", committed_text="Alice acts."),
        event_id=event_id,
        evidence_projection=StoryEvidenceProjectionProvenance(
            source_event_id=event_id,
            projection_sources=("summary",),
        ),
    )


def _update_proposal(
    fixture: LiveSession,
    store: PlotCognitionOverlayStore,
    *,
    goals: tuple[dict, ...] = (),
    pressures: tuple[dict, ...] = (),
    inactivated_goal_ids: tuple[str, ...] = (),
    frame: dict | None = None,
    replan_required: bool = False,
) -> PlotCognitionUpdateProposal:
    snapshot = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
    return PlotCognitionUpdateProposal(
        schema=UPDATE_PROPOSAL_SCHEMA,
        proposal_id=new_proposal_id(),
        source_snapshot_id=snapshot.snapshot_id,
        source_snapshot_fingerprint=snapshot.authority_source_fingerprint,
        plot_cognition_scope_id=fixture.plot_cognition_scope_id,
        prior_store_revision=store.store_revision,
        assimilation_rationale="Assimilate authoritative delta.",
        goals=goals,
        pressures=pressures,
        global_frame=frame,
        inactivated_goal_ids=inactivated_goal_ids,
        replan_required=replan_required,
    )


class PlotCognitionLegacyStoreCompatibilityTests(unittest.TestCase):
    def test_legacy_ready_store_loads_without_authority_metadata(self) -> None:
        tmpdir = tempfile.mkdtemp()
        try:
            repo = PlotCognitionOverlayRepository(tmpdir)
            service = PlotCognitionOverlayService(repo)
            store = empty_store("legacy-scope")
            store.store_revision = 1
            store.goals[plot_goal_from_dict(_goal_draft()).goal_id] = plot_goal_from_dict(_goal_draft())
            repo.save_raw("legacy-scope", store.to_dict(), expected_revision=0)
            loaded = service.load("legacy-scope", policy=TEST_POLICY)
            self.assertEqual(loaded.status, LoadStatus.READY)
            assert loaded.store is not None
            self.assertIsNone(loaded.store.assimilated_authority)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_legacy_store_freshness_unknown_not_corrupt(self) -> None:
        store = empty_store("legacy-scope")
        store.store_revision = 1
        status = authority_freshness_status(
            store,
            current_domain_commit_id="commit-1",
            current_continuity_version=1,
            current_authority_source_fingerprint="abc",
        )
        self.assertEqual(status, "freshness_unprovable")
        self.assertFalse(
            is_authority_fresh(
                store,
                current_domain_commit_id="commit-1",
                current_continuity_version=1,
                current_authority_source_fingerprint="abc",
            )
        )


class PlotCognitionAuthorityProjectionTests(unittest.TestCase):
    def test_fingerprint_stable_for_same_state(self) -> None:
        fixture = _session()
        body_a = build_plot_cognition_authority_projection(fixture, [], None)
        body_b = deepcopy(body_a)
        self.assertEqual(
            compute_authority_source_fingerprint(body_a),
            compute_authority_source_fingerprint(body_b),
        )

    def test_presentation_persist_same_fingerprint(self) -> None:
        fixture = _session()
        first = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        append_history_entry(
            fixture.rp_history,
            kind="presentation",
            content="Narration only.",
            presentation_status="rendered",
        )
        fixture.continuity_version += 1
        second = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        self.assertEqual(first, second)

    def test_skip_persist_same_fingerprint(self) -> None:
        fixture = _session()
        first = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        fixture.continuity_version += 1
        fixture.rp_history.append({"kind": "skip", "content": "Alice skipped."})
        second = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        self.assertEqual(first, second)

    def test_failed_audit_persist_same_fingerprint(self) -> None:
        fixture = _session()
        first = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        fixture.continuity_version += 1
        fixture.librarian_proposal_audit_log.append(
            {"status": "rejected", "proposal_kind": "environment_audit"}
        )
        second = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        self.assertEqual(first, second)

    def test_accepted_b2_changes_fingerprint(self) -> None:
        fixture = _session()
        first = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        records = [_b2_record(commit_id="commit-b2")]
        second = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, records, None)
        )
        self.assertNotEqual(first, second)

    def test_librarian_apply_changes_fingerprint(self) -> None:
        fixture = _session()
        issue = IssueState(
            issue_id="issue-1",
            description="Blocked door",
            participants=["Alice"],
            status=IssueStatus.ACTIVE,
            pressure_kind="obstacle",
            created_at=datetime.now(timezone.utc),
        )
        fixture.manager.issues["issue-1"] = issue
        fixture.manager.scene_state.active_issue_ids = ["issue-1"]
        first = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        fixture.manager.issue_pressure_semantic_overlays = {
            "issue-1": {
                "lifecycle": "active",
                "issue_material_fingerprint": compute_issue_material_fingerprint(issue),
                "semantic_unmet_condition": "door remains locked",
                "semantic_authority": {"source": "librarian_overlay"},
            }
        }
        second = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        self.assertNotEqual(first, second)

    def test_k2_occurrence_not_duplicated(self) -> None:
        fixture = _session()
        event_id = "evt-1"
        fixture.manager.public_events.append(
            PublicEvent(
                event_id=event_id,
                timestamp=datetime.now(timezone.utc),
                event_type="action",
                participants=["Alice"],
                summary="Alice opens the door.",
                turn_index=1,
                known_by=["Alice"],
            )
        )
        with_k2 = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(
                fixture,
                [_k2_occurrence_record(event_id=event_id)],
                None,
            )
        )
        without_k2 = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        self.assertEqual(with_k2, without_k2)

    def test_commit_changes_lineage_and_fingerprint(self) -> None:
        fixture = _session()
        first = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        commit_id = "commit-1"
        fixture.commit_ids.append(commit_id)
        fixture.rounds.append(
            RoundFixture(
                hg_round_id="round-1",
                hg_scene_id=fixture.hg_scene_id,
                turn_index=0,
                domain_commit_id=commit_id,
                committed_character_id="Alice",
                committed_move={"beats": [{"type": "action", "action": "searches"}]},
                continuity_turn_index=1,
                character_turns=[
                    CharacterTurnRecord(
                        character_id="Alice",
                        committed_move={"beats": [{"type": "action", "action": "searches"}]},
                        domain_commit_id=commit_id,
                        continuity_turn_index=1,
                        director_decision={},
                    )
                ],
            )
        )
        second = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], commit_id)
        )
        self.assertNotEqual(first, second)

    def test_meaningful_fact_change_alters_fingerprint(self) -> None:
        fixture = _session()
        first = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        fixture.manager.scene_state.location = "Vault"
        second = compute_authority_source_fingerprint(
            build_plot_cognition_authority_projection(fixture, [], None)
        )
        self.assertNotEqual(first, second)

    def test_irrelevant_correlation_does_not_alter_fingerprint(self) -> None:
        fixture = _session()
        body = build_plot_cognition_authority_projection(fixture, [], None)
        first = compute_authority_source_fingerprint(body)
        body_copy = deepcopy(body)
        body_copy["_audit_correlation_id"] = "should-not-be-in-canonical"
        second = compute_authority_source_fingerprint(body)
        self.assertEqual(first, second)


class PlotCognitionSemanticAuthorityTests(unittest.TestCase):
    def test_public_event_summary_in_semantic_excerpts(self) -> None:
        fixture = _session()
        fixture.manager.public_events.append(
            PublicEvent(
                event_id="evt-treaty",
                timestamp=datetime.now(timezone.utc),
                event_type="dialogue",
                participants=["Alice"],
                summary="The treaty is finished. Everyone here saw what happened.",
                turn_index=1,
            )
        )
        excerpts = build_semantic_authority_excerpts(fixture, through_domain_commit_id=None)
        self.assertEqual(len(excerpts["public_events"]), 1)
        self.assertIn("treaty", excerpts["public_events"][0]["summary"].lower())
        body = build_plot_cognition_authority_projection(fixture, [], None)
        self.assertIn("summary_digest", body["continuity"]["public_events"][0])
        self.assertNotIn("summary", body["continuity"]["public_events"][0])

    def test_semantic_excerpts_bounded(self) -> None:
        fixture = _session()
        long_summary = "x" * (DEFAULT_MAX_EVENT_SUMMARY_CHARS + 50)
        fixture.manager.public_events.append(
            PublicEvent(
                event_id="evt-long",
                timestamp=datetime.now(timezone.utc),
                event_type="dialogue",
                participants=["Alice"],
                summary=long_summary,
                turn_index=1,
            )
        )
        excerpts = build_semantic_authority_excerpts(fixture, through_domain_commit_id=None)
        self.assertLessEqual(len(excerpts["public_events"][0]["summary"]), DEFAULT_MAX_EVENT_SUMMARY_CHARS)

    def test_snapshot_includes_semantic_excerpts_without_changing_fingerprint(self) -> None:
        fixture = _session()
        fixture.manager.public_events.append(
            PublicEvent(
                event_id="evt-1",
                timestamp=datetime.now(timezone.utc),
                event_type="dialogue",
                participants=["Alice"],
                summary="A committed public event occurred.",
                turn_index=1,
            )
        )
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        snapshot = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
        self.assertIn("semantic_authority_excerpts", snapshot.to_dict())
        self.assertTrue(snapshot.semantic_authority_excerpts["public_events"])
        fingerprint_from_body = compute_authority_source_fingerprint(snapshot.canonical_body)
        self.assertEqual(snapshot.authority_source_fingerprint, fingerprint_from_body)

    def test_issue_description_in_semantic_excerpts(self) -> None:
        fixture = _session()
        issue = IssueState(
            issue_id="issue-1",
            description="The vault door remains sealed.",
            participants=["Alice"],
            status=IssueStatus.ACTIVE,
            pressure_kind="obstacle",
            created_at=datetime.now(timezone.utc),
        )
        fixture.manager.issues["issue-1"] = issue
        fixture.manager.scene_state.active_issue_ids = ["issue-1"]
        excerpts = build_semantic_authority_excerpts(fixture, through_domain_commit_id=None)
        self.assertEqual(excerpts["issues"][0]["description"], "The vault door remains sealed.")

    def test_committed_move_excerpt_when_no_public_event(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [{"type": "dialogue", "dialogue": "The treaty is finished."}],
        }
        excerpt = extract_bounded_move_excerpt(move)
        self.assertIn("treaty", excerpt.lower())


class PlotCognitionUpdateServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = PlotCognitionOverlayRepository(self._tmpdir)
        self.locks = PlotCognitionScopeLockRegistry()
        self.overlay = PlotCognitionOverlayService(self.repo, scope_locks=self.locks)
        self.service = PlotCognitionUpdateService(self.overlay)
        self.fixture = _session()
        self.store = _initialized_store(self.fixture, self.overlay)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_first_reconciliation_establishes_authority_metadata(self) -> None:
        result = self.service.first_reconciliation(
            self.fixture,
            self.store,
            TEST_POLICY,
            contributors=(self.fixture.hg_scene_id,),
        )
        self.assertTrue(result.success)
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        self.assertIsNotNone(loaded.store.assimilated_authority)

    def test_objective_authority_unchanged_advancement(self) -> None:
        self.service.first_reconciliation(self.fixture, self.store, TEST_POLICY)
        self.fixture.continuity_version += 1
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        snapshot = gather_update_source_snapshot(
            self.fixture, loaded.store, [], (self.fixture.hg_scene_id,)
        )
        result = self.service.advance_authority_unchanged(
            self.fixture,
            loaded.store,
            TEST_POLICY,
            source_snapshot=snapshot,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.code, "authority_unchanged")

    def test_semantic_no_change_advances_freshness(self) -> None:
        self.service.first_reconciliation(self.fixture, self.store, TEST_POLICY)
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        self.fixture.manager.scene_state.location = "Changed Hall"
        snapshot = gather_update_source_snapshot(
            self.fixture, loaded.store, [], (self.fixture.hg_scene_id,)
        )
        proposal = _update_proposal(self.fixture, loaded.store)
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="no_change",
            findings=(),
            no_change_rationale="No cognition adjustment warranted.",
        )
        result = self.service.commit_update(
            self.fixture,
            proposal,
            evaluation,
            policy=TEST_POLICY,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.code, "semantic_no_change")

    def test_stale_revision_rejects(self) -> None:
        self.service.first_reconciliation(self.fixture, self.store, TEST_POLICY)
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        proposal = _update_proposal(self.fixture, loaded.store, goals=(_goal_draft(),))
        proposal = PlotCognitionUpdateProposal(
            **{**proposal.__dict__, "prior_store_revision": loaded.store.store_revision - 1}
        )
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        result = self.service.commit_update(
            self.fixture, proposal, evaluation, policy=TEST_POLICY
        )
        self.assertFalse(result.success)
        self.assertEqual(result.code, "stale_revision")

    def test_stale_fingerprint_rejects(self) -> None:
        self.service.first_reconciliation(self.fixture, self.store, TEST_POLICY)
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        proposal = _update_proposal(self.fixture, loaded.store, goals=(_goal_draft(),))
        self.fixture.manager.scene_state.location = "Different room"
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        result = self.service.commit_update(
            self.fixture, proposal, evaluation, policy=TEST_POLICY
        )
        self.assertFalse(result.success)
        self.assertEqual(result.code, "stale_source")

    def test_concurrent_writer_cas(self) -> None:
        self.service.first_reconciliation(self.fixture, self.store, TEST_POLICY)
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        proposal_a = _update_proposal(self.fixture, loaded.store, goals=(_goal_draft(goal_id="g-a"),))
        proposal_b = _update_proposal(self.fixture, loaded.store, goals=(_goal_draft(goal_id="g-b"),))
        eval_a = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal_a.proposal_id,
            overall_result="accept",
            findings=(),
        )
        eval_b = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal_b.proposal_id,
            overall_result="accept",
            findings=(),
        )
        results: list = []

        def commit(proposal, evaluation) -> None:
            results.append(
                self.service.commit_update(
                    self.fixture, proposal, evaluation, policy=TEST_POLICY
                )
            )

        threads = [
            threading.Thread(target=commit, args=(proposal_a, eval_a)),
            threading.Thread(target=commit, args=(proposal_b, eval_b)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        successes = [item for item in results if item.success]
        self.assertEqual(len(successes), 1)

    def test_scalar_vector_consistency_single_session(self) -> None:
        authority = AssimilatedAuthority(
            schema=ASSIMILATED_AUTHORITY_SCHEMA,
            sessions=(
                AssimilatedSessionAuthority(
                    hg_scene_id=self.fixture.hg_scene_id,
                    through_domain_commit_id="commit-1",
                    through_continuity_version=1,
                    authority_source_fingerprint="fp-1",
                ),
            ),
        )
        store = deepcopy(self.store)
        store.assimilated_authority = authority
        store.assimilated_through_domain_commit_id = "commit-1"
        synced = sync_legacy_commit_lineage(store, sole_contributor_hg_scene_id=self.fixture.hg_scene_id)
        self.assertEqual(synced.assimilated_through_domain_commit_id, "commit-1")


class PlotCognitionUpdateContractTests(unittest.TestCase):
    def test_goal_advance_preserves_identity(self) -> None:
        goal_id = "goal-stable"
        prior = _goal_draft(goal_id=goal_id)
        updated = dict(prior)
        updated["momentum_note"] = "Progress made."
        self.assertTrue(cognition_identity_preserved(prior, updated))

    def test_material_direction_change_mints_new_id(self) -> None:
        prior = _goal_draft(goal_id="goal-old")
        updated = _goal_draft(goal_id="goal-new")
        self.assertFalse(cognition_identity_preserved(prior, updated))

    def test_subordinate_goal_lineage(self) -> None:
        child = _goal_draft(goal_id="child")
        child["lineage"] = {"parent_goal_id": "parent", "superseded_by_goal_id": None}
        goal = plot_goal_from_dict(child)
        self.assertEqual(goal.lineage.parent_goal_id, "parent")

    def test_horizon_modification_same_id(self) -> None:
        prior = _goal_draft(goal_id="goal-1")
        updated = dict(prior)
        updated["planning_horizon"] = "SHORT"
        self.assertTrue(cognition_identity_preserved(prior, updated))

    def test_resolve_to_inactive(self) -> None:
        item = _goal_draft(state="inactive")
        self.assertTrue(is_inactive(item))

    def test_supersede_marks_inactive_and_new_id(self) -> None:
        old = _goal_draft(goal_id="old")
        old["lineage"] = {"parent_goal_id": None, "superseded_by_goal_id": "new"}
        self.assertTrue(is_superseded(old))
        new = _goal_draft(goal_id="new")
        self.assertNotEqual(old["goal_id"], new["goal_id"])

    def test_reactivation_inactive_to_active(self) -> None:
        item = _goal_draft(state="inactive")
        item["activity_state"] = "active"
        self.assertFalse(is_inactive(item))

    def test_retired_rejected_in_proposal(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        goal = _goal_draft()
        goal["activity_state"] = "retired"
        proposal = _update_proposal(fixture, store, goals=(goal,))
        validation = validate_update_proposal_objective(
            proposal,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertFalse(validation.ok)

    def test_overflow_rejected(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        goals = tuple(_goal_draft(goal_id=f"g{i}") for i in range(3))
        proposal = _update_proposal(fixture, store, goals=goals)
        validation = validate_update_proposal_objective(
            proposal,
            policy_max_active_goals=TEST_POLICY.max_active_goals,
            policy_max_active_pressures=TEST_POLICY.max_active_pressures,
        )
        self.assertFalse(validation.ok)
        self.assertTrue(validation.over_budget)

    def test_semantic_rebalance_inactivate_and_admit(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        store.goals["g1"] = plot_goal_from_dict(_goal_draft(goal_id="g1"))
        store.goals["g2"] = plot_goal_from_dict(_goal_draft(goal_id="g2"))
        proposal = _update_proposal(
            fixture,
            store,
            goals=(_goal_draft(goal_id="g3"),),
            inactivated_goal_ids=("g1",),
        )
        validation = validate_update_proposal_objective(
            proposal,
            policy_max_active_goals=TEST_POLICY.max_active_goals,
            policy_max_active_pressures=TEST_POLICY.max_active_pressures,
        )
        self.assertTrue(validation.ok)

    def test_frame_only_update(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        proposal = _update_proposal(fixture, store, frame=_frame_draft())
        validation = validate_update_proposal_objective(
            proposal,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertTrue(validation.ok)

    def test_fully_empty_update_valid(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        proposal = _update_proposal(fixture, store)
        validation = validate_update_proposal_objective(
            proposal,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertTrue(validation.ok)

    def test_character_origin_in_basis_refs(self) -> None:
        goal = _goal_draft()
        goal["basis_refs"] = [
            {"ref_kind": "committed_move", "stable_ref": "commit-1:Alice:action"}
        ]
        goal["creation_provenance"] = {"source": "storyteller"}
        self.assertEqual(goal["creation_provenance"]["source"], "storyteller")

    def test_player_origin_in_basis_refs(self) -> None:
        goal = _goal_draft()
        goal["basis_refs"] = [
            {"ref_kind": "triggering_user", "stable_ref": "entry-u-1"}
        ]
        self.assertEqual(goal["creation_provenance"]["source"], "storyteller")


class PlotCognitionSharedScopeTests(unittest.TestCase):
    def test_two_contributor_vector(self) -> None:
        authority = AssimilatedAuthority(
            schema=ASSIMILATED_AUTHORITY_SCHEMA,
            sessions=(
                AssimilatedSessionAuthority(
                    hg_scene_id="scene-a",
                    through_domain_commit_id="commit-a",
                    through_continuity_version=2,
                    authority_source_fingerprint="fp-a",
                ),
                AssimilatedSessionAuthority(
                    hg_scene_id="scene-b",
                    through_domain_commit_id="commit-b",
                    through_continuity_version=3,
                    authority_source_fingerprint="fp-b",
                ),
            ),
        )
        store = empty_store("shared-scope")
        store.store_revision = 1
        store.assimilated_authority = authority
        self.assertEqual(len(store.assimilated_authority.sessions), 2)

    def test_incomplete_contributor_vector_not_fresh(self) -> None:
        authority = AssimilatedAuthority(
            schema=ASSIMILATED_AUTHORITY_SCHEMA,
            sessions=(
                AssimilatedSessionAuthority(
                    hg_scene_id="scene-a",
                    through_domain_commit_id="commit-a",
                    through_continuity_version=2,
                    authority_source_fingerprint="fp-a",
                ),
            ),
        )
        store = empty_store("shared-scope")
        store.store_revision = 1
        store.assimilated_authority = authority
        status = authority_freshness_status(
            store,
            current_domain_commit_id="commit-a",
            current_continuity_version=2,
            current_authority_source_fingerprint="fp-a",
            contributor_hg_scene_ids=("scene-a", "scene-b"),
        )
        self.assertEqual(status, "shared_scope_ambiguous")


class PlotCognitionCatchUpTests(unittest.TestCase):
    def test_sequential_catch_up_mode(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        snapshot = gather_update_source_snapshot(
            fixture, store, [], (fixture.hg_scene_id,), catch_up_mode="sequential"
        )
        self.assertEqual(snapshot.catch_up_mode, "sequential")
        self.assertFalse(snapshot.evidence_gap)

    def test_endpoint_reconciliation_records_evidence_gap(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        snapshot = gather_update_source_snapshot(
            fixture,
            store,
            [],
            (fixture.hg_scene_id,),
            catch_up_mode="endpoint_reconciliation",
            evidence_gap=True,
            evidence_gap_detail="intermediate decisions missing",
        )
        self.assertTrue(snapshot.evidence_gap)
        self.assertEqual(snapshot.evidence_gap_detail, "intermediate decisions missing")

    def test_unreconstructable_lineage_blocks(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.assimilated_authority = AssimilatedAuthority(
            schema=ASSIMILATED_AUTHORITY_SCHEMA,
            sessions=(
                AssimilatedSessionAuthority(
                    hg_scene_id=fixture.hg_scene_id,
                    through_domain_commit_id="missing-commit",
                    through_continuity_version=0,
                    authority_source_fingerprint="fp",
                ),
            ),
        )
        status = authority_freshness_status(
            store,
            current_domain_commit_id="other-commit",
            current_continuity_version=0,
            current_authority_source_fingerprint="fp",
            contributor_hg_scene_ids=(fixture.hg_scene_id,),
        )
        self.assertEqual(status, "semantic_assimilation_pending")


class PlotCognitionCompositionBoundaryTests(unittest.TestCase):
    def test_cognition_composition_exposes_update_service(self) -> None:
        tmpdir = tempfile.mkdtemp()
        try:
            repo = PlotCognitionOverlayRepository(tmpdir)
            composition = CognitionComposition.for_tests(
                plot_cognition_overlay_repository=repo,
            )
            self.assertIsNotNone(composition.plot_cognition_update)
            self.assertIsInstance(composition.plot_cognition_update, PlotCognitionUpdateService)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_dsh_orchestration_modules_in_update_surface(self) -> None:
        import domain_api.plot_cognition_update_service as service_module

        source = Path(service_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("storyteller_service", source)
        self.assertNotIn("commit_move_transaction", source)

    def test_materialize_update_overlay_through_replace_snapshot_only(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        proposal = _update_proposal(fixture, store, goals=(_goal_draft(),))
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        authority = AssimilatedAuthority(
            schema=ASSIMILATED_AUTHORITY_SCHEMA,
            sessions=(),
        )
        materialized, validation = materialize_update_overlay(
            store,
            proposal,
            evaluation,
            assimilated_authority=authority,
            through_domain_commit_id=None,
        )
        assert materialized is not None
        self.assertTrue(validation.ok)
        self.assertEqual(materialized.store_revision, 2)


class PlotCognitionReplanContractTests(unittest.TestCase):
    def test_replan_proposal_validation(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        snapshot = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
        proposal = PlotCognitionReplanProposal(
            schema=REPLAN_PROPOSAL_SCHEMA,
            proposal_id=new_replan_proposal_id(),
            source_snapshot_id=snapshot.snapshot_id,
            source_snapshot_fingerprint=snapshot.authority_source_fingerprint,
            plot_cognition_scope_id=fixture.plot_cognition_scope_id,
            prior_store_revision=1,
            replan_rationale="Pursuit must change.",
            trigger_summary="Character refused reconciliation.",
            goals=(_goal_draft(goal_id="replacement"),),
            pressures=(),
            global_frame=None,
            superseded_goal_ids=("old-goal",),
        )
        validation = validate_replan_proposal_objective(
            proposal,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertTrue(validation.ok)

    def test_materialize_replan_overlay(self) -> None:
        fixture = _session()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        store.goals["old-goal"] = plot_goal_from_dict(_goal_draft(goal_id="old-goal"))
        snapshot = gather_update_source_snapshot(fixture, store, [], (fixture.hg_scene_id,))
        proposal = PlotCognitionReplanProposal(
            schema=REPLAN_PROPOSAL_SCHEMA,
            proposal_id=new_replan_proposal_id(),
            source_snapshot_id=snapshot.snapshot_id,
            source_snapshot_fingerprint=snapshot.authority_source_fingerprint,
            plot_cognition_scope_id=fixture.plot_cognition_scope_id,
            prior_store_revision=1,
            replan_rationale="New pursuit.",
            trigger_summary="Divergence.",
            goals=(_goal_draft(goal_id="new-goal"),),
            pressures=(),
            global_frame=None,
            superseded_goal_ids=("old-goal",),
        )
        evaluation = PlotCognitionReplanEvaluation(
            schema=REPLAN_EVALUATION_SCHEMA,
            evaluation_id=new_replan_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        authority = AssimilatedAuthority(schema=ASSIMILATED_AUTHORITY_SCHEMA, sessions=())
        materialized, validation = materialize_replan_overlay(
            store,
            proposal,
            evaluation,
            assimilated_authority=authority,
            through_domain_commit_id=None,
        )
        assert materialized is not None
        self.assertTrue(validation.ok)
        self.assertEqual(materialized.goals["old-goal"].activity_state, "inactive")
        self.assertIn("new-goal", materialized.goals)

    def test_forensic_handoff_outcomes(self) -> None:
        handoff = UpdateForensicHandoff()
        for outcome in (
            "semantic_update",
            "semantic_replan",
            "semantic_no_change",
            "objective_authority_unchanged",
            "endpoint_reconciliation",
        ):
            handoff.outcome = outcome  # type: ignore[assignment]
            self.assertEqual(handoff.outcome, outcome)


if __name__ == "__main__":
    unittest.main()

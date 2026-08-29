"""#63 Plot Cognition runtime orchestration tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_contract import StableReference  # noqa: E402
from domain_api.plot_cognition_orchestration_contract import (  # noqa: E402
    REGENERATION_GUIDANCE_SCHEMA,
    RegenerationGuidance,
)
from domain_api.plot_cognition_orchestration_service import (  # noqa: E402
    PlotCognitionOrchestrationService,
)
from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
    GLOBAL_PLOT_FRAME_SCHEMA,
    PLOT_GOAL_SCHEMA,
    CognitionApplicability,
    CreationProvenance,
    GlobalPlotFrame,
    GoalLineage,
    PlotGoal,
    new_frame_id,
    new_goal_id,
)
from domain_api.plot_cognition_overlay_repository import PlotCognitionOverlayRepository  # noqa: E402
from domain_api.plot_cognition_overlay_service import PlotCognitionOverlayService  # noqa: E402
from domain_api.plot_cognition_overlay_store import (  # noqa: E402
    BoundednessPolicy,
    OperativePlotCognitionView,
    PlotCognitionOverlayStore,
    empty_store,
)
from domain_api.plot_cognition_projection_batch import (  # noqa: E402
    CharacterProjectionSemanticResult,
    clear_prepared_batches_for_tests,
    finalize_character_projection_batch,
    prepare_character_projection_batch,
)
from domain_api.plot_cognition_projection_contract import (  # noqa: E402
    CharacterAdvisoryCandidate,
    ProjectionBudget,
    RegenerationCycleInput,
    SemanticEvaluationResult,
    frame_derived_character_candidate,
    global_goal_derived_character_candidate,
    new_candidate_id,
    overlay_goal_to_character_candidate,
)
from domain_api.plot_cognition_projection_semantic_safety import (  # noqa: E402
    DeterministicRuleBasedEpistemicEvaluator,
)
from domain_api.plot_cognition_projection_service import (  # noqa: E402
    project_character_candidates,
)
from domain_api.session_state import RoundFixture, initialize_live_session  # noqa: E402
from domain_api.storyteller_contract import advisory_package_to_dict  # noqa: E402
from domain_api.storyteller_round_packaging import storyteller_contributions_for_consumer  # noqa: E402
from domain.tests.test_storyteller_packaging_s3b import (  # noqa: E402
    _binding,
    _fixture,
    _package,
)

TEST_BUDGET = ProjectionBudget(max_evaluation_candidates=4, max_projection_candidates=2)
TEST_POLICY = BoundednessPolicy(max_active_goals=4, max_active_pressures=4)


def _session_with_event(*, known_by: list[str]):
    from datetime import datetime, timezone

    from domain.modules.continuity_state_public_event import PublicEvent  # noqa: E402

    fixture = initialize_live_session(cast=["Alice", "Bob"], plot_cognition_scope_id="scope-orch")
    fixture.manager.public_events.append(
        PublicEvent(
            event_id="evt-secret",
            timestamp=datetime.now(timezone.utc),
            event_type="dialogue",
            participants=["Bob"],
            summary="Bob whispered the vault code.",
            turn_index=1,
            known_by=list(known_by),
        )
    )
    return fixture


def _character_goal(*, character_id: str = "Alice", direction: str = "Find the key.") -> PlotGoal:
    return PlotGoal(
        schema=PLOT_GOAL_SCHEMA,
        goal_id=new_goal_id(),
        intended_direction=direction,
        basis_note=None,
        basis_refs=(
            StableReference(ref_kind="character_card", stable_ref=f"{character_id.lower()}:goals"),
        ),
        applicability=CognitionApplicability(
            applicability_kind="character",
            primary_character_id=character_id,
            involved_character_ids=(character_id,),
        ),
        planning_horizon="MEDIUM",
        creation_provenance=CreationProvenance(source="storyteller"),
        lineage=GoalLineage(),
        activity_state="active",
    )


def _overlay_service() -> PlotCognitionOverlayService:
    tmp = tempfile.mkdtemp(prefix="hg-orch-overlay-")
    repo = PlotCognitionOverlayRepository(Path(tmp))
    return PlotCognitionOverlayService(repo)


def _round(fixture) -> RoundFixture:
    return RoundFixture(
        hg_round_id="round-orch-1",
        hg_scene_id=fixture.hg_scene_id,
        turn_index=1,
    )


def _seed_overlay(
    service: PlotCognitionOverlayService,
    fixture,
    *,
    goals: tuple[PlotGoal, ...] = (),
    frame: GlobalPlotFrame | None = None,
) -> OperativePlotCognitionView:
    scope_id = str(fixture.plot_cognition_scope_id)
    store = empty_store(scope_id)
    store.goals = {goal.goal_id: goal for goal in goals}
    store.active_frame = frame
    service.replace_snapshot(scope_id, store, expected_revision=0, policy=TEST_POLICY)
    loaded = service.load(scope_id, policy=TEST_POLICY)
    assert loaded.store is not None
    return service.operative_view(loaded.store, policy=TEST_POLICY, load_status=loaded.status)


class PlotCognitionOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_prepared_batches_for_tests()

    def tearDown(self) -> None:
        clear_prepared_batches_for_tests()

    def test_split_prepare_finalize_without_sync_evaluator(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-split",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        self.assertEqual(len(prepared.batch.items), 1)
        pass_id = prepared.batch.items[0].evaluation_pass_id
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=pass_id,
                    candidate_id=candidate.candidate_id,
                    semantic=SemanticEvaluationResult(verdict="pass", rationale="ok"),
                    regeneration_guidance=None,
                ),
            ),
            hg_round_id="round-1",
            turn_index=1,
        )
        self.assertEqual(len(finalized.contributions), 1)

    def test_stale_prepared_batch_rejected(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-stale",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        pass_id = prepared.batch.items[0].evaluation_pass_id
        with self.assertRaises(ValueError):
            finalize_character_projection_batch(
                fixture,
                batch_id=prepared.batch.batch_id,
                semantic_results=(
                    CharacterProjectionSemanticResult(
                        evaluation_pass_id=pass_id,
                        candidate_id=candidate.candidate_id,
                        semantic=SemanticEvaluationResult(verdict="pass", rationale="ok"),
                        regeneration_guidance=None,
                    ),
                ),
                hg_round_id="round-2",
                turn_index=2,
            )

    def test_epistemic_context_contains_authorized_text(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal(direction="Seek reconciliation."))
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-epi",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        envelope = prepared.batch.items[0].epistemic_context
        joined = "\n".join(envelope.semantic_material)
        self.assertIn("reconciliation", joined.lower())
        self.assertIn("Proposed candidate text", joined)

    def test_snapshot_ids_not_used_as_semantic_material(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-digest",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        envelope = prepared.batch.items[0].epistemic_context
        for material in envelope.semantic_material:
            self.assertNotEqual(material.strip(), envelope.known_by_snapshot_id)
            self.assertNotEqual(material.strip(), envelope.visibility_digest)

    def test_withheld_private_text_absent_from_evaluator_context(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = CharacterAdvisoryCandidate(
            candidate_id=new_candidate_id(),
            text="Alice may consider next steps.",
            source_kind="overlay_character_candidate",
            lineage=("l1",),
            basis_refs=(
                StableReference(ref_kind="character_card", stable_ref="alice:goals"),
                StableReference(ref_kind="character_card", stable_ref="bob:secrets"),
            ),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
        )
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-withheld",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        joined = "\n".join(prepared.batch.items[0].epistemic_context.semantic_material).lower()
        self.assertNotIn("bob:secrets", joined)
        self.assertTrue(prepared.batch.items[0].epistemic_context.withheld_basis_index)

    def test_rewrite_requires_structured_regeneration_guidance(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-rewrite",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        item = prepared.batch.items[0]
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=item.evaluation_pass_id,
                    candidate_id=item.candidate.candidate_id,
                    semantic=SemanticEvaluationResult(
                        verdict="rewrite_required",
                        rationale="needs rewrite",
                        forensic_rationale="forensic detail",
                    ),
                    regeneration_guidance=None,
                ),
            ),
            hg_round_id="round-1",
            turn_index=1,
        )
        self.assertEqual(finalized.contributions, ())

    def test_valid_regeneration_guidance_surfaces_pending(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-pending",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        item = prepared.batch.items[0]
        guidance = RegenerationGuidance(
            schema=REGENERATION_GUIDANCE_SCHEMA,
            violation_class="over_specific_prospective",
            safe_constraints=("Keep advice prospective.",),
        )
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=item.evaluation_pass_id,
                    candidate_id=item.candidate.candidate_id,
                    semantic=SemanticEvaluationResult(
                        verdict="rewrite_required",
                        rationale="rewrite",
                        forensic_rationale="forensic",
                        regeneration_guidance=guidance,
                    ),
                    regeneration_guidance=guidance,
                ),
            ),
            hg_round_id="round-1",
            turn_index=1,
        )
        self.assertEqual(len(finalized.pending_regenerations), 1)
        self.assertNotIn("forensic", finalized.pending_regenerations[0].regeneration_guidance.to_dict())

    def test_provenance_paths_remain_distinct(self) -> None:
        goal = _character_goal()
        frame = GlobalPlotFrame(
            schema=GLOBAL_PLOT_FRAME_SCHEMA,
            frame_id=new_frame_id(),
            direction_sense="Rising tension.",
            pacing_note="Fast.",
            cross_character_note="Hidden alliances.",
            opportunity_note="Window opening.",
            basis_refs=(),
            activity_state="active",
            superseded_by_frame_id=None,
            creation_provenance=CreationProvenance(source="storyteller"),
        )
        overlay_candidate = overlay_goal_to_character_candidate(goal)
        global_derived = global_goal_derived_character_candidate(
            goal,
            text="Alice may watch ensemble dynamics.",
            character_id="Alice",
        )
        frame_derived = frame_derived_character_candidate(frame, text="Alice may sense rising tension.")
        self.assertEqual(overlay_candidate.source_kind, "overlay_goal")
        self.assertEqual(global_derived.source_kind, "overlay_character_candidate")
        self.assertEqual(frame_derived.source_kind, "overlay_character_candidate")
        self.assertNotEqual(global_derived.lineage, frame_derived.lineage)

    def test_overlay_extraction_still_requires_layer_b(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        view = _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        rnd = _round(fixture)
        contributions = storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id="m-no-sem",
            consumer_target="character",
            character_id="Alice",
            overlay_service=service,
            overlay_view=view,
            orchestration_service=orch,
        )
        self.assertEqual(contributions, ())

    def test_global_cognition_never_directly_projected(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        global_goal = PlotGoal(
            schema=PLOT_GOAL_SCHEMA,
            goal_id=new_goal_id(),
            intended_direction="Escalate ensemble conflict.",
            basis_note="secret",
            basis_refs=(),
            applicability=CognitionApplicability(
                applicability_kind="global",
                primary_character_id=None,
                involved_character_ids=(),
            ),
            planning_horizon="LONG",
            creation_provenance=CreationProvenance(source="storyteller"),
            lineage=GoalLineage(),
            activity_state="active",
        )
        direct = CharacterAdvisoryCandidate(
            candidate_id=global_goal.goal_id,
            text=global_goal.intended_direction,
            source_kind="overlay_goal",
            lineage=(global_goal.goal_id,),
            basis_refs=global_goal.basis_refs,
            applicability=global_goal.applicability,
        )
        result = project_character_candidates(
            fixture,
            manifest_id="m-global",
            character_id="Alice",
            candidates=(direct,),
            budget=TEST_BUDGET,
            evaluator=DeterministicRuleBasedEpistemicEvaluator(),
        )
        self.assertEqual(result.contributions, ())

    def test_no_deterministic_semantic_fallback_in_production_path(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        view = _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        rnd = _round(fixture)
        contributions = storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id="m-failclosed",
            consumer_target="character",
            character_id="Alice",
            overlay_service=service,
            overlay_view=view,
            orchestration_service=orch,
            projection_batch_id="missing-batch",
            projection_semantic_results=[],
        )
        self.assertEqual(contributions, ())

    def test_director_overlay_live_when_fresh(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        view = _seed_overlay(fixture=fixture, service=service, goals=(_character_goal(),))
        rnd = _round(fixture)
        contributions = storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id="m-director",
            consumer_target="director",
            overlay_service=service,
            overlay_view=view,
        )
        self.assertTrue(any("Find the key" in item.content for item in contributions))

    def test_stale_overlay_withheld_for_director(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        view = _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        orch.record_post_commit_pending_work(fixture, domain_commit_id="commit-1")
        rnd = _round(fixture)
        contributions = storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id="m-stale-dir",
            consumer_target="director",
            overlay_service=service,
            overlay_view=view,
            orchestration_service=orch,
        )
        overlay_text = "\n".join(item.content for item in contributions if "Find the key" in item.content)
        self.assertEqual(overlay_text, "")

    def test_stale_overlay_character_advice_withheld(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        view = _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        orch.record_post_commit_pending_work(fixture, domain_commit_id="commit-2")
        rnd = _round(fixture)
        contributions = storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id="m-stale-char",
            consumer_target="character",
            character_id="Alice",
            overlay_service=service,
            overlay_view=view,
            orchestration_service=orch,
        )
        self.assertEqual(contributions, ())

    def test_pending_work_persists_in_overlay_store(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        pending = orch.record_post_commit_pending_work(fixture, domain_commit_id="commit-3")
        assert pending is not None
        loaded = service.load(str(fixture.plot_cognition_scope_id), policy=TEST_POLICY)
        assert loaded.store is not None
        self.assertIsNotNone(loaded.store.pending_work)
        status = orch.assess_overlay_freshness(fixture)
        self.assertFalse(status.fresh)

    def test_post_commit_creates_freshness_obligation(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        self.assertTrue(orch.assess_overlay_freshness(fixture).fresh)
        orch.record_post_commit_pending_work(fixture, domain_commit_id="commit-4")
        self.assertFalse(orch.assess_overlay_freshness(fixture).fresh)

    def test_regeneration_at_most_one_attempt(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        original = overlay_goal_to_character_candidate(
            _character_goal(direction="Needs rewrite [[REWRITE]]")
        )
        regenerated = CharacterAdvisoryCandidate(
            candidate_id="regen-1",
            text="Alice may consider calm next steps.",
            source_kind=original.source_kind,
            lineage=original.lineage,
            basis_refs=original.basis_refs,
            applicability=original.applicability,
        )
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-regen",
            character_id="Alice",
            candidates=(original,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        item = prepared.batch.items[0]
        guidance = RegenerationGuidance(
            schema=REGENERATION_GUIDANCE_SCHEMA,
            violation_class="other",
            safe_constraints=("Avoid rewrite markers.",),
        )
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=item.evaluation_pass_id,
                    candidate_id=item.candidate.candidate_id,
                    semantic=SemanticEvaluationResult(
                        verdict="rewrite_required",
                        rationale="rewrite",
                        regeneration_guidance=guidance,
                    ),
                    regeneration_guidance=guidance,
                ),
            ),
            hg_round_id="round-1",
            turn_index=1,
            regeneration_inputs={
                original.candidate_id: RegenerationCycleInput(
                    original_candidate=original,
                    evaluator_result=SemanticEvaluationResult(
                        verdict="rewrite_required",
                        rationale="rewrite",
                    ),
                    regenerated_candidate=regenerated,
                )
            },
            second_pass_results={
                item.evaluation_pass_id: SemanticEvaluationResult(verdict="pass", rationale="ok"),
            },
        )
        self.assertEqual(len(finalized.contributions), 1)

    def test_second_layer_b_failure_withholds(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        original = overlay_goal_to_character_candidate(_character_goal())
        regenerated = CharacterAdvisoryCandidate(
            candidate_id="regen-fail",
            text="Leaked bob:secrets content.",
            source_kind=original.source_kind,
            lineage=original.lineage,
            basis_refs=original.basis_refs,
            applicability=original.applicability,
        )
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-regen-fail",
            character_id="Alice",
            candidates=(original,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        item = prepared.batch.items[0]
        guidance = RegenerationGuidance(
            schema=REGENERATION_GUIDANCE_SCHEMA,
            violation_class="withheld_basis_exposure",
            safe_constraints=("Do not expose withheld basis.",),
        )
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=item.evaluation_pass_id,
                    candidate_id=item.candidate.candidate_id,
                    semantic=SemanticEvaluationResult(
                        verdict="rewrite_required",
                        rationale="rewrite",
                        regeneration_guidance=guidance,
                    ),
                    regeneration_guidance=guidance,
                ),
            ),
            hg_round_id="round-1",
            turn_index=1,
            regeneration_inputs={
                original.candidate_id: RegenerationCycleInput(
                    original_candidate=original,
                    evaluator_result=SemanticEvaluationResult(verdict="rewrite_required", rationale="r"),
                    regenerated_candidate=regenerated,
                )
            },
            second_pass_results={
                item.evaluation_pass_id: SemanticEvaluationResult(verdict="withhold", rationale="still leaky"),
            },
        )
        self.assertEqual(finalized.contributions, ())

    def test_provider_failure_fails_closed(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-unavail",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        item = prepared.batch.items[0]
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=item.evaluation_pass_id,
                    candidate_id=item.candidate.candidate_id,
                    semantic=SemanticEvaluationResult(
                        verdict="evaluator_unavailable",
                        rationale="timeout",
                    ),
                    regeneration_guidance=None,
                ),
            ),
            hg_round_id="round-1",
            turn_index=1,
        )
        self.assertEqual(finalized.contributions, ())

    def test_forensic_handoff_contains_lineage(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-forensic",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id="round-1",
            turn_index=1,
        )
        item = prepared.batch.items[0]
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=(
                CharacterProjectionSemanticResult(
                    evaluation_pass_id=item.evaluation_pass_id,
                    candidate_id=item.candidate.candidate_id,
                    semantic=SemanticEvaluationResult(verdict="pass", rationale="ok"),
                    regeneration_guidance=None,
                    inference_evidence_id="evidence-1",
                ),
            ),
            hg_round_id="round-1",
            turn_index=1,
        )
        payload = finalized.forensic.to_dict()
        self.assertGreaterEqual(payload["projected_count"], 1)
        self.assertTrue(payload["records"])

    def test_model_a_distinct_from_overlay_in_collection(self) -> None:
        fixture = _fixture()
        rnd = _round(fixture)
        rnd.storyteller_advisory_package = advisory_package_to_dict(_package())
        service = _overlay_service()
        view = _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        candidates = orch.collect_character_candidates(
            fixture,
            rnd,
            character_id="Alice",
            overlay_view=view,
            include_model_a=True,
        )
        kinds = {item.source_kind for item in candidates}
        self.assertTrue(any(kind.startswith("model_a") or kind.startswith("overlay") for kind in kinds))

    def test_fail_closed_regression_without_evaluator(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = overlay_goal_to_character_candidate(_character_goal())
        result = project_character_candidates(
            fixture,
            manifest_id="m-missing-eval",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(result.contributions, ())
        self.assertTrue(
            any(record.outcome == "semantic_evaluator_unavailable" for record in result.forensic.records)
        )


class PlotCognitionPostCommitPlanningTests(unittest.TestCase):
    def test_plan_routes_reconciliation_when_authority_missing(self) -> None:
        from domain_api.plot_cognition_orchestration_api import plan_post_commit_plot_cognition_work

        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        _seed_overlay(service, fixture, goals=(_character_goal(),))
        orch = PlotCognitionOrchestrationService(service)
        orch.record_post_commit_pending_work(fixture, domain_commit_id="commit-plan-1")

        class _Kernel:
            cognition = type(
                "Cognition",
                (),
                {
                    "plot_cognition_overlay": service,
                    "plot_cognition_update": __import__(
                        "domain_api.plot_cognition_update_service",
                        fromlist=["PlotCognitionUpdateService"],
                    ).PlotCognitionUpdateService(service),
                    "plot_cognition_initialization": None,
                },
            )()

        plan = plan_post_commit_plot_cognition_work(_Kernel(), fixture)
        self.assertEqual(plan["operation"], "reconciliation")

    def test_post_commit_plan_update_then_finalize_clears_pending(self) -> None:
        from domain_api.plot_cognition_orchestration_api import plan_post_commit_plot_cognition_work
        from domain_api.plot_cognition_update_contract import (
            UPDATE_EVALUATION_SCHEMA,
            new_evaluation_id,
        )
        from domain_api.plot_cognition_update_service import PlotCognitionUpdateService
        from domain_api.plot_cognition_update_sources import gather_update_source_snapshot
        from domain.tests.test_plot_cognition_update_replan import (
            _initialized_store,
            _update_proposal,
        )
        from domain_api.plot_cognition_update_contract import PlotCognitionUpdateEvaluation
        from domain_api.plot_cognition_lifecycle_api import finalize_plot_cognition_update

        fixture = _session_with_event(known_by=["Alice"])
        service = _overlay_service()
        store = _initialized_store(fixture, service)
        update_svc = PlotCognitionUpdateService(service)
        update_svc.first_reconciliation(fixture, store, TEST_POLICY)
        orch = PlotCognitionOrchestrationService(service)
        orch.record_post_commit_pending_work(fixture, domain_commit_id="commit-e2e-1")
        fixture.continuity_version += 1
        fixture.manager.scene_state.location = "Changed Hall"
        self.assertFalse(orch.assess_overlay_freshness(fixture).fresh)

        class _Kernel:
            cognition = type(
                "Cognition",
                (),
                {
                    "plot_cognition_overlay": service,
                    "plot_cognition_update": update_svc,
                    "plot_cognition_initialization": None,
                },
            )()

        plan = plan_post_commit_plot_cognition_work(_Kernel(), fixture)
        self.assertEqual(plan["operation"], "semantic_update")
        loaded = service.load(str(fixture.plot_cognition_scope_id), policy=TEST_POLICY)
        assert loaded.store is not None
        proposal = _update_proposal(fixture, loaded.store)
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="no_change",
            findings=(),
            no_change_rationale="No cognition adjustment warranted.",
        )
        finalized = finalize_plot_cognition_update(
            _Kernel(),
            fixture,
            {
                "proposal": proposal.to_dict(),
                "evaluation": evaluation.to_dict(),
            },
        )
        self.assertTrue(finalized["accepted"])
        self.assertTrue(orch.assess_overlay_freshness(fixture).fresh)

    def test_plan_routes_initialization_when_overlay_absent(self) -> None:
        from domain_api.cognition_composition import CognitionComposition
        from domain_api.plot_cognition_orchestration_api import plan_post_commit_plot_cognition_work
        from domain_api.session_state import initialize_live_session

        fixture = initialize_live_session(
            cast=["Alice"],
            plot_cognition_scope_id="scope-absent-init",
        )
        tmpdir = tempfile.mkdtemp()
        try:
            repo = PlotCognitionOverlayRepository(tmpdir)
            composition = CognitionComposition.for_tests(
                plot_cognition_overlay_repository=repo,
            )

            class _Kernel:
                cognition = composition

            plan = plan_post_commit_plot_cognition_work(_Kernel(), fixture)
            self.assertEqual(plan["operation"], "initialization")
            self.assertTrue(plan["accepted"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

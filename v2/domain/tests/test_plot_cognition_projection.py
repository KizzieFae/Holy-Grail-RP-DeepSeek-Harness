"""#62 Plot Cognition consumer projection and epistemic isolation tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_contract import StableReference  # noqa: E402
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
    new_frame_id,
    new_goal_id,
    new_pressure_id,
)
from domain_api.plot_cognition_overlay_store import OperativePlotCognitionView  # noqa: E402
from domain_api.plot_cognition_projection_contract import (  # noqa: E402
    MODEL_A_CHARACTER_SCOPE_REF_KIND,
    CharacterAdvisoryCandidate,
    ProjectionBudget,
    RegenerationCycleInput,
    frame_derived_character_candidate,
    global_goal_derived_character_candidate,
    new_candidate_id,
    overlay_goal_to_character_candidate,
    projection_invalidation_predicates_match,
)
from domain_api.plot_cognition_projection_semantic_safety import (  # noqa: E402
    DeterministicRuleBasedEpistemicEvaluator,
)
from domain_api.plot_cognition_projection_service import (  # noqa: E402
    assess_structural_eligibility,
    build_projection_invalidation_context,
    collect_overlay_character_candidates,
    model_a_has_structural_character_evidence,
    project_character_candidates,
    project_director_overlay,
    apply_evaluation_budget,
)
from domain_api.plot_cognition_projection_contract import SemanticEvaluationResult  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from domain_api.storyteller_packaging_mapper import map_storyteller_package_to_contributions  # noqa: E402
from domain.tests.test_storyteller_packaging_s3b import (  # noqa: E402
    _binding,
    _character_scope_ref,
    _fixture,
    _package,
)
from domain_api.storyteller_contract import (  # noqa: E402
    NarrativeObservation,
    NarrativeTension,
)

TEST_BUDGET = ProjectionBudget(max_evaluation_candidates=3, max_projection_candidates=2)


def _session_with_event(*, known_by: list[str]):
    from datetime import datetime, timezone

    from domain.modules.continuity_state_public_event import PublicEvent  # noqa: E402

    fixture = initialize_live_session(cast=["Alice", "Bob"], plot_cognition_scope_id="scope-proj")
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


def _global_goal() -> PlotGoal:
    return PlotGoal(
        schema=PLOT_GOAL_SCHEMA,
        goal_id=new_goal_id(),
        intended_direction="Escalate ensemble conflict.",
        basis_note="Storyteller ensemble read.",
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


def _relational_pressure() -> UnresolvedNarrativePressure:
    return UnresolvedNarrativePressure(
        schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
        pressure_id=new_pressure_id(),
        pressure_text="Bob distrusts Alice.",
        dramatic_rationale="Private relational strain.",
        basis_note=None,
        basis_refs=(
            StableReference(ref_kind="character_card", stable_ref="bob:relationships:Alice"),
        ),
        continuity_issue_refs=(),
        applicability=CognitionApplicability(
            applicability_kind="relational",
            primary_character_id="Bob",
            involved_character_ids=("Bob", "Alice"),
        ),
        creation_provenance=CreationProvenance(source="storyteller"),
        activity_state="active",
    )


def _global_frame() -> GlobalPlotFrame:
    return GlobalPlotFrame(
        schema=GLOBAL_PLOT_FRAME_SCHEMA,
        frame_id=new_frame_id(),
        direction_sense="Rising tension across the cast.",
        pacing_note="Accelerating.",
        cross_character_note="Hidden alliances may surface.",
        opportunity_note="Confrontation window opening.",
        basis_refs=(),
        activity_state="active",
        superseded_by_frame_id=None,
        creation_provenance=CreationProvenance(source="storyteller"),
    )


class PlotCognitionProjectionContractTests(unittest.TestCase):
    def test_character_name_in_hidden_source_text_does_not_create_eligibility(self) -> None:
        package = _package(
            observations=(
                NarrativeObservation(
                    text="Alice's secret motive is revenge.",
                    evidence_refs=(_character_scope_ref("Bob"),),
                ),
            )
        )
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="m1",
            consumer_target="character",
            binding=_binding(pipeline_stage="character"),
            character_id="Alice",
            fixture=_fixture(),
        )
        self.assertEqual(result.contributions, ())

    def test_relevance_without_epistemic_eligibility_is_withheld(self) -> None:
        fixture = _session_with_event(known_by=["Bob"])
        pressure = _relational_pressure()
        candidate = CharacterAdvisoryCandidate(
            candidate_id=pressure.pressure_id,
            text=pressure.pressure_text,
            source_kind="overlay_pressure",
            lineage=(pressure.pressure_id,),
            basis_refs=pressure.basis_refs,
            applicability=pressure.applicability,
            creation_provenance=pressure.creation_provenance,
        )
        structural = assess_structural_eligibility(
            fixture,
            candidate=candidate,
            character_id="Alice",
        )
        self.assertFalse(structural.eligible)
        self.assertEqual(structural.code, "ineligible_epistemic")

    def test_hidden_basis_safe_prospective_candidate_can_project(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        goal = PlotGoal(
            schema=PLOT_GOAL_SCHEMA,
            goal_id=new_goal_id(),
            intended_direction="Consider whether reconciliation remains possible.",
            basis_note="Mixed basis.",
            basis_refs=(
                StableReference(ref_kind="character_card", stable_ref="alice:goals"),
                StableReference(ref_kind="character_card", stable_ref="bob:secrets"),
            ),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            planning_horizon="SHORT",
            creation_provenance=CreationProvenance(source="storyteller"),
            lineage=GoalLineage(),
            activity_state="active",
        )
        candidate = overlay_goal_to_character_candidate(goal)
        result = project_character_candidates(
            fixture,
            manifest_id="m-prospective",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(len(result.contributions), 1)
        self.assertIn("reconciliation", result.contributions[0].content)
        outcomes = {record.outcome for record in result.forensic.records}
        self.assertIn("projected_prospective", outcomes)

    def test_prospective_candidate_leaking_hidden_salience_is_rejected(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = CharacterAdvisoryCandidate(
            candidate_id=new_candidate_id(),
            text="Alice should confront Bob about his hidden vault secret.",
            source_kind="overlay_character_candidate",
            lineage=("lineage-1",),
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
        result = project_character_candidates(
            fixture,
            manifest_id="m-leak",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(result.contributions, ())
        self.assertTrue(
            any(record.outcome == "semantic_withhold" for record in result.forensic.records)
        )

    def test_partial_basis_cannot_expose_withheld_facets(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = CharacterAdvisoryCandidate(
            candidate_id=new_candidate_id(),
            text="Alice knows bob:secrets and must act on it.",
            source_kind="overlay_character_candidate",
            lineage=("lineage-2",),
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
        result = project_character_candidates(
            fixture,
            manifest_id="m-partial",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(result.contributions, ())

    def test_third_party_private_relational_cognition_remains_isolated(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        pressure = _relational_pressure()
        candidate = overlay_goal_to_character_candidate(_character_goal())
        bob_private = CharacterAdvisoryCandidate(
            candidate_id=new_candidate_id(),
            text="Bob's private distrust should guide Alice.",
            source_kind="overlay_pressure",
            lineage=(pressure.pressure_id,),
            basis_refs=pressure.basis_refs,
            applicability=pressure.applicability,
        )
        result = project_character_candidates(
            fixture,
            manifest_id="m-rel",
            character_id="Alice",
            candidates=(candidate, bob_private),
            budget=TEST_BUDGET,
        )
        joined = "\n".join(item.content for item in result.contributions)
        self.assertNotIn("Bob's private distrust", joined)

    def test_character_player_originated_lineage_preserved(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = CharacterAdvisoryCandidate(
            candidate_id="cand-lineage",
            text="Alice may pursue clarity about the treaty.",
            source_kind="overlay_character_candidate",
            lineage=("goal-parent", "frame-parent"),
            basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
            creation_provenance=CreationProvenance(source="character_committed"),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
        )
        result = project_character_candidates(
            fixture,
            manifest_id="m-lineage",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(result.contributions[0].knowledge_ids, ("goal-parent", "frame-parent"))

    def test_known_by_change_alters_reprojection_result(self) -> None:
        fixture = _session_with_event(known_by=["Bob"])
        candidate = CharacterAdvisoryCandidate(
            candidate_id="evt-based",
            text="Alice may respond to the whisper she overheard.",
            source_kind="overlay_character_candidate",
            lineage=("evt-secret",),
            basis_refs=(StableReference(ref_kind="public_event", stable_ref="evt-secret"),),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
        )
        first = project_character_candidates(
            fixture,
            manifest_id="m-kb1",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        fixture.manager.public_events[0].known_by.append("Alice")
        second = project_character_candidates(
            fixture,
            manifest_id="m-kb2",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(first.contributions, ())
        self.assertEqual(len(second.contributions), 1)

    def test_frame_derived_safe_candidate_projects_while_frame_never_does(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        frame = _global_frame()
        view = OperativePlotCognitionView(goals=(), pressures=(), active_frame=frame)
        director = project_director_overlay(view, manifest_id="m-dir")
        self.assertTrue(any("Rising tension" in item.content for item in director))
        safe = frame_derived_character_candidate(
            frame,
            text="Alice may notice tensions rising without learning hidden alliances.",
        )
        char_result = project_character_candidates(
            fixture,
            manifest_id="m-frame-cand",
            character_id="Alice",
            candidates=(safe,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(len(char_result.contributions), 1)
        raw_frame_candidate = CharacterAdvisoryCandidate(
            candidate_id=frame.frame_id,
            text=frame.direction_sense,
            source_kind="overlay_frame",
            lineage=(frame.frame_id,),
            basis_refs=frame.basis_refs,
            creation_provenance=frame.creation_provenance,
        )
        blocked = assess_structural_eligibility(
            fixture,
            candidate=raw_frame_candidate,
            character_id="Alice",
        )
        self.assertEqual(blocked.code, "ineligible_frame_direct")

    def test_global_plot_goal_not_directly_projected_to_character(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        goal = _global_goal()
        view = OperativePlotCognitionView(goals=(goal,), pressures=(), active_frame=None)
        candidates = collect_overlay_character_candidates(view, character_id="Alice")
        self.assertEqual(candidates, ())
        direct = overlay_goal_to_character_candidate(goal)
        structural = assess_structural_eligibility(
            fixture,
            candidate=direct,
            character_id="Alice",
        )
        self.assertEqual(structural.code, "ineligible_global_direct")
        derived = global_goal_derived_character_candidate(
            goal,
            text="Alice may feel rising pressure without learning ensemble plans.",
            character_id="Alice",
        )
        derived_result = project_character_candidates(
            fixture,
            manifest_id="m-global-derived",
            character_id="Alice",
            candidates=(derived,),
            budget=TEST_BUDGET,
        )
        self.assertEqual(len(derived_result.contributions), 1)

    def test_model_a_insufficient_evidence_fails_closed(self) -> None:
        package = _package(
            observations=(
                NarrativeObservation(
                    text="Alice feels uneasy.",
                    evidence_refs=(_character_scope_ref("Bob"),),
                ),
            )
        )
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="m-insufficient",
            consumer_target="character",
            binding=_binding(pipeline_stage="character"),
            character_id="Alice",
            fixture=_fixture(),
        )
        self.assertEqual(result.contributions, ())

    def test_substring_applicability_cannot_authorize_model_a_character_projection(self) -> None:
        package = _package(
            observations=(
                NarrativeObservation(
                    text="Alice's trust fracture is central.",
                    evidence_refs=(_character_scope_ref("Bob"),),
                ),
            )
        )
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id="m-substring",
            consumer_target="character",
            binding=_binding(pipeline_stage="character"),
            character_id="Alice",
            fixture=_fixture(),
        )
        self.assertEqual(result.contributions, ())
        self.assertFalse(
            model_a_has_structural_character_evidence(
                (_character_scope_ref("Bob"),),
                character_id="Alice",
            )
        )

    def test_evaluation_budget_exclusions_are_deterministic_and_forensic(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidates = tuple(
            CharacterAdvisoryCandidate(
                candidate_id=f"cand-{index}",
                text=f"Safe advisory option {index}.",
                source_kind="overlay_character_candidate",
                lineage=(f"line-{index}",),
                basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
                applicability=CognitionApplicability(
                    applicability_kind="character",
                    primary_character_id="Alice",
                    involved_character_ids=("Alice",),
                ),
            )
            for index in range(5)
        )
        budget = ProjectionBudget(max_evaluation_candidates=2, max_projection_candidates=5)
        included, excluded = apply_evaluation_budget(candidates, budget)
        self.assertEqual(len(included), 2)
        self.assertEqual(len(excluded), 3)
        result = project_character_candidates(
            fixture,
            manifest_id="m-eval-budget",
            character_id="Alice",
            candidates=candidates,
            budget=budget,
        )
        excluded_records = [
            record for record in result.forensic.records if record.outcome == "evaluation_budget_excluded"
        ]
        self.assertEqual(len(excluded_records), 3)

    def test_projection_budget_exclusions_are_deterministic_and_forensic(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidates = tuple(
            CharacterAdvisoryCandidate(
                candidate_id=f"proj-{index}",
                text=f"Approved advisory {index}.",
                source_kind="overlay_character_candidate",
                lineage=(f"pl-{index}",),
                basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
                applicability=CognitionApplicability(
                    applicability_kind="character",
                    primary_character_id="Alice",
                    involved_character_ids=("Alice",),
                ),
            )
            for index in range(4)
        )
        budget = ProjectionBudget(max_evaluation_candidates=4, max_projection_candidates=2)
        result = project_character_candidates(
            fixture,
            manifest_id="m-proj-budget",
            character_id="Alice",
            candidates=candidates,
            budget=budget,
        )
        self.assertEqual(len(result.contributions), 2)
        excluded_records = [
            record for record in result.forensic.records if record.outcome == "projection_budget_excluded"
        ]
        self.assertEqual(len(excluded_records), 2)

    def test_semantic_evaluator_unavailable_fails_closed(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = CharacterAdvisoryCandidate(
            candidate_id="unavail",
            text="Safe text.",
            source_kind="overlay_character_candidate",
            lineage=("l1",),
            basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
        )
        result = project_character_candidates(
            fixture,
            manifest_id="m-unavail",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            evaluator=DeterministicRuleBasedEpistemicEvaluator(unavailable=True),
        )
        self.assertEqual(result.contributions, ())
        self.assertTrue(
            any(record.outcome == "semantic_evaluator_unavailable" for record in result.forensic.records)
        )

    def test_one_bounded_regeneration_cycle_is_reconstructable(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        original = CharacterAdvisoryCandidate(
            candidate_id="rewrite-me",
            text="Needs rewrite [[REWRITE]]",
            source_kind="overlay_character_candidate",
            lineage=("rw-1",),
            basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
        )
        regenerated = CharacterAdvisoryCandidate(
            candidate_id="rewrite-me-regen",
            text="Alice may consider next steps calmly.",
            source_kind="overlay_character_candidate",
            lineage=("rw-1",),
            basis_refs=original.basis_refs,
            applicability=original.applicability,
        )
        result = project_character_candidates(
            fixture,
            manifest_id="m-regen",
            character_id="Alice",
            candidates=(original,),
            budget=TEST_BUDGET,
            regeneration_inputs={
                "rewrite-me": RegenerationCycleInput(
                    original_candidate=original,
                    evaluator_result=SemanticEvaluationResult(
                        verdict="rewrite_required",
                        rationale="rewrite marker",
                    ),
                    regenerated_candidate=regenerated,
                )
            },
        )
        regen_records = [
            record for record in result.forensic.records if record.outcome == "regenerated_candidate_passed"
        ]
        self.assertEqual(len(regen_records), 1)
        self.assertEqual(regen_records[0].regenerated_text, regenerated.text)
        self.assertEqual(len(result.contributions), 1)

    def test_failed_regenerated_candidate_is_withheld(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        original = CharacterAdvisoryCandidate(
            candidate_id="rewrite-fail",
            text="Needs rewrite [[REWRITE]]",
            source_kind="overlay_character_candidate",
            lineage=("rw-2",),
            basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
        )
        regenerated = CharacterAdvisoryCandidate(
            candidate_id="rewrite-fail-regen",
            text="Still leaks [[LEAK:hidden vault]]",
            source_kind="overlay_character_candidate",
            lineage=("rw-2",),
            basis_refs=original.basis_refs,
            applicability=original.applicability,
        )
        result = project_character_candidates(
            fixture,
            manifest_id="m-regen-fail",
            character_id="Alice",
            candidates=(original,),
            budget=TEST_BUDGET,
            regeneration_inputs={
                "rewrite-fail": RegenerationCycleInput(
                    original_candidate=original,
                    evaluator_result=SemanticEvaluationResult(
                        verdict="rewrite_required",
                        rationale="rewrite marker",
                    ),
                    regenerated_candidate=regenerated,
                )
            },
        )
        self.assertEqual(result.contributions, ())
        self.assertTrue(
            any(record.outcome == "regenerated_candidate_failed" for record in result.forensic.records)
        )

    def test_director_global_projection_does_not_weaken_character_safety(self) -> None:
        frame = _global_frame()
        goal = _global_goal()
        view = OperativePlotCognitionView(goals=(goal,), pressures=(), active_frame=frame)
        director = project_director_overlay(view, manifest_id="m-dir-safe")
        self.assertGreaterEqual(len(director), 2)
        fixture = _session_with_event(known_by=["Alice"])
        char_candidates = collect_overlay_character_candidates(view, character_id="Alice")
        self.assertEqual(char_candidates, ())

    def test_prompt_rendering_cannot_append_unapproved_raw_source_cognition(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        candidate = CharacterAdvisoryCandidate(
            candidate_id="render-boundary",
            text="Approved advisory only.",
            source_kind="overlay_character_candidate",
            lineage=("render-1",),
            basis_refs=(StableReference(ref_kind="character_card", stable_ref="alice:goals"),),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            host_metadata={"hidden_source": "RAW_GLOBAL_FRAME_SECRET"},
        )
        result = project_character_candidates(
            fixture,
            manifest_id="m-render",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
        )
        content = result.contributions[0].content
        self.assertIn("Approved advisory only.", content)
        self.assertNotIn("RAW_GLOBAL_FRAME_SECRET", content)
        self.assertNotIn("hidden_source", content)

    def test_invalidation_predicates_and_continuity_boundaries_unchanged(self) -> None:
        prior = build_projection_invalidation_context(
            overlay_revision=1,
            authority_fingerprint="fp-1",
            known_by_snapshot_id="kb-1",
        )
        current = build_projection_invalidation_context(
            overlay_revision=1,
            authority_fingerprint="fp-2",
            known_by_snapshot_id="kb-1",
        )
        self.assertTrue(projection_invalidation_predicates_match(prior, current))
        package = _package(
            active_tensions=(
                NarrativeTension(
                    label="Scene pressure",
                    interpretive_note="Tension remains.",
                    evidence_refs=(_character_scope_ref("Alice"),),
                ),
            )
        )
        mapped = map_storyteller_package_to_contributions(
            package,
            manifest_id="m-auth",
            consumer_target="character",
            binding=_binding(pipeline_stage="character"),
            character_id="Alice",
            fixture=_fixture(),
        )
        for contribution in mapped.contributions:
            self.assertEqual(contribution.authority_class, "suggestive")


if __name__ == "__main__":
    unittest.main()

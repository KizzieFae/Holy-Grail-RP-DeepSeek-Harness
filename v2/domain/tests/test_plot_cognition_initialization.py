"""#60 Plot Cognition initialization domain contract tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.cognition_composition import CognitionComposition  # noqa: E402
from domain_api.librarian_contract import StableReference  # noqa: E402
from domain_api.plot_cognition_initialization_contract import (  # noqa: E402
    AUTHORED_STORYTELLER_DIRECTION_REF_KIND,
    INITIALIZATION_EVALUATION_SCHEMA,
    INITIALIZATION_PROPOSAL_SCHEMA,
    InitializationForensicHandoff,
    PlotCognitionInitializationEvaluation,
    PlotCognitionInitializationProposal,
    materialize_initial_overlay,
    new_evaluation_id,
    new_proposal_id,
    validate_authored_material_provenance,
    validate_initialization_evaluation_contract,
    validate_initialization_proposal_objective,
)
from domain_api.plot_cognition_initialization_service import (  # noqa: E402
    PlotCognitionInitializationService,
)
from domain_api.plot_cognition_initialization_sources import (  # noqa: E402
    compute_source_fingerprint,
    gather_initialization_sources,
    initialization_sources_complete,
    resolve_opening_completeness,
)
from domain_api.plot_cognition_overlay_contract import (  # noqa: E402
    PLOT_GOAL_SCHEMA,
    UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
    CognitionApplicability,
    CreationProvenance,
    GoalLineage,
    PlotGoal,
    UnresolvedNarrativePressure,
    new_goal_id,
    new_pressure_id,
    plot_goal_from_dict,
    plot_goal_to_dict,
    unresolved_narrative_pressure_to_dict,
)
from domain_api.plot_cognition_overlay_repository import PlotCognitionOverlayRepository  # noqa: E402
from domain_api.plot_cognition_overlay_service import PlotCognitionOverlayService  # noqa: E402
from domain_api.plot_cognition_overlay_store import (  # noqa: E402
    BoundednessPolicy,
    IntegrityReport,
    LoadStatus,
    ReplaceResult,
    empty_store,
)
from domain_api.plot_cognition_scope_lock import PlotCognitionScopeLockRegistry  # noqa: E402
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import LiveSession, initialize_live_session  # noqa: E402

TEST_POLICY = BoundednessPolicy(max_active_goals=2, max_active_pressures=2)


def _session_with_opening(
    *,
    opening_mode: str = "minimal",
    opening_text: str = "",
    goals_text: str = "Wants revenge on X.",
) -> LiveSession:
    fixture = initialize_live_session(cast=["Alice"], plot_cognition_scope_id="scope-init-test")
    fixture.setup_snapshot = {
        "opening": {"mode": opening_mode},
        "scene_template_id": "tpl-test",
        "scene_template": {"template_id": "tpl-test", "premise": "A tense reunion."},
        "character_cards": {
            "alice": {
                "name": "Alice",
                "goals": goals_text,
                "relationships": {"Bob": "rival"},
            }
        },
        "location": "Hall",
    }
    if opening_text:
        append_history_entry(
            fixture.rp_history,
            kind="opening",
            content=opening_text,
            entry_id=f"opening-{fixture.hg_session_id}",
            presentation_status="authored",
            metadata={"opening": True, "mode": opening_mode},
        )
    return fixture


def _goal_draft(*, goal_id: str | None = None, provenance: str = "storyteller") -> dict:
    gid = goal_id or new_goal_id()
    return plot_goal_to_dict(
        PlotGoal(
            schema=PLOT_GOAL_SCHEMA,
            goal_id=gid,
            intended_direction="Explore whether Alice pursues reconciliation.",
            basis_note="Authored rivalry context.",
            basis_refs=(
                StableReference(ref_kind="character_card", stable_ref="alice:relationships:Bob"),
            ),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            planning_horizon="MEDIUM",
            creation_provenance=CreationProvenance(source=provenance),  # type: ignore[arg-type]
            lineage=GoalLineage(),
            activity_state="active",
        )
    )


def _pressure_draft(*, pressure_id: str | None = None) -> dict:
    pid = pressure_id or new_pressure_id()
    return unresolved_narrative_pressure_to_dict(
        UnresolvedNarrativePressure(
            schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
            pressure_id=pid,
            pressure_text="Alice's desire for revenge remains unresolved.",
            dramatic_rationale="Creates ongoing tension without prescribing action.",
            basis_note="Authored motivation present.",
            basis_refs=(
                StableReference(ref_kind="character_card", stable_ref="alice:goals"),
            ),
            continuity_issue_refs=(),
            applicability=CognitionApplicability(
                applicability_kind="character",
                primary_character_id="Alice",
                involved_character_ids=("Alice",),
            ),
            creation_provenance=CreationProvenance(source="storyteller"),
            activity_state="active",
        )
    )


def _proposal_from_fixture(
    fixture: LiveSession,
    *,
    goals: list[dict] | None = None,
    pressures: list[dict] | None = None,
) -> PlotCognitionInitializationProposal:
    sources = gather_initialization_sources(fixture)
    resolved_goals = list(goals) if goals is not None else []
    resolved_pressures = list(pressures) if pressures is not None else [_pressure_draft()]
    return PlotCognitionInitializationProposal(
        schema=INITIALIZATION_PROPOSAL_SCHEMA,
        proposal_id=new_proposal_id(),
        source_snapshot_id=sources.snapshot_id,
        source_snapshot_fingerprint=sources.fingerprint,
        plot_cognition_scope_id=fixture.plot_cognition_scope_id,
        adoption_rationale="Storyteller adopts pressure from authored motivation without steering revenge yet.",
        goals=tuple(resolved_goals),
        pressures=tuple(resolved_pressures),
        global_frame=None,
    )


class PlotCognitionInitializationSourceTests(unittest.TestCase):
    def test_minimal_opening_not_expected(self) -> None:
        fixture = _session_with_opening(opening_mode="minimal")
        sources = gather_initialization_sources(fixture)
        self.assertEqual(sources.opening_completeness, "prose_not_expected")
        self.assertTrue(initialization_sources_complete(sources.opening_completeness))

    def test_custom_opening_durable(self) -> None:
        fixture = _session_with_opening(opening_mode="custom", opening_text="Custom opening.")
        sources = gather_initialization_sources(fixture)
        self.assertEqual(sources.opening_completeness, "prose_present")
        self.assertIsNotNone(sources.opening_entry_id)

    def test_template_opening_durable(self) -> None:
        fixture = _session_with_opening(opening_mode="template", opening_text="Template opener.")
        sources = gather_initialization_sources(fixture)
        self.assertEqual(sources.opening_completeness, "prose_present")

    def test_generated_opening_pending_and_present(self) -> None:
        pending = _session_with_opening(opening_mode="generated")
        self.assertEqual(
            resolve_opening_completeness("generated", opening_entry=None),
            "prose_pending",
        )
        self.assertFalse(
            initialization_sources_complete(
                gather_initialization_sources(pending).opening_completeness
            )
        )
        present = _session_with_opening(opening_mode="generated", opening_text="Generated prose.")
        self.assertEqual(gather_initialization_sources(present).opening_completeness, "prose_present")

    def test_fingerprint_stable_for_same_semantic_inputs(self) -> None:
        fixture_a = _session_with_opening(opening_mode="custom", opening_text="Same text.")
        fixture_b = deepcopy(fixture_a)
        snap_a = gather_initialization_sources(fixture_a)
        snap_b = gather_initialization_sources(fixture_b)
        self.assertEqual(snap_a.fingerprint, snap_b.fingerprint)
        self.assertNotEqual(snap_a.snapshot_id, snap_b.snapshot_id)

    def test_fingerprint_changes_when_source_changes(self) -> None:
        fixture = _session_with_opening(opening_mode="minimal", goals_text="Original motivation.")
        first = gather_initialization_sources(fixture).fingerprint
        fixture.setup_snapshot["character_cards"]["alice"]["goals"] = "Changed motivation."
        second = gather_initialization_sources(fixture).fingerprint
        self.assertNotEqual(first, second)

    def test_snapshot_id_does_not_affect_fingerprint(self) -> None:
        fixture = _session_with_opening()
        body = gather_initialization_sources(fixture).canonical_body
        self.assertEqual(compute_source_fingerprint(body), compute_source_fingerprint(body))


class PlotCognitionInitializationContractTests(unittest.TestCase):
    def test_character_motivation_not_auto_materialized(self) -> None:
        fixture = _session_with_opening(goals_text="She wants revenge on X.")
        sources = gather_initialization_sources(fixture)
        self.assertIn("goals_digest", sources.canonical_body["characters"][0])
        empty = _proposal_from_fixture(fixture, goals=[], pressures=[])
        validation = validate_initialization_proposal_objective(
            empty,
            policy_max_active_goals=TEST_POLICY.max_active_goals,
            policy_max_active_pressures=TEST_POLICY.max_active_pressures,
        )
        self.assertTrue(validation.ok)

    def test_storyteller_provenance_with_authored_basis_refs(self) -> None:
        goal = _goal_draft()
        self.assertEqual(goal["creation_provenance"]["source"], "storyteller")
        self.assertTrue(goal["basis_refs"])

    def test_authored_material_requires_storyteller_direction_ref(self) -> None:
        goal = _goal_draft(provenance="authored_material")
        ok, violations = validate_authored_material_provenance(goal)
        self.assertFalse(ok)
        goal["creation_provenance"]["provenance_refs"] = [
            {
                "ref_kind": AUTHORED_STORYTELLER_DIRECTION_REF_KIND,
                "stable_ref": "progression:tpl-test",
            }
        ]
        ok, violations = validate_authored_material_provenance(goal)
        self.assertTrue(ok)

    def test_zero_goals_valid(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
        validation = validate_initialization_proposal_objective(
            proposal,
            policy_max_active_goals=TEST_POLICY.max_active_goals,
            policy_max_active_pressures=TEST_POLICY.max_active_pressures,
        )
        self.assertTrue(validation.ok)

    def test_fully_empty_valid(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[])
        validation = validate_initialization_proposal_objective(
            proposal,
            policy_max_active_goals=TEST_POLICY.max_active_goals,
            policy_max_active_pressures=TEST_POLICY.max_active_pressures,
        )
        self.assertTrue(validation.ok)

    def test_objective_invalid_missing_rationale(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture)
        invalid = PlotCognitionInitializationProposal(
            schema=proposal.schema,
            proposal_id=proposal.proposal_id,
            source_snapshot_id=proposal.source_snapshot_id,
            source_snapshot_fingerprint=proposal.source_snapshot_fingerprint,
            plot_cognition_scope_id=proposal.plot_cognition_scope_id,
            adoption_rationale="",
            goals=proposal.goals,
            pressures=proposal.pressures,
            global_frame=None,
        )
        validation = validate_initialization_proposal_objective(
            invalid,
            policy_max_active_goals=TEST_POLICY.max_active_goals,
            policy_max_active_pressures=TEST_POLICY.max_active_pressures,
        )
        self.assertFalse(validation.ok)

    def test_duplicate_ids_rejected(self) -> None:
        fixture = _session_with_opening()
        goal = _goal_draft(goal_id="dup")
        proposal = _proposal_from_fixture(fixture, goals=[goal, goal], pressures=[])
        validation = validate_initialization_proposal_objective(
            proposal,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertFalse(validation.ok)

    def test_retired_rejected(self) -> None:
        fixture = _session_with_opening()
        goal = _goal_draft()
        goal["activity_state"] = "retired"
        proposal = _proposal_from_fixture(fixture, goals=[goal], pressures=[])
        validation = validate_initialization_proposal_objective(
            proposal,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertFalse(validation.ok)

    def test_over_budget_rejected_not_truncated(self) -> None:
        fixture = _session_with_opening()
        goals = [_goal_draft(goal_id=f"g{i}") for i in range(3)]
        proposal = _proposal_from_fixture(fixture, goals=goals, pressures=[])
        validation = validate_initialization_proposal_objective(
            proposal,
            policy_max_active_goals=TEST_POLICY.max_active_goals,
            policy_max_active_pressures=TEST_POLICY.max_active_pressures,
        )
        self.assertFalse(validation.ok)
        self.assertTrue(validation.over_budget)

    def test_materialized_assimilation_anchor_null(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[])
        store, validation = materialize_initial_overlay(
            proposal,
            plot_cognition_scope_id=fixture.plot_cognition_scope_id,
        )
        assert store is not None
        self.assertTrue(validation.ok)
        self.assertIsNone(store.assimilated_through_domain_commit_id)

    def test_evaluation_contract_requires_revision_brief(self) -> None:
        evaluation = PlotCognitionInitializationEvaluation(
            schema=INITIALIZATION_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id="p1",
            overall_result="revise",
            findings=(),
            revision_brief=None,
        )
        validation = validate_initialization_evaluation_contract(evaluation)
        self.assertFalse(validation.ok)


class PlotCognitionInitializationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = PlotCognitionOverlayRepository(self._tmpdir)
        self.locks = PlotCognitionScopeLockRegistry()
        self.overlay = PlotCognitionOverlayService(self.repo, scope_locks=self.locks)
        self.service = PlotCognitionInitializationService(self.overlay)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_absent_eligible(self) -> None:
        fixture = _session_with_opening()
        eligible, reason = self.service.is_initialization_eligible(fixture, policy=TEST_POLICY)
        self.assertTrue(eligible)
        self.assertEqual(reason, "absent")

    def test_ready_nonempty_skips(self) -> None:
        fixture = _session_with_opening()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.goals[_goal_draft()["goal_id"]] = plot_goal_from_dict(_goal_draft())
        store.store_revision = 1
        self.overlay.replace_snapshot(
            fixture.plot_cognition_scope_id,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        eligible, reason = self.service.is_initialization_eligible(fixture, policy=TEST_POLICY)
        self.assertFalse(eligible)
        self.assertEqual(reason, "already_initialized")

    def test_ready_empty_skips(self) -> None:
        fixture = _session_with_opening()
        store = empty_store(fixture.plot_cognition_scope_id)
        store.store_revision = 1
        self.overlay.replace_snapshot(
            fixture.plot_cognition_scope_id,
            store,
            expected_revision=0,
            policy=TEST_POLICY,
        )
        eligible, reason = self.service.is_initialization_eligible(fixture, policy=TEST_POLICY)
        self.assertFalse(eligible)

    def test_generated_opening_incomplete_blocks_commit(self) -> None:
        fixture = _session_with_opening(opening_mode="generated")
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[])
        result = self.service.commit_initial_overlay_if_absent(
            fixture,
            proposal,
            policy=TEST_POLICY,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.code, "opening_incomplete")

    def test_commit_success_through_overlay_service(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
        handoff = InitializationForensicHandoff()
        result = self.service.commit_initial_overlay_if_absent(
            fixture,
            proposal,
            policy=TEST_POLICY,
            forensic_handoff=handoff,
        )
        self.assertTrue(result.success)
        loaded = self.overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.READY)
        self.assertIsNotNone(handoff.materialized_store)

    def test_stale_fingerprint_blocks_persist(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
        fixture.setup_snapshot["location"] = "Changed Hall"
        result = self.service.commit_initial_overlay_if_absent(
            fixture,
            proposal,
            policy=TEST_POLICY,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.code, "stale_source")

    def test_corrupt_blocks(self) -> None:
        fixture = _session_with_opening()
        path = self.repo.store_path(fixture.plot_cognition_scope_id)
        path.write_text("{not-json", encoding="utf-8")
        eligible, reason = self.service.is_initialization_eligible(fixture, policy=TEST_POLICY)
        self.assertFalse(eligible)
        self.assertEqual(reason, "corrupt")

    def test_unsupported_version_blocks(self) -> None:
        fixture = _session_with_opening()
        path = self.repo.store_path(fixture.plot_cognition_scope_id)
        path.write_text(
            '{"store_schema":"hg_unknown","plot_cognition_scope_id":"x","store_revision":0,"goals":{},"pressures":{}}',
            encoding="utf-8",
        )
        loaded = self.overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.UNSUPPORTED_VERSION)

    def test_degraded_blocks(self) -> None:
        fixture = _session_with_opening()
        store = empty_store(fixture.plot_cognition_scope_id)
        for index in range(3):
            store.goals[f"g{index}"] = plot_goal_from_dict(_goal_draft(goal_id=f"g{index}"))
        self.repo.save_raw(fixture.plot_cognition_scope_id, store.to_dict(), expected_revision=0)
        loaded = self.overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.DEGRADED)

    def test_concurrent_first_writer_wins(self) -> None:
        fixture = _session_with_opening()
        proposal_a = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
        proposal_b = _proposal_from_fixture(
            fixture,
            goals=[],
            pressures=[
                unresolved_narrative_pressure_to_dict(
                    UnresolvedNarrativePressure(
                        schema=UNRESOLVED_NARRATIVE_PRESSURE_SCHEMA,
                        pressure_id=new_pressure_id(),
                        pressure_text="Second pressure",
                        dramatic_rationale="Race test",
                        basis_note=None,
                        basis_refs=(),
                        continuity_issue_refs=(),
                        applicability=CognitionApplicability(
                            applicability_kind="global",
                            primary_character_id=None,
                            involved_character_ids=(),
                        ),
                        creation_provenance=CreationProvenance(source="storyteller"),
                        activity_state="active",
                    )
                )
            ],
        )
        results: list = []

        def commit(proposal: PlotCognitionInitializationProposal) -> None:
            results.append(
                self.service.commit_initial_overlay_if_absent(
                    fixture,
                    proposal,
                    policy=TEST_POLICY,
                )
            )

        threads = [
            threading.Thread(target=commit, args=(proposal_a,)),
            threading.Thread(target=commit, args=(proposal_b,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        successes = [result for result in results if result.success]
        already = [result for result in results if result.code == "already_initialized"]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(already), 1)

    def test_failed_persistence_error_normalizes_when_authoritative_ready(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
        winner_store, validation = materialize_initial_overlay(
            proposal,
            plot_cognition_scope_id=fixture.plot_cognition_scope_id,
        )
        assert winner_store is not None
        self.assertTrue(validation.ok)

        def simulate_concurrent_winner_failure(
            plot_cognition_scope_id: str,
            store: object,
            *,
            expected_revision: int,
            policy: BoundednessPolicy,
        ) -> ReplaceResult:
            self.repo.save_raw(
                plot_cognition_scope_id,
                winner_store.to_dict(),
                expected_revision=expected_revision,
            )
            return ReplaceResult(
                success=False,
                prior_revision=expected_revision,
                new_revision=None,
                integrity=IntegrityReport(ok=True, violations=()),
                error_code="persistence_error",
                error_message="simulated persistence failure after concurrent winner",
            )

        with patch.object(
            self.overlay,
            "replace_snapshot",
            side_effect=simulate_concurrent_winner_failure,
        ):
            result = self.service.commit_initial_overlay_if_absent(
                fixture,
                proposal,
                policy=TEST_POLICY,
            )

        self.assertFalse(result.success)
        self.assertEqual(result.code, "already_initialized")
        loaded = self.overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.READY)

    def test_failed_persistence_error_preserved_when_still_absent(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])

        with patch.object(
            self.overlay,
            "replace_snapshot",
            return_value=ReplaceResult(
                success=False,
                prior_revision=0,
                new_revision=None,
                integrity=IntegrityReport(ok=True, violations=()),
                error_code="persistence_error",
                error_message="genuine persistence failure",
            ),
        ):
            result = self.service.commit_initial_overlay_if_absent(
                fixture,
                proposal,
                policy=TEST_POLICY,
            )

        self.assertFalse(result.success)
        self.assertEqual(result.code, "persistence_failed")
        loaded = self.overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.ABSENT)

    def test_failed_revision_conflict_preserved_when_still_absent(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])

        with patch.object(
            self.overlay,
            "replace_snapshot",
            return_value=ReplaceResult(
                success=False,
                prior_revision=0,
                new_revision=None,
                integrity=IntegrityReport(ok=True, violations=()),
                error_code="revision_conflict",
                error_message="revision conflict without established initialization",
            ),
        ):
            result = self.service.commit_initial_overlay_if_absent(
                fixture,
                proposal,
                policy=TEST_POLICY,
            )

        self.assertFalse(result.success)
        self.assertEqual(result.code, "revision_conflict")
        loaded = self.overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.ABSENT)

    def test_concurrent_barrier_stress_first_writer_wins(self) -> None:
        fixture = _session_with_opening()
        barrier = threading.Barrier(2)
        results: list = []

        def commit(proposal: PlotCognitionInitializationProposal) -> None:
            barrier.wait(timeout=2)
            results.append(
                self.service.commit_initial_overlay_if_absent(
                    fixture,
                    proposal,
                    policy=TEST_POLICY,
                )
            )

        for _ in range(100):
            results.clear()
            proposal_a = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
            proposal_b = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
            threads = [
                threading.Thread(target=commit, args=(proposal_a,)),
                threading.Thread(target=commit, args=(proposal_b,)),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            successes = [result for result in results if result.success]
            already = [result for result in results if result.code == "already_initialized"]
            failed = [
                result
                for result in results
                if not result.success and result.code != "already_initialized"
            ]
            self.assertEqual(len(successes), 1, msg=f"unexpected failures: {failed}")
            self.assertEqual(len(already), 1, msg=f"unexpected failures: {failed}")
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = tempfile.mkdtemp()
            self.repo = PlotCognitionOverlayRepository(self._tmpdir)
            self.overlay = PlotCognitionOverlayService(self.repo, scope_locks=self.locks)
            self.service = PlotCognitionInitializationService(self.overlay)

    def test_fully_empty_commit_persists_ready(self) -> None:
        fixture = _session_with_opening()
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[])
        result = self.service.commit_initial_overlay_if_absent(
            fixture,
            proposal,
            policy=TEST_POLICY,
        )
        self.assertTrue(result.success)
        loaded = self.overlay.load(fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        self.assertEqual(loaded.status, LoadStatus.READY)
        self.assertEqual(len(loaded.store.goals), 0)  # type: ignore[union-attr]
        self.assertEqual(len(loaded.store.pressures), 0)  # type: ignore[union-attr]
        self.assertIsNone(loaded.store.active_frame)  # type: ignore[union-attr]

    def test_degraded_blocks_commit(self) -> None:
        fixture = _session_with_opening()
        store = empty_store(fixture.plot_cognition_scope_id)
        for index in range(3):
            store.goals[f"g{index}"] = plot_goal_from_dict(_goal_draft(goal_id=f"g{index}"))
        self.repo.save_raw(fixture.plot_cognition_scope_id, store.to_dict(), expected_revision=0)
        proposal = _proposal_from_fixture(fixture, goals=[], pressures=[_pressure_draft()])
        result = self.service.commit_initial_overlay_if_absent(
            fixture,
            proposal,
            policy=TEST_POLICY,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.code, "blocked_status")

    def test_template_id_does_not_auto_authored_material(self) -> None:
        fixture = _session_with_opening()
        goal = _goal_draft(provenance="authored_material")
        self.assertFalse(validate_authored_material_provenance(goal)[0])

    def test_cognition_composition_exposes_initialization_service(self) -> None:
        composition = CognitionComposition.for_tests(
            plot_cognition_overlay_repository=self.repo,
            plot_cognition_scope_locks=self.locks,
        )
        self.assertIsNotNone(composition.plot_cognition_initialization)
        self.assertIsInstance(
            composition.plot_cognition_initialization,
            PlotCognitionInitializationService,
        )


if __name__ == "__main__":
    unittest.main()

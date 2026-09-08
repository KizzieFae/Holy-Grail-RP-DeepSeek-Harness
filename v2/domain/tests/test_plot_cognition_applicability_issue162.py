"""Issue #162 — applicability canonicalization end-to-end domain tests."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.plot_cognition_forensics_integration import (  # noqa: E402
    format_plot_cognition_wafi_finalize_response,
)
from domain_api.plot_cognition_overlay_repository import PlotCognitionOverlayRepository  # noqa: E402
from domain_api.plot_cognition_overlay_service import PlotCognitionOverlayService  # noqa: E402
from domain_api.plot_cognition_overlay_store import PlotCognitionOverlayStore  # noqa: E402
from domain_api.plot_cognition_projection_contract import (  # noqa: E402
    ProjectionBudget,
    overlay_goal_to_character_candidate,
)
from domain_api.plot_cognition_projection_semantic_safety import (  # noqa: E402
    DeterministicRuleBasedEpistemicEvaluator,
)
from domain_api.plot_cognition_projection_service import project_character_candidates  # noqa: E402
from domain_api.plot_cognition_update_contract import (  # noqa: E402
    UPDATE_EVALUATION_SCHEMA,
    UPDATE_PROPOSAL_SCHEMA,
    PlotCognitionUpdateEvaluation,
    PlotCognitionUpdateProposal,
    UpdateCommitResult,
    new_evaluation_id,
    validate_update_proposal_objective,
)
from domain_api.plot_cognition_update_service import PlotCognitionUpdateService  # noqa: E402
from domain_api.plot_cognition_proposal_enrichment import enrich_update_proposal  # noqa: E402
from domain.tests.test_plot_cognition_update_replan import (  # noqa: E402
    TEST_POLICY,
    _initialized_store,
    _session,
    _update_proposal,
)


LIVE_FIXTURE_PATH = Path(
    r"C:\Users\kelly\AppData\Local\Temp\hg-plot-long-horizon\results\A_baseline_rep1"
    r"\execution_evidence\hg-session-7c07b776-94b6-4fbb-b8a7-9be99ef90145\attempts"
    r"\135aa142-051a-45b3-bf58-725f0dfe13c4.json"
)


def _misencoded_live_goals() -> tuple[dict, ...]:
    return (
        {
            "goal_id": "goal_ayame_assert_control",
            "intended_direction": "Ayame maintains command over her household and the interview process.",
            "planning_horizon": "MEDIUM",
            "applicability": {
                "applicability_kind": "character",
                "primary_character_id": "Ayame",
                "involved_character_ids": ["Ayame", "Kizzie"],
            },
        },
        {
            "goal_id": "goal_kizzie_gain_access",
            "intended_direction": "Kizzie secures a position while concealing her purpose.",
            "planning_horizon": "MEDIUM",
            "applicability": {
                "applicability_kind": "character",
                "primary_character_id": "Kizzie",
                "involved_character_ids": ["Kizzie", "Ayame"],
            },
        },
    )


def _misencoded_live_pressures() -> tuple[dict, ...]:
    return (
        {
            "pressure_id": "pressure_presence_conflict",
            "pressure_text": "Unresolved power struggle between Ayame and Kizzie.",
            "dramatic_rationale": "Maintains relational tension.",
            "applicability": {
                "applicability_kind": "relational",
                "primary_character_id": "Ayame",
                "involved_character_ids": ["Ayame", "Kizzie"],
            },
        },
    )


class PlotCognitionApplicabilityIssue162Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.repo = PlotCognitionOverlayRepository(self.tmpdir)
        self.overlay = PlotCognitionOverlayService(self.repo)
        self.fixture = _session(scope_id="scope-issue-162")
        self.store = _initialized_store(self.fixture, self.overlay)
        self.service = PlotCognitionUpdateService(self.overlay)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_live_fixture_passes_objective_validation_after_enrichment(self) -> None:
        if LIVE_FIXTURE_PATH.is_file():
            attempt = json.loads(LIVE_FIXTURE_PATH.read_text(encoding="utf-8"))
            update = json.loads(attempt["response"]["assistant_text"])["update_proposal"]
            goals = tuple(update.get("goals") or [])
            pressures = tuple(update.get("pressures") or [])
        else:
            goals = _misencoded_live_goals()
            pressures = _misencoded_live_pressures()

        proposal = _update_proposal(self.fixture, self.store, goals=goals, pressures=pressures)
        enriched = enrich_update_proposal(proposal)
        validation = validate_update_proposal_objective(
            enriched,
            policy_max_active_goals=10,
            policy_max_active_pressures=10,
        )
        self.assertTrue(validation.ok, validation.violations)

    def test_commit_update_assimilates_misencoded_proposal_into_overlay(self) -> None:
        proposal = _update_proposal(
            self.fixture,
            self.store,
            goals=_misencoded_live_goals(),
            pressures=_misencoded_live_pressures(),
        )
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        result = self.service.commit_update(
            self.fixture,
            proposal,
            evaluation,
            policy=TEST_POLICY,
        )
        self.assertTrue(result.success, (result.code, result.message, result.violations))
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        self.assertIn("goal_ayame_assert_control", loaded.store.goals)
        self.assertIn("goal_kizzie_gain_access", loaded.store.goals)
        self.assertIn("pressure_presence_conflict", loaded.store.pressures)

    def test_failed_objective_validation_exposes_violation_codes(self) -> None:
        proposal = _update_proposal(
            self.fixture,
            self.store,
            pressures=(
                {
                    "pressure_id": "pressure-rel-only-one",
                    "pressure_text": "Only one character in scope.",
                    "dramatic_rationale": "Fails relational cardinality.",
                    "applicability": {
                        "applicability_kind": "relational",
                        "primary_character_id": "Alice",
                        "involved_character_ids": ["Alice"],
                    },
                },
            ),
        )
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        result = self.service.commit_update(
            self.fixture,
            proposal,
            evaluation,
            policy=TEST_POLICY,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.code, "integrity_invalid")
        self.assertTrue(result.violations)
        response = format_plot_cognition_wafi_finalize_response(
            result,
            True,
            None,
            persistence_message="unused",
        )
        self.assertIn("violations", response)
        self.assertTrue(
            any(
                "relational_applicability_requires_two_or_more_characters" in item
                for item in response["violations"]
            )
        )

    def test_assimilated_overlay_projects_to_character_consumer(self) -> None:
        proposal = _update_proposal(
            self.fixture,
            self.store,
            goals=_misencoded_live_goals(),
            pressures=(),
        )
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        commit = self.service.commit_update(
            self.fixture,
            proposal,
            evaluation,
            policy=TEST_POLICY,
        )
        self.assertTrue(commit.success)
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        ayame_goal = loaded.store.goals["goal_ayame_assert_control"]
        candidate = overlay_goal_to_character_candidate(ayame_goal)
        projection = project_character_candidates(
            self.fixture,
            manifest_id="m-issue-162",
            character_id="Ayame",
            candidates=(candidate,),
            budget=ProjectionBudget(max_evaluation_candidates=8, max_projection_candidates=4),
            evaluator=DeterministicRuleBasedEpistemicEvaluator(),
        )
        self.assertTrue(projection.contributions)
        self.assertIn("Ayame maintains command", projection.contributions[0].content)


if __name__ == "__main__":
    unittest.main()

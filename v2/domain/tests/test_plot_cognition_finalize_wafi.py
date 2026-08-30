"""Plot Cognition finalize WAFI failure propagation tests (#68)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.plot_cognition_forensics_integration import (  # noqa: E402
    format_plot_cognition_wafi_finalize_response,
)
from domain_api.plot_cognition_forensics_repository import (  # noqa: E402
    ForensicsPersistenceError,
    PlotCognitionForensicsRepository,
)
from domain_api.plot_cognition_forensics_service import (  # noqa: E402
    PlotCognitionForensicsService,
    WafiResult,
)
from domain_api.plot_cognition_lifecycle_api import finalize_plot_cognition_update  # noqa: E402
from domain_api.plot_cognition_overlay_store import BoundednessPolicy  # noqa: E402
from domain_api.plot_cognition_update_contract import (  # noqa: E402
    REPLAN_EVALUATION_SCHEMA,
    REPLAN_PROPOSAL_SCHEMA,
    UPDATE_EVALUATION_SCHEMA,
    UPDATE_PROPOSAL_SCHEMA,
    PlotCognitionReplanEvaluation,
    PlotCognitionReplanProposal,
    PlotCognitionUpdateEvaluation,
    PlotCognitionUpdateProposal,
    UpdateCommitResult,
    new_evaluation_id,
    new_replan_evaluation_id,
    new_replan_proposal_id,
)
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain.tests.test_plot_cognition_update_replan import (  # noqa: E402
    TEST_POLICY,
    _initialized_store,
    _session,
    _update_proposal,
)


class FaultInjectForensicsRepository(PlotCognitionForensicsRepository):
    def __init__(self, store_root: str | Path, *, fail_after: str | None = None) -> None:
        super().__init__(store_root)
        self.fail_after = fail_after

    def append_record(self, record: dict[str, Any]) -> str:
        phase = record.get("mutation_phase")
        if self.fail_after == "intent" and phase == "intent":
            raise ForensicsPersistenceError("injected intent failure")
        if self.fail_after == "completion" and phase == "completion":
            raise ForensicsPersistenceError("injected completion failure")
        return super().append_record(record)


class PlotCognitionFinalizeWafiTests(unittest.TestCase):
    def test_format_mutation_failure_preserves_domain_code(self) -> None:
        result = UpdateCommitResult(
            success=False,
            code="integrity_invalid",
            message="replan proposal failed objective validation",
        )
        response = format_plot_cognition_wafi_finalize_response(
            result,
            False,
            WafiResult(
                ok=False,
                code="mutation_failed",
                message="replan proposal failed objective validation",
                idempotency_key="k",
            ),
            persistence_message="unused",
        )
        self.assertFalse(response["accepted"])
        self.assertEqual(response["code"], "integrity_invalid")
        self.assertEqual(response["forensic_stage"], "mutation_failed")

    def test_format_stale_revision_mutation_failure(self) -> None:
        result = UpdateCommitResult(
            success=False,
            code="stale_revision",
            message="overlay store revision changed since proposal",
            store_revision=5,
        )
        response = format_plot_cognition_wafi_finalize_response(
            result,
            False,
            WafiResult(ok=False, code="mutation_failed", message="stale", idempotency_key="k"),
            persistence_message="unused",
        )
        self.assertEqual(response["code"], "stale_revision")
        self.assertEqual(response["store_revision"], 5)

    def test_format_intent_persistence_failure(self) -> None:
        response = format_plot_cognition_wafi_finalize_response(
            None,
            False,
            WafiResult(
                ok=False,
                code="intent_persistence_failed",
                message="disk error",
                idempotency_key="k",
            ),
            persistence_message="plot cognition update forensic persistence failed",
        )
        self.assertEqual(response["code"], "forensic_persistence_failed")
        self.assertEqual(response["forensic_stage"], "intent_persistence_failed")

    def test_format_completion_persistence_failure(self) -> None:
        result = UpdateCommitResult(success=True, code="committed", message="ok", store_revision=4)
        response = format_plot_cognition_wafi_finalize_response(
            result,
            False,
            WafiResult(
                ok=False,
                code="completion_persistence_failed",
                message="completion write failed",
                idempotency_key="k",
            ),
            persistence_message="plot cognition update forensic persistence failed",
        )
        self.assertEqual(response["code"], "forensic_persistence_failed")
        self.assertEqual(response["forensic_stage"], "completion_persistence_failed")

    def test_format_success_unchanged(self) -> None:
        result = UpdateCommitResult(success=True, code="committed", message="ok", store_revision=6)
        response = format_plot_cognition_wafi_finalize_response(
            result,
            True,
            WafiResult(ok=True, code="completed", message="ok", idempotency_key="k"),
            persistence_message="unused",
        )
        self.assertTrue(response["accepted"])
        self.assertEqual(response["code"], "committed")
        self.assertEqual(response["store_revision"], 6)


class PlotCognitionFinalizeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp(prefix="pcf-finalize-")
        self._prior_hg_data = os.environ.get("HG_DATA_DIR")
        os.environ["HG_DATA_DIR"] = self.tempdir
        self.sessions_dir = Path(self.tempdir) / "sessions"
        self.repo = SessionRepository(self.sessions_dir)
        self.kernel = DomainKernel.for_repository(self.repo)
        self.scope_id = "scope-finalize-wafi"
        self.fixture = self.repo.create_session(
            cast=["Alice"],
            plot_cognition_scope_id=self.scope_id,
        )
        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        store = _initialized_store(self.fixture, overlay)
        self.update_svc = self.kernel.cognition.plot_cognition_update
        assert self.update_svc is not None
        self.update_svc.first_reconciliation(self.fixture, store, TEST_POLICY)
        self.loaded = overlay.load(self.scope_id, policy=TEST_POLICY)
        assert self.loaded.store is not None

    def tearDown(self) -> None:
        if self._prior_hg_data is None:
            os.environ.pop("HG_DATA_DIR", None)
        else:
            os.environ["HG_DATA_DIR"] = self._prior_hg_data
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_finalize_reports_domain_integrity_invalid_for_objective_rejection(self) -> None:
        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        loaded = overlay.load(self.scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        proposal = _update_proposal(self.fixture, loaded.store, replan_required=True)
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        replan_proposal = PlotCognitionReplanProposal(
            schema=REPLAN_PROPOSAL_SCHEMA,
            proposal_id=new_replan_proposal_id(),
            source_snapshot_id=proposal.source_snapshot_id,
            source_snapshot_fingerprint=proposal.source_snapshot_fingerprint,
            plot_cognition_scope_id=proposal.plot_cognition_scope_id,
            prior_store_revision=proposal.prior_store_revision,
            replan_rationale="Replace invalidated pursuit.",
            trigger_summary="Authority invalidated prior direction.",
            goals=(
                {
                    "goal_id": "replacement-goal",
                    "intended_direction": "Pursue alternate path.",
                },
            ),
            pressures=(
                {
                    "pressure_id": "replacement-pressure",
                    "pressure_text": "Uncertainty remains.",
                },
            ),
            global_frame=None,
        )
        replan_eval = PlotCognitionReplanEvaluation(
            schema=REPLAN_EVALUATION_SCHEMA,
            evaluation_id=new_replan_evaluation_id(),
            proposal_id=replan_proposal.proposal_id,
            overall_result="accept",
            findings=(),
        )
        finalized = finalize_plot_cognition_update(
            self.kernel,
            self.fixture,
            {
                "proposal": proposal.to_dict(),
                "evaluation": evaluation.to_dict(),
                "replan_proposal": replan_proposal.to_dict(),
                "replan_evaluation": replan_eval.to_dict(),
            },
        )
        self.assertFalse(finalized["accepted"])
        self.assertEqual(finalized["code"], "integrity_invalid")
        self.assertEqual(finalized["forensic_stage"], "mutation_failed")
        self.assertNotEqual(finalized["code"], "forensic_persistence_failed")

    def test_finalize_intent_persistence_failure(self) -> None:
        fault_repo = FaultInjectForensicsRepository(
            Path(self.tempdir) / "plot_cognition_forensics",
            fail_after="intent",
        )
        self.repo._plot_cognition_forensics = PlotCognitionForensicsService(fault_repo)

        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        loaded = overlay.load(self.scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        proposal = _update_proposal(self.fixture, loaded.store)
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="no_change",
            findings=(),
            no_change_rationale="No change.",
        )
        finalized = finalize_plot_cognition_update(
            self.kernel,
            self.fixture,
            {
                "proposal": proposal.to_dict(),
                "evaluation": evaluation.to_dict(),
            },
        )
        self.assertFalse(finalized["accepted"])
        self.assertEqual(finalized["code"], "forensic_persistence_failed")
        self.assertEqual(finalized["forensic_stage"], "intent_persistence_failed")

    def test_finalize_completion_persistence_failure(self) -> None:
        fault_repo = FaultInjectForensicsRepository(
            Path(self.tempdir) / "plot_cognition_forensics",
            fail_after="completion",
        )
        self.repo._plot_cognition_forensics = PlotCognitionForensicsService(fault_repo)

        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        loaded = overlay.load(self.scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        proposal = _update_proposal(self.fixture, loaded.store)
        evaluation = PlotCognitionUpdateEvaluation(
            schema=UPDATE_EVALUATION_SCHEMA,
            evaluation_id=new_evaluation_id(),
            proposal_id=proposal.proposal_id,
            overall_result="no_change",
            findings=(),
            no_change_rationale="No change.",
        )
        finalized = finalize_plot_cognition_update(
            self.kernel,
            self.fixture,
            {
                "proposal": proposal.to_dict(),
                "evaluation": evaluation.to_dict(),
            },
        )
        self.assertFalse(finalized["accepted"])
        self.assertEqual(finalized["code"], "forensic_persistence_failed")
        self.assertEqual(finalized["forensic_stage"], "completion_persistence_failed")


if __name__ == "__main__":
    unittest.main()

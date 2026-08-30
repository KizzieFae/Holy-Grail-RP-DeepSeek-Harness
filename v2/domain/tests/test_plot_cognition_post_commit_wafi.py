"""Production post-commit pending-work WAFI regression tests (#64 remediation)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.plot_cognition_forensics_repository import (  # noqa: E402
    ForensicsPersistenceError,
    PlotCognitionForensicsRepository,
)
from domain_api.plot_cognition_forensics_service import PlotCognitionForensicsService  # noqa: E402
from domain_api.plot_cognition_orchestration_api import record_plot_cognition_post_commit  # noqa: E402
from domain_api.plot_cognition_orchestration_service import PlotCognitionOrchestrationService  # noqa: E402
from domain_api.plot_cognition_overlay_store import BoundednessPolicy, empty_store  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


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


class PostCommitPendingWorkWafiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp(prefix="pcf-post-commit-")
        self._prior_hg_data = os.environ.get("HG_DATA_DIR")
        os.environ["HG_DATA_DIR"] = self.tempdir
        self.sessions_dir = Path(self.tempdir) / "sessions"
        self.repo = SessionRepository(self.sessions_dir)
        self.kernel = DomainKernel.for_repository(self.repo)
        self.scope_id = "scope-post-commit-wafi"
        self.fixture = self.repo.create_session(
            cast=["Alice"],
            plot_cognition_scope_id=self.scope_id,
        )
        store = empty_store(self.scope_id)
        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        overlay.replace_snapshot(
            self.scope_id,
            store,
            expected_revision=0,
            policy=BoundednessPolicy(max_active_goals=4, max_active_pressures=4),
        )

    def tearDown(self) -> None:
        if self._prior_hg_data is None:
            os.environ.pop("HG_DATA_DIR", None)
        else:
            os.environ["HG_DATA_DIR"] = self._prior_hg_data
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def _loaded_store_dict(self) -> dict[str, Any]:
        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        loaded = overlay.load(
            self.scope_id,
            policy=BoundednessPolicy(max_active_goals=4, max_active_pressures=4),
        )
        assert loaded.store is not None
        return loaded.store.to_dict()

    def test_wafi_ordering_intent_before_overlay_before_completion(self) -> None:
        order: list[str] = []
        forensics_repo = self.repo._plot_cognition_forensics_repo
        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        original_append = forensics_repo.append_record
        original_replace = overlay.replace_snapshot

        def track_append(record: dict[str, Any]) -> str:
            phase = record.get("mutation_phase")
            if phase == "intent":
                order.append("intent")
            elif phase == "completion":
                order.append("completion")
            return original_append(record)

        def track_replace(*args: Any, **kwargs: Any):
            order.append("overlay_replace")
            return original_replace(*args, **kwargs)

        with mock.patch.object(forensics_repo, "append_record", side_effect=track_append):
            with mock.patch.object(overlay, "replace_snapshot", side_effect=track_replace):
                result = record_plot_cognition_post_commit(
                    self.kernel,
                    self.fixture,
                    domain_commit_id="commit-order-1",
                )
        self.assertTrue(result["recorded"])
        self.assertEqual(order, ["intent", "overlay_replace", "completion"])

    def test_intent_failure_leaves_overlay_unchanged(self) -> None:
        before = self._loaded_store_dict()
        self.assertIsNone(before.get("pending_work"))
        fault_repo = FaultInjectForensicsRepository(
            Path(self.tempdir) / "plot_cognition_forensics",
            fail_after="intent",
        )
        self.repo._plot_cognition_forensics = PlotCognitionForensicsService(fault_repo)
        result = record_plot_cognition_post_commit(
            self.kernel,
            self.fixture,
            domain_commit_id="commit-intent-fail",
        )
        self.assertFalse(result["recorded"])
        after = self._loaded_store_dict()
        self.assertIsNone(after.get("pending_work"))

    def test_completion_failure_reports_failure_and_preserves_intent(self) -> None:
        fault_repo = FaultInjectForensicsRepository(
            Path(self.tempdir) / "plot_cognition_forensics",
            fail_after="completion",
        )
        self.repo._plot_cognition_forensics = PlotCognitionForensicsService(fault_repo)
        result = record_plot_cognition_post_commit(
            self.kernel,
            self.fixture,
            domain_commit_id="commit-completion-fail",
        )
        self.assertFalse(result["recorded"])
        index = fault_repo.load_index(self.scope_id)
        idem = f"{self.scope_id}:pending:commit-completion-fail"
        self.assertIn("intent", (index.get("by_idempotency_key") or {}).get(idem, {}))
        self.assertNotIn("completion", (index.get("by_idempotency_key") or {}).get(idem, {}))

    def test_intent_prior_snapshot_excludes_new_pending_work(self) -> None:
        result = record_plot_cognition_post_commit(
            self.kernel,
            self.fixture,
            domain_commit_id="commit-prior-1",
        )
        self.assertTrue(result["recorded"])
        index = self.repo._plot_cognition_forensics_repo.load_index(self.scope_id)
        idem = f"{self.scope_id}:pending:commit-prior-1"
        intent_id = (index.get("by_idempotency_key") or {}).get(idem, {}).get("intent")
        assert intent_id
        intent = self.repo._plot_cognition_forensics_repo.load_record(self.scope_id, str(intent_id))
        assert intent is not None
        prior = (intent.get("payload") or {}).get("prior_snapshot") or {}
        self.assertIsNone(prior.get("pending_work"))
        trigger = ((intent.get("payload") or {}).get("pending_work") or {}).get(
            "trigger_domain_commit_id"
        )
        self.assertEqual(trigger, "commit-prior-1")

    def test_idempotent_replay_does_not_double_apply(self) -> None:
        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        first = record_plot_cognition_post_commit(
            self.kernel,
            self.fixture,
            domain_commit_id="commit-replay-1",
        )
        revision_after_first = self._loaded_store_dict()["store_revision"]
        second = record_plot_cognition_post_commit(
            self.kernel,
            self.fixture,
            domain_commit_id="commit-replay-1",
        )
        revision_after_second = self._loaded_store_dict()["store_revision"]
        self.assertTrue(first["recorded"])
        self.assertTrue(second.get("recorded"))
        self.assertTrue(second.get("replayed"))
        self.assertEqual(revision_after_first, revision_after_second)

    def test_mutation_failure_preserves_intent_without_completion(self) -> None:
        from domain_api.plot_cognition_orchestration_service import PendingWorkApplyResult

        with mock.patch(
            "domain_api.plot_cognition_orchestration_service.PlotCognitionOrchestrationService.apply_post_commit_pending_work",
            return_value=PendingWorkApplyResult(
                success=False,
                code="stale_revision",
                message="stale",
                store_revision=1,
                prior_revision=0,
                overlay_mutated=False,
            ),
        ):
            result = record_plot_cognition_post_commit(
                self.kernel,
                self.fixture,
                domain_commit_id="commit-mutation-fail",
            )
        self.assertFalse(result["recorded"])
        index = self.repo._plot_cognition_forensics_repo.load_index(self.scope_id)
        idem = f"{self.scope_id}:pending:commit-mutation-fail"
        self.assertIn("intent", (index.get("by_idempotency_key") or {}).get(idem, {}))
        self.assertNotIn("completion", (index.get("by_idempotency_key") or {}).get(idem, {}))

    def test_clear_pending_work_captured_in_update_wafi_completion(self) -> None:
        record_plot_cognition_post_commit(
            self.kernel,
            self.fixture,
            domain_commit_id="commit-clear-setup",
        )
        self.assertIsNotNone(self._loaded_store_dict().get("pending_work"))
        overlay = self.kernel.cognition.plot_cognition_overlay
        assert overlay is not None
        orch = PlotCognitionOrchestrationService(overlay)

        class _FakeResult:
            success = True
            code = "committed"
            message = "ok"
            store_revision = self._loaded_store_dict()["store_revision"]
            prior_revision = self._loaded_store_dict()["store_revision"] - 1

        from domain_api.plot_cognition_forensics_integration import wafi_update_like

        result, forensic_ok, _wafi = wafi_update_like(
            self.kernel,
            self.fixture,
            operation_kind="update",
            idempotency_suffix="proposal-clear-test",
            intent_payload={"proposal_id": "proposal-clear-test"},
            correlation_extra={"domain_commit_id": "commit-clear-setup"},
            commit_fn=lambda: _FakeResult(),
            before_completion_snapshot=lambda res: (
                orch.clear_pending_work(self.fixture) if res.success else None
            ),
        )
        self.assertTrue(forensic_ok)
        self.assertTrue(result.success)
        index = self.repo._plot_cognition_forensics_repo.load_index(self.scope_id)
        completion_id = (
            (index.get("by_idempotency_key") or {})
            .get(f"{self.scope_id}:update:proposal-clear-test", {})
            .get("completion")
        )
        assert completion_id
        completion = self.repo._plot_cognition_forensics_repo.load_record(
            self.scope_id,
            str(completion_id),
        )
        assert completion is not None
        resulting = (completion.get("payload") or {}).get("resulting_snapshot") or {}
        self.assertIsNone(resulting.get("pending_work"))
        self.assertIsNone(self._loaded_store_dict().get("pending_work"))


if __name__ == "__main__":
    unittest.main()

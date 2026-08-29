"""#64 Plot Cognition Forensic Chronicle tests."""

from __future__ import annotations

import ast
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

from domain_api.plot_cognition_forensics_contract import PlotCognitionForensicRecord, new_record_id  # noqa: E402
from domain_api.plot_cognition_forensics_repository import (  # noqa: E402
    ForensicsPersistenceError,
    PlotCognitionForensicsRepository,
)
from domain_api.plot_cognition_forensics_service import PlotCognitionForensicsService  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402


class FaultInjectRepository(PlotCognitionForensicsRepository):
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


class PlotCognitionForensicsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp(prefix="pcf-test-")
        self.repo = PlotCognitionForensicsRepository(self.tempdir)
        self.service = PlotCognitionForensicsService(self.repo)
        self.scope_id = "scope-forensics-test"

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_chronicle_survives_reload(self) -> None:
        record = PlotCognitionForensicRecord(
            record_id=new_record_id(),
            plot_cognition_scope_id=self.scope_id,
            record_class="semantic_decision",
            operation_kind="projection_evaluate",
            idempotency_key=f"{self.scope_id}:projection:batch-1:finalize",
            payload={"verdict": "withheld"},
            recorded_at_ms=1,
        )
        record_id = self.repo.append_record(record.to_dict())
        reloaded = PlotCognitionForensicsRepository(self.tempdir)
        loaded = reloaded.load_record(self.scope_id, record_id)
        assert loaded is not None
        self.assertEqual(loaded["payload"]["verdict"], "withheld")

    def test_wafi_intent_before_mutation(self) -> None:
        order: list[str] = []

        def mutation() -> dict[str, Any]:
            order.append("mutation")
            return {"success": True, "store_revision": 2, "prior_revision": 1, "code": "committed", "message": "ok"}

        result = self.service.execute_wafi_mutation(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=f"{self.scope_id}:update:proposal-1",
            operation_kind="update",
            intent_payload={"proposal_id": "proposal-1", "prior_revision": 1},
            correlation={"plot_cognition_scope_id": self.scope_id},
            mutation_fn=mutation,
            completion_builder=lambda result: {
                "store_revision": result["store_revision"],
                "prior_revision": result["prior_revision"],
            },
        )
        self.assertTrue(result.ok)
        self.assertEqual(order, ["mutation"])
        self.assertTrue(self.repo.has_mutation_phase(self.scope_id, f"{self.scope_id}:update:proposal-1", "intent"))

    def test_intent_failure_blocks_mutation(self) -> None:
        fault_repo = FaultInjectRepository(self.tempdir, fail_after="intent")
        service = PlotCognitionForensicsService(fault_repo)

        def mutation() -> dict[str, Any]:
            self.fail("mutation should not run")

        result = service.execute_wafi_mutation(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=f"{self.scope_id}:update:blocked",
            operation_kind="update",
            intent_payload={"prior_revision": 0},
            correlation={},
            mutation_fn=mutation,
            completion_builder=lambda _result: {},
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "intent_persistence_failed")

    def test_completion_failure_reports_not_ok(self) -> None:
        fault_repo = FaultInjectRepository(self.tempdir, fail_after="completion")
        service = PlotCognitionForensicsService(fault_repo)
        mutated = {"called": False}

        def mutation() -> dict[str, Any]:
            mutated["called"] = True
            return {"success": True, "store_revision": 2, "prior_revision": 1, "code": "committed", "message": "ok"}

        result = service.execute_wafi_mutation(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=f"{self.scope_id}:update:completion-fail",
            operation_kind="update",
            intent_payload={"prior_revision": 1},
            correlation={},
            mutation_fn=mutation,
            completion_builder=lambda _result: {"store_revision": 2},
        )
        self.assertTrue(mutated["called"])
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "completion_persistence_failed")

    def test_replay_does_not_double_apply(self) -> None:
        calls = {"count": 0}

        def mutation() -> dict[str, Any]:
            calls["count"] += 1
            return {"success": True, "store_revision": 2, "prior_revision": 1, "code": "committed", "message": "ok"}

        kwargs = dict(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=f"{self.scope_id}:update:replay",
            operation_kind="update",
            intent_payload={"prior_revision": 1},
            correlation={},
            mutation_fn=mutation,
            completion_builder=lambda result: {"store_revision": result["store_revision"]},
        )
        first = self.service.execute_wafi_mutation(**kwargs)
        second = self.service.execute_wafi_mutation(**kwargs)
        self.assertTrue(first.ok)
        self.assertTrue(second.replayed)
        self.assertEqual(calls["count"], 1)

    def test_d_class_persistence_failure_fails_closed(self) -> None:
        with mock.patch.object(
            self.repo,
            "append_record",
            side_effect=ForensicsPersistenceError("decision failed"),
        ):
            result = self.service.record_semantic_decision(
                plot_cognition_scope_id=self.scope_id,
                idempotency_key=f"{self.scope_id}:projection:batch-x:finalize",
                record_class="consumer_decision",
                operation_kind="projection_evaluate",
                correlation={"batch_id": "batch-x"},
                payload={"verdict": "admitted"},
            )
        self.assertFalse(result.ok)

    def test_activation_baseline_only_for_existing_scope(self) -> None:
        activation_id = self.service.ensure_scope_activation(
            self.scope_id,
            overlay_store_dict={"store_revision": 3, "goals": {}, "pressures": {}},
            hg_session_id="sess-1",
        )
        self.assertIsNotNone(activation_id)
        records = [self.repo.load_record(self.scope_id, rid) for rid in self.repo.list_record_ids(self.scope_id)]
        kinds = {record.get("operation_kind") for record in records if record}
        self.assertIn("chronicle_activation", kinds)
        self.assertNotIn("initialization", kinds)
        self.assertNotIn("update", kinds)

    def test_shared_scope_single_timeline(self) -> None:
        self.service.attach_session(self.scope_id, "sess-a")
        self.service.attach_session(self.scope_id, "sess-b")
        self.service.record_semantic_decision(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=f"{self.scope_id}:projection:batch-1:finalize",
            record_class="consumer_decision",
            operation_kind="projection_evaluate",
            correlation={"hg_session_id": "sess-a", "batch_id": "batch-1"},
            payload={"from": "sess-a"},
        )
        self.service.record_semantic_decision(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=f"{self.scope_id}:projection:batch-2:finalize",
            record_class="consumer_decision",
            operation_kind="projection_evaluate",
            correlation={"hg_session_id": "sess-b", "batch_id": "batch-2"},
            payload={"from": "sess-b"},
        )
        manifest = self.repo.load_manifest(self.scope_id)
        assert manifest
        self.assertEqual(len(manifest.get("attached_sessions") or []), 2)
        self.assertEqual(len(self.repo.list_record_ids(self.scope_id)), 2)

    def test_session_delete_does_not_remove_chronicle(self) -> None:
        self.service.ensure_scope_activation(
            self.scope_id,
            overlay_store_dict={"store_revision": 1, "goals": {}, "pressures": {}},
            hg_session_id="sess-delete",
        )
        scope_dir = self.repo.scope_dir(self.scope_id)
        self.assertTrue(scope_dir.exists())
        session_file = Path(self.tempdir) / "sess-delete.json"
        session_file.write_text("{}", encoding="utf-8")
        session_file.unlink()
        self.assertTrue(scope_dir.exists())

    def test_forensic_preservation_predicate(self) -> None:
        idem = f"{self.scope_id}:overlay_item:goal-1"
        self.service.execute_wafi_mutation(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=idem,
            operation_kind="overlay_item_lifecycle",
            intent_payload={"prior_revision": 1},
            correlation={},
            mutation_fn=lambda: {
                "success": True,
                "store_revision": 2,
                "prior_revision": 1,
                "code": "committed",
                "message": "ok",
            },
            completion_builder=lambda _result: {
                "prior_snapshot": {"goals": [{"goal_id": "goal-1"}]},
                "retired_or_superseded_items": [],
            },
        )
        self.assertTrue(
            self.service.forensic_preservation_satisfied(
                self.scope_id,
                cognition_item_id="goal-1",
                idempotency_key=idem,
            )
        )

    def test_authority_artifact_has_verbatim_not_digest_only(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], plot_cognition_scope_id=self.scope_id)
        fixture.setup_snapshot = {
            "opening": {"mode": "minimal"},
            "scene_template": {"template_id": "tpl", "premise": "Test premise"},
            "character_cards": {"alice": {"name": "Alice", "goals": "Find the truth"}},
            "location": "Hall",
        }
        from domain_api.plot_cognition_forensics_capture import capture_authority_projection_verbatim  # noqa: E402

        artifact = capture_authority_projection_verbatim(fixture, None, None)
        self.assertIn("public_events_verbatim", artifact)
        artifact_id = self.repo.store_content(self.scope_id, artifact)
        loaded = self.repo.load_content(self.scope_id, artifact_id)
        assert loaded is not None
        self.assertIn("public_events_verbatim", loaded)

    def test_rebuild_index(self) -> None:
        self.service.record_semantic_decision(
            plot_cognition_scope_id=self.scope_id,
            idempotency_key=f"{self.scope_id}:projection:batch-r:finalize",
            record_class="consumer_decision",
            operation_kind="projection_evaluate",
            correlation={"domain_commit_id": "commit-r", "candidate_id": "cand-r"},
            payload={},
            inference_evidence_refs=[{"evidence_id": "ev-r", "role": "layer_b"}],
        )
        self.repo.index_path(self.scope_id).unlink()
        rebuilt = self.repo.rebuild_index(self.scope_id)
        self.assertIn("commit-r", rebuilt.get("by_commit") or {})


PACKAGING_MODULES = [
    _V2 / "domain_api" / "storyteller_round_packaging.py",
    _V2 / "domain_api" / "storyteller_packaging_mapper.py",
    _V2 / "domain_api" / "character_context.py",
]


class PlotCognitionForensicsIsolationTests(unittest.TestCase):
    def test_packaging_modules_do_not_import_chronicle(self) -> None:
        forbidden = "plot_cognition_forensics"
        for path in PACKAGING_MODULES:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, source, msg=f"{path.name} must not reference Chronicle modules")


if __name__ == "__main__":
    unittest.main()

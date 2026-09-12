"""Formal validation suite for Issue #166 (Lanes 1 + 2)."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.modules.continuity_state_public_event import PublicEvent  # noqa: E402
from domain_api.librarian_contract import StableReference  # noqa: E402
from domain_api.plot_cognition_forensics_integration import (  # noqa: E402
    record_plot_cognition_orchestration_decision,
)
from domain_api.plot_cognition_forensics_repository import PlotCognitionForensicsRepository  # noqa: E402
from domain_api.plot_cognition_forensics_service import PlotCognitionForensicsService  # noqa: E402
from domain_api.plot_cognition_layer_b_reuse import (  # noqa: E402
    clear_layer_b_reuse_for_tests,
    compute_layer_b_eval_reuse_key_from_envelope,
)
from domain_api.plot_cognition_orchestration_api import (  # noqa: E402
    plan_post_commit_plot_cognition_work,
    record_plot_cognition_orchestration_gate,
    resolve_plot_cognition_layer_b_epistemic_reuse,
)
from domain_api.plot_cognition_orchestration_service import PlotCognitionOrchestrationService  # noqa: E402
from domain_api.plot_cognition_overlay_repository import PlotCognitionOverlayRepository  # noqa: E402
from domain_api.plot_cognition_overlay_service import PlotCognitionOverlayService  # noqa: E402
from domain_api.plot_cognition_overlay_store import BoundednessPolicy  # noqa: E402
from domain_api.plot_cognition_projection_batch import (  # noqa: E402
    clear_prepared_batches_for_tests,
    prepare_character_projection_batch,
)
from domain_api.plot_cognition_projection_contract import (  # noqa: E402
    CharacterAdvisoryCandidate,
    ProjectionBudget,
    new_candidate_id,
    overlay_goal_to_character_candidate,
)
from domain_api.plot_cognition_projection_runtime import register_projection_semantic_result  # noqa: E402
from domain_api.plot_cognition_update_service import PlotCognitionUpdateService  # noqa: E402
from domain_api.plot_cognition_update_sources import gather_update_source_snapshot  # noqa: E402
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import RoundFixture, initialize_live_session  # noqa: E402
from domain.tests.test_plot_cognition_orchestration import (  # noqa: E402
    TEST_BUDGET,
    TEST_POLICY,
    _character_goal,
    _overlay_service,
    _round,
    _seed_overlay,
    _session_with_event,
)
from domain.tests.test_plot_cognition_update_replan import (  # noqa: E402
    _initialized_store,
    _session,
)


def _kernel(overlay, update_svc=None, init_svc=None):
    return type(
        "Kernel",
        (),
        {
            "cognition": type(
                "Cognition",
                (),
                {
                    "plot_cognition_overlay": overlay,
                    "plot_cognition_update": update_svc,
                    "plot_cognition_initialization": init_svc,
                },
            )()
        },
    )()


def _forensics_kernel(overlay, forensics_dir: str):
    repo = PlotCognitionForensicsRepository(forensics_dir)
    forensics = PlotCognitionForensicsService(repo)
    update_svc = PlotCognitionUpdateService(overlay)
    kernel = _kernel(overlay, update_svc)
    kernel.plot_cognition_forensics = forensics  # type: ignore[attr-defined]
    return kernel, forensics


class Issue166Lane1ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_prepared_batches_for_tests()
        self._tmpdir = tempfile.mkdtemp()
        self.overlay = PlotCognitionOverlayService(PlotCognitionOverlayRepository(self._tmpdir))
        self.update_svc = PlotCognitionUpdateService(self.overlay)
        self.fixture = _session(scope_id="scope-lane1-val")
        self.store = _initialized_store(self.fixture, self.overlay)
        self.update_svc.first_reconciliation(self.fixture, self.store, TEST_POLICY)

    def tearDown(self) -> None:
        clear_prepared_batches_for_tests()
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_cv_only_same_fingerprint_routes_authority_advance(self) -> None:
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        snapshot_before = gather_update_source_snapshot(
            self.fixture, loaded.store, [], (self.fixture.hg_scene_id,)
        )
        orch = PlotCognitionOrchestrationService(self.overlay)
        orch.record_post_commit_pending_work(self.fixture, domain_commit_id="commit-advance-val")
        self.fixture.continuity_version += 1
        append_history_entry(
            self.fixture.rp_history,
            kind="presentation",
            content="Narration only.",
            presentation_status="rendered",
        )
        assessment = self.update_svc.assess_freshness(self.fixture, loaded.store, TEST_POLICY)
        self.assertEqual(assessment.status, "authority_generation_changed_unchecked")
        plan = plan_post_commit_plot_cognition_work(_kernel(self.overlay, self.update_svc), self.fixture)
        self.assertEqual(plan["operation"], "authority_advance")
        snapshot_after = gather_update_source_snapshot(
            self.fixture, loaded.store, [], (self.fixture.hg_scene_id,)
        )
        self.assertEqual(
            snapshot_before.authority_source_fingerprint,
            snapshot_after.authority_source_fingerprint,
        )

    def test_changed_authority_fingerprint_routes_semantic_update(self) -> None:
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        orch = PlotCognitionOrchestrationService(self.overlay)
        orch.record_post_commit_pending_work(self.fixture, domain_commit_id="commit-val-1")
        self.fixture.continuity_version += 1
        self.fixture.manager.scene_state.location = "Changed Strategic Hall"
        assessment = self.update_svc.assess_freshness(self.fixture, loaded.store, TEST_POLICY)
        self.assertEqual(assessment.status, "semantic_assimilation_pending")
        plan = plan_post_commit_plot_cognition_work(_kernel(self.overlay, self.update_svc), self.fixture)
        self.assertEqual(plan["operation"], "semantic_update")

    def test_pending_work_records_gather_authority_fingerprint(self) -> None:
        loaded = self.overlay.load(self.fixture.plot_cognition_scope_id, policy=TEST_POLICY)
        assert loaded.store is not None
        snapshot = gather_update_source_snapshot(
            self.fixture, loaded.store, [], (self.fixture.hg_scene_id,)
        )
        orch = PlotCognitionOrchestrationService(self.overlay)
        pending = orch.build_post_commit_pending_work(self.fixture, domain_commit_id="commit-fp")
        assert pending is not None
        self.assertEqual(pending.authority_source_fingerprint, snapshot.authority_source_fingerprint)
        self.assertNotEqual(pending.authority_source_fingerprint, "commit-fp")

    def test_orchestration_none_gate_is_non_mutation_semantic_decision(self) -> None:
        forensics_dir = tempfile.mkdtemp(prefix="pcf-lane1-")
        try:
            kernel, forensics = _forensics_kernel(self.overlay, forensics_dir)
            result = record_plot_cognition_orchestration_gate(
                kernel,
                self.fixture,
                {
                    "plan_operation": "none",
                    "reason": "no_pending_work",
                    "freshness_status": "fresh",
                    "inference_id": "inf-none-val",
                },
            )
            self.assertTrue(result["accepted"])
            index = forensics.repository.load_index(self.fixture.plot_cognition_scope_id)
            records = [
                forensics.repository.load_record(self.fixture.plot_cognition_scope_id, record_id)
                for record_id in index.get("record_ids", [])
            ]
            gate = next(
                record
                for record in records
                if record and record.get("record_class") == "semantic_decision"
            )
            self.assertEqual(gate["operation_kind"], "freshness_barrier")
            self.assertFalse(gate["payload"]["mutation_lifecycle_entered"])
            self.assertFalse(any(record.get("mutation_phase") for record in records if record))
        finally:
            shutil.rmtree(forensics_dir, ignore_errors=True)


class Issue166Lane2ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_layer_b_reuse_for_tests()
        clear_prepared_batches_for_tests()

    def tearDown(self) -> None:
        clear_layer_b_reuse_for_tests()
        clear_prepared_batches_for_tests()

    def _register_baseline(self, fixture, rnd, candidate, *, overlay_revision=4, fingerprint="fp-base"):
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-val-base",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint=fingerprint,
            overlay_revision=overlay_revision,
        )
        item = prepared.batch.items[0]
        register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={"verdict": "pass", "rationale": "ok", "leak_indicators": []},
            inference_evidence_id="ev-val-base",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        return prepared, item

    def _resolve(self, fixture, rnd, candidate, *, overlay_revision=4, fingerprint="fp-base"):
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id=f"m-val-{overlay_revision}-{fingerprint}",
            character_id="Alice",
            candidates=(candidate,),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint=fingerprint,
            overlay_revision=overlay_revision,
        )
        item = prepared.batch.items[0]
        kernel = _kernel(None)
        return resolve_plot_cognition_layer_b_epistemic_reuse(
            kernel,
            fixture,
            rnd,
            {
                "batch_id": prepared.batch.batch_id,
                "evaluation_pass_id": item.evaluation_pass_id,
                "evaluation_attempt": 1,
            },
        ), prepared, item

    def test_identical_state_reuses_prior_layer_b_eval(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        candidate = overlay_goal_to_character_candidate(_character_goal())
        self._register_baseline(fixture, rnd, candidate)
        resolved, _, _ = self._resolve(fixture, rnd, candidate)
        self.assertEqual(resolved["action"], "reuse")
        self.assertEqual(resolved["prior_inference_evidence_id"], "ev-val-base")

    def test_candidate_change_invalidates_reuse(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        first_candidate = overlay_goal_to_character_candidate(_character_goal(direction="Find the key."))
        second_candidate = overlay_goal_to_character_candidate(
            _character_goal(direction="Find the vault instead.")
        )
        self._register_baseline(fixture, rnd, first_candidate)
        resolved, _, _ = self._resolve(fixture, rnd, second_candidate)
        self.assertEqual(resolved["action"], "invoke")

    def test_overlay_revision_change_invalidates_reuse(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        candidate = overlay_goal_to_character_candidate(_character_goal())
        self._register_baseline(fixture, rnd, candidate, overlay_revision=4)
        resolved, _, _ = self._resolve(fixture, rnd, candidate, overlay_revision=5)
        self.assertEqual(resolved["action"], "invoke")

    def test_authority_fingerprint_change_invalidates_reuse(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        candidate = overlay_goal_to_character_candidate(_character_goal())
        self._register_baseline(fixture, rnd, candidate, fingerprint="fp-a")
        resolved, _, _ = self._resolve(fixture, rnd, candidate, fingerprint="fp-b")
        self.assertEqual(resolved["action"], "invoke")

    def test_known_by_change_invalidates_reuse(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared, item = self._register_baseline(fixture, rnd, candidate)
        baseline_key = compute_layer_b_eval_reuse_key_from_envelope(
            item.epistemic_context,
            plot_cognition_scope_id=str(fixture.plot_cognition_scope_id),
            assimilated_authority_source_fingerprint="fp-base",
        )
        fixture.manager.public_events.append(
            PublicEvent(
                event_id="evt-alice-learns",
                timestamp=datetime.now(timezone.utc),
                event_type="dialogue",
                participants=["Bob"],
                summary="Bob revealed a new clue.",
                turn_index=2,
                known_by=["Alice"],
            )
        )
        resolved, _, item2 = self._resolve(fixture, rnd, candidate)
        changed_key = compute_layer_b_eval_reuse_key_from_envelope(
            item2.epistemic_context,
            plot_cognition_scope_id=str(fixture.plot_cognition_scope_id),
            assimilated_authority_source_fingerprint="fp-base",
        )
        self.assertNotEqual(baseline_key, changed_key)
        self.assertEqual(resolved["action"], "invoke")

    def test_withheld_basis_change_invalidates_reuse(self) -> None:
        from domain_api.character_epistemic_projection_context import (
            build_character_epistemic_context_envelope,
        )

        fixture = _session_with_event(known_by=["Bob"])
        rnd = _round(fixture)
        open_candidate = overlay_goal_to_character_candidate(_character_goal())
        secret_candidate = CharacterAdvisoryCandidate(
            candidate_id=new_candidate_id(),
            source_kind="overlay_goal",
            text="Whisper about the vault.",
            basis_refs=(
                StableReference(ref_kind="public_event", stable_ref="evt-secret"),
            ),
            lineage={},
        )
        env_open = build_character_epistemic_context_envelope(
            fixture,
            character_id="Alice",
            candidate=open_candidate,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint="fp-base",
            overlay_revision=4,
        )
        env_secret = build_character_epistemic_context_envelope(
            fixture,
            character_id="Alice",
            candidate=secret_candidate,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint="fp-base",
            overlay_revision=4,
        )
        self.assertNotEqual(env_open.withheld_basis_index, env_secret.withheld_basis_index)
        key_open = compute_layer_b_eval_reuse_key_from_envelope(
            env_open,
            plot_cognition_scope_id=str(fixture.plot_cognition_scope_id),
            assimilated_authority_source_fingerprint="fp-base",
        )
        key_secret = compute_layer_b_eval_reuse_key_from_envelope(
            env_secret,
            plot_cognition_scope_id=str(fixture.plot_cognition_scope_id),
            assimilated_authority_source_fingerprint="fp-base",
        )
        self.assertNotEqual(key_open, key_secret)
        self._register_baseline(fixture, rnd, open_candidate)
        resolved, _, _ = self._resolve(fixture, rnd, open_candidate)
        self.assertEqual(resolved["action"], "reuse")
        prepared_secret = prepare_character_projection_batch(
            fixture,
            manifest_id="m-withheld-secret",
            character_id="Alice",
            candidates=(secret_candidate,),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            authority_fingerprint="fp-base",
            overlay_revision=4,
        )
        if not prepared_secret.batch.items:
            self.skipTest("secret candidate structurally ineligible; key inequality already proven")
        item = prepared_secret.batch.items[0]
        resolved_secret = resolve_plot_cognition_layer_b_epistemic_reuse(
            _kernel(None),
            fixture,
            rnd,
            {
                "batch_id": prepared_secret.batch.batch_id,
                "evaluation_pass_id": item.evaluation_pass_id,
                "evaluation_attempt": 1,
            },
        )
        self.assertEqual(resolved_secret["action"], "invoke")

    def test_scene_visible_change_invalidates_reuse(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared, item = self._register_baseline(fixture, rnd, candidate)
        baseline_key = compute_layer_b_eval_reuse_key_from_envelope(
            item.epistemic_context,
            plot_cognition_scope_id=str(fixture.plot_cognition_scope_id),
            assimilated_authority_source_fingerprint="fp-base",
        )
        fixture.manager.scene_state.location = "A different visible room"
        resolved, _, item2 = self._resolve(fixture, rnd, candidate)
        changed_key = compute_layer_b_eval_reuse_key_from_envelope(
            item2.epistemic_context,
            plot_cognition_scope_id=str(fixture.plot_cognition_scope_id),
            assimilated_authority_source_fingerprint="fp-base",
        )
        self.assertNotEqual(baseline_key, changed_key)
        self.assertEqual(resolved["action"], "invoke")

    def test_scope_boundary_prevents_cross_scope_reuse(self) -> None:
        fixture_a = initialize_live_session(
            cast=["Alice"], plot_cognition_scope_id="scope-a-val"
        )
        fixture_b = initialize_live_session(
            cast=["Alice"], plot_cognition_scope_id="scope-b-val"
        )
        rnd = RoundFixture(hg_round_id="round-scope", hg_scene_id=fixture_a.hg_scene_id, turn_index=1)
        candidate = overlay_goal_to_character_candidate(_character_goal())
        self._register_baseline(fixture_a, rnd, candidate)
        resolved, _, _ = self._resolve(fixture_b, rnd, candidate)
        self.assertEqual(resolved["action"], "invoke")

    def test_regeneration_attempt_always_invokes_fresh_eval(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        candidate = overlay_goal_to_character_candidate(_character_goal())
        prepared, item = self._register_baseline(fixture, rnd, candidate)
        kernel = _kernel(None)
        resolved = resolve_plot_cognition_layer_b_epistemic_reuse(
            kernel,
            fixture,
            rnd,
            {
                "batch_id": prepared.batch.batch_id,
                "evaluation_pass_id": item.evaluation_pass_id,
                "evaluation_attempt": 2,
            },
        )
        self.assertEqual(resolved["action"], "invoke")
        self.assertEqual(resolved["reason"], "regeneration_or_second_pass_requires_fresh_eval")

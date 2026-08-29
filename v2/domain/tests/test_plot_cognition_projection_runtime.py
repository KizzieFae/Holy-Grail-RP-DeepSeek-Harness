"""#66 projection runtime registration and regeneration authority tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.plot_cognition_orchestration_contract import (  # noqa: E402
    REGENERATION_GUIDANCE_SCHEMA,
    RegenerationGuidance,
)
from domain_api.plot_cognition_projection_batch import (  # noqa: E402
    clear_prepared_batches_for_tests,
    finalize_character_projection_batch,
    prepare_character_projection_batch,
)
from domain_api.plot_cognition_projection_contract import (  # noqa: E402
    ProjectionBudget,
    SemanticEvaluationResult,
    overlay_goal_to_character_candidate,
)
from domain_api.plot_cognition_projection_runtime import (  # noqa: E402
    finalize_projection_regeneration,
    prepare_projection_regeneration,
    register_projection_semantic_result,
)
from domain_api.session_state import RoundFixture, initialize_live_session  # noqa: E402
from domain.tests.test_plot_cognition_orchestration import (  # noqa: E402
    TEST_BUDGET,
    _character_goal,
    _round,
    _session_with_event,
)


def _guidance() -> RegenerationGuidance:
    return RegenerationGuidance(
        schema=REGENERATION_GUIDANCE_SCHEMA,
        violation_class="basis_leak",
        safe_constraints=("Do not reveal the vault code.",),
        do_not_introduce=("vault code",),
        affected_dimensions=("knowledge_boundary",),
    )


class PlotCognitionProjectionRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_prepared_batches_for_tests()

    def tearDown(self) -> None:
        clear_prepared_batches_for_tests()

    def test_semantic_registration_idempotent_and_conflict(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-runtime",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        semantic = {
            "verdict": "pass",
            "rationale": "ok",
            "leak_indicators": [],
        }
        first = register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw=semantic,
            inference_evidence_id="ev-1",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        self.assertTrue(first["accepted"])
        replay = register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw=semantic,
            inference_evidence_id="ev-1",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        self.assertTrue(replay["accepted"])
        self.assertEqual(replay.get("reason"), "idempotent_replay")
        conflict = register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={**semantic, "verdict": "withhold"},
            inference_evidence_id="ev-2",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        self.assertFalse(conflict["accepted"])
        self.assertEqual(conflict.get("reason"), "conflicting_semantic_replay")

    def test_regeneration_prepare_rejects_without_registered_rewrite(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-regen-gate",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        denied = prepare_projection_regeneration(
            None,
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        self.assertFalse(denied["accepted"])

    def test_regeneration_authorization_single_use(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-regen-once",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        guidance = _guidance()
        register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={
                "verdict": "rewrite_required",
                "rationale": "leak",
                "regeneration_guidance": guidance.to_dict(),
            },
            inference_evidence_id="ev-eval",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        regen_prepare = prepare_projection_regeneration(
            None,
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        self.assertTrue(regen_prepare["accepted"])
        regen_prepare_again = prepare_projection_regeneration(
            None,
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        self.assertFalse(regen_prepare_again["accepted"])
        regen_finalize = finalize_projection_regeneration(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            regeneration_prepare_id=regen_prepare["regeneration_prepare_id"],
            candidate_id=item.candidate.candidate_id,
            regenerated_text="Stay curious about the key without naming secrets.",
            generator_inference_evidence_id="ev-gen",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        self.assertTrue(regen_finalize["accepted"])
        regen_finalize_twice = finalize_projection_regeneration(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            regeneration_prepare_id=regen_prepare["regeneration_prepare_id"],
            candidate_id=item.candidate.candidate_id,
            regenerated_text="Another rewrite.",
            generator_inference_evidence_id="ev-gen-2",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        self.assertFalse(regen_finalize_twice["accepted"])

    def test_finalize_uses_registered_results(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-finalize-registered",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={"verdict": "pass", "rationale": "ok", "leak_indicators": []},
            inference_evidence_id="ev-pass",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        from domain_api.plot_cognition_projection_runtime import (  # noqa: E402
            collect_regeneration_inputs,
            collect_registered_results_for_finalize,
        )

        first_pass, second_pass = collect_registered_results_for_finalize(prepared.batch.batch_id)
        finalized = finalize_character_projection_batch(
            fixture,
            batch_id=prepared.batch.batch_id,
            semantic_results=tuple(first_pass),
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            regeneration_inputs=collect_regeneration_inputs(prepared.batch.batch_id),
            second_pass_results=second_pass,
        )
        self.assertTrue(finalized.contributions)

    def test_stale_binding_rejects_registration(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-stale-binding",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        denied = register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={"verdict": "pass", "rationale": "ok", "leak_indicators": []},
            inference_evidence_id="ev-stale",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index) + 99,
            evaluation_attempt=1,
        )
        self.assertFalse(denied["accepted"])
        self.assertEqual(denied["reason"], "stale_projection_batch_binding")

    def test_semantic_evaluation_ceiling_rejects_third_registration(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-ceiling",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        guidance = _guidance()
        register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={
                "verdict": "rewrite_required",
                "rationale": "leak",
                "regeneration_guidance": guidance.to_dict(),
            },
            inference_evidence_id="ev-1",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        regen_prepare = prepare_projection_regeneration(
            None,
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        finalize_projection_regeneration(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            regeneration_prepare_id=regen_prepare["regeneration_prepare_id"],
            candidate_id=item.candidate.candidate_id,
            regenerated_text="Safe rewrite.",
            generator_inference_evidence_id="ev-gen",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        second = register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={"verdict": "pass", "rationale": "ok", "leak_indicators": []},
            inference_evidence_id="ev-2",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=2,
        )
        self.assertTrue(second["accepted"])
        third = register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={"verdict": "withhold", "rationale": "extra", "leak_indicators": []},
            inference_evidence_id="ev-3",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=2,
        )
        self.assertFalse(third["accepted"])
        self.assertEqual(third["reason"], "conflicting_semantic_replay")

    def test_invalid_rewrite_guidance_rejected(self) -> None:
        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-bad-guidance",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        denied = register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={
                "verdict": "rewrite_required",
                "rationale": "leak",
                "regeneration_guidance": {"schema": REGENERATION_GUIDANCE_SCHEMA, "safe_constraints": []},
            },
            inference_evidence_id="ev-bad",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        self.assertFalse(denied["accepted"])
        self.assertEqual(denied["reason"], "invalid_regeneration_guidance")

    def test_finalize_fail_closed_when_chronicle_persistence_fails(self) -> None:
        from unittest import mock

        from domain_api.plot_cognition_orchestration_api import finalize_plot_cognition_projection

        fixture = _session_with_event(known_by=["Alice"])
        rnd = _round(fixture)
        prepared = prepare_character_projection_batch(
            fixture,
            manifest_id="m-chronicle-fail",
            character_id="Alice",
            candidates=(overlay_goal_to_character_candidate(_character_goal()),),
            budget=TEST_BUDGET,
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
        )
        item = prepared.batch.items[0]
        register_projection_semantic_result(
            fixture,
            batch_id=prepared.batch.batch_id,
            evaluation_pass_id=item.evaluation_pass_id,
            candidate_id=item.candidate.candidate_id,
            semantic_raw={"verdict": "pass", "rationale": "ok", "leak_indicators": []},
            inference_evidence_id="ev-pass",
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            evaluation_attempt=1,
        )
        class _Kernel:
            cognition = type("C", (), {"plot_cognition_overlay": None})()

        with mock.patch(
            "domain_api.plot_cognition_forensics_integration.record_projection_decisions",
            return_value=False,
        ):
            result = finalize_plot_cognition_projection(
                _Kernel(),
                fixture,
                rnd,
                {
                    "batch_id": prepared.batch.batch_id,
                    "use_registered_results": True,
                },
            )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "forensic_persistence_failed")
        self.assertEqual(result["contributions"], [])


if __name__ == "__main__":
    unittest.main()

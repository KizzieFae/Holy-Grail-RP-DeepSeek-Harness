"""Issue #151 — environmental cognition status / false sufficiency remediation."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest

from domain_api.narrator_environment_cognition import (
    classify_environment_cognition_outcome,
    finalize_narrator_environment_cognition,
    parse_n1_cognition_result,
    record_environment_cognition_failure,
)
from domain_api.narrator_environment_sufficiency import (
    build_sufficiency_undetermined_obligation,
    reconcile_post_mediation_environmental_resolutions,
)
from domain_api.narrator_environment_projection import build_environmental_current_view
from domain_api.kernel import DomainKernel
from domain_api.story_knowledge_repository import StoryKnowledgeRepository
from domain_api.story_knowledge_service import StoryKnowledgeService
from domain_api.session_state import CharacterTurnRecord, initialize_live_session


class EnvironmentCognitionClassificationTests(unittest.TestCase):
    def test_d1_valid_sufficient(self) -> None:
        raw = {
            "baseline_sufficient": True,
            "information_needs": [],
            "resolutions": [],
        }
        n1, parsed = classify_environment_cognition_outcome(raw, None)
        self.assertEqual(n1.cognition_status, "determined")
        self.assertEqual(n1.status_reason, "model_result")
        self.assertTrue(n1.baseline_sufficient)
        self.assertIsNotNone(parsed)

    def test_d2_valid_insufficient(self) -> None:
        raw = {
            "baseline_sufficient": False,
            "information_needs": [{"need_id": "need-1", "question": "What color are the walls?"}],
            "resolutions": [{"need_id": "need-1", "category": "B1", "detail": "teal walls"}],
        }
        n1, _ = classify_environment_cognition_outcome(raw, None)
        self.assertEqual(n1.cognition_status, "determined")
        self.assertFalse(n1.baseline_sufficient)
        self.assertEqual(len(n1.information_needs), 1)

    def test_d3_true_with_needs_contract_invalid(self) -> None:
        raw = {
            "baseline_sufficient": True,
            "information_needs": [{"need_id": "need-1", "question": "Why?"}],
            "resolutions": [],
        }
        n1, parsed = classify_environment_cognition_outcome(raw, None)
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "contract_invalid")
        self.assertIsNone(n1.baseline_sufficient)
        self.assertIsNone(parsed)

    def test_d4_false_without_needs_contract_invalid(self) -> None:
        raw = {"baseline_sufficient": False, "information_needs": [], "resolutions": []}
        n1, _ = classify_environment_cognition_outcome(raw, None)
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "contract_invalid")
        self.assertIsNone(n1.baseline_sufficient)

    def test_d5_missing_sufficiency_contract_invalid(self) -> None:
        raw = {"information_needs": [], "resolutions": []}
        n1, _ = classify_environment_cognition_outcome(raw, None)
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "contract_invalid")

    def test_d6_wrong_sufficiency_type_contract_invalid(self) -> None:
        raw = {
            "baseline_sufficient": "yes",
            "information_needs": [],
            "resolutions": [],
        }
        n1, _ = classify_environment_cognition_outcome(raw, None)
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "contract_invalid")

    def test_d7_schema_invalid_missing_resolutions(self) -> None:
        raw = {"baseline_sufficient": True, "information_needs": []}
        n1, _ = classify_environment_cognition_outcome(raw, None)
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "contract_invalid")

    def test_d8_malformed_json(self) -> None:
        n1, _ = classify_environment_cognition_outcome("not-json", None)
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "malformed_output")

    def test_d9_empty_output(self) -> None:
        n1, _ = classify_environment_cognition_outcome("", None)
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "empty_output")

    def test_d10_provider_limit_unusable(self) -> None:
        n1, _ = classify_environment_cognition_outcome(
            "",
            {"finish_kind": "max-tokens", "inference_failed": False},
        )
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "provider_limit")

    def test_d11_provider_limit_with_valid_contract_still_determined(self) -> None:
        raw = json.dumps(
            {
                "baseline_sufficient": True,
                "information_needs": [],
                "resolutions": [],
            }
        )
        n1, parsed = classify_environment_cognition_outcome(
            raw,
            {"finish_kind": "max-tokens", "inference_failed": False},
        )
        self.assertEqual(n1.cognition_status, "determined")
        self.assertEqual(n1.status_reason, "model_result")
        self.assertIsNotNone(parsed)

    def test_d12_inference_error(self) -> None:
        n1, _ = classify_environment_cognition_outcome(
            "",
            {"inference_failed": True, "finish_kind": "error"},
        )
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertEqual(n1.status_reason, "inference_error")

    def test_d21_legacy_coercion_removed(self) -> None:
        n1 = parse_n1_cognition_result(
            {"baseline_sufficient": False, "information_needs": [], "resolutions": []}
        )
        self.assertEqual(n1.cognition_status, "indeterminate")
        self.assertIsNone(n1.baseline_sufficient)


class EnvironmentCognitionObligationTests(unittest.TestCase):
    def test_d14_indeterminate_not_no_material_obligation(self) -> None:
        n1, _ = classify_environment_cognition_outcome("", None)
        fixture = initialize_live_session(cast=["Alice"])
        view = build_environmental_current_view(fixture, story_records=[])
        _, _, obligations = reconcile_post_mediation_environmental_resolutions(
            n1=n1,
            resolutions=[],
            librarian_outcomes=[],
            n2_raw_items=[],
            current_view=view,
        )
        self.assertEqual(len(obligations), 1)
        self.assertEqual(obligations[0].render_behavior, "sufficiency_undetermined")
        self.assertNotEqual(obligations[0].render_behavior, "no_material_obligation")

    def test_d15_determined_sufficient_still_no_material_obligation(self) -> None:
        n1, _ = classify_environment_cognition_outcome(
            {
                "baseline_sufficient": True,
                "information_needs": [],
                "resolutions": [],
            },
            None,
        )
        fixture = initialize_live_session(cast=["Alice"])
        view = build_environmental_current_view(fixture, story_records=[])
        _, _, obligations = reconcile_post_mediation_environmental_resolutions(
            n1=n1,
            resolutions=[],
            librarian_outcomes=[],
            n2_raw_items=[],
            current_view=view,
        )
        self.assertEqual(obligations[0].render_behavior, "no_material_obligation")


class EnvironmentCognitionFinalizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.service = StoryKnowledgeService(StoryKnowledgeRepository(self._tmpdir))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _turn(self) -> tuple:
        fixture = initialize_live_session(cast=["Kizzie"], location="Ayame doorstep")
        turn = CharacterTurnRecord(
            character_id="Kizzie",
            committed_move={"move_schema_version": 2, "beats": []},
            domain_commit_id="commit-kizzie-1",
            continuity_turn_index=1,
            director_decision={},
        )
        return fixture, turn

    def test_indeterminate_finalize_skips_b2(self) -> None:
        fixture, turn = self._turn()
        result = finalize_narrator_environment_cognition(
            fixture,
            turn,
            story_service=self.service,
            cognition_raw="",
            inference_envelope={"finish_kind": "max-tokens", "inference_failed": False},
        )
        self.assertEqual(result["cognition_status"], "indeterminate")
        self.assertIsNone(result["baseline_sufficient"])
        obligations = result["environmental_response_obligations"]
        self.assertEqual(obligations[0]["render_behavior"], "sufficiency_undetermined")
        self.assertEqual(result["establishment_decisions"], [])

    def test_record_failure_no_affirmative_sufficiency(self) -> None:
        fixture, turn = self._turn()
        audit = record_environment_cognition_failure(
            fixture,
            turn,
            failure_stage="substrate_exception",
            failure_reason="import_error",
        )
        self.assertTrue(audit["cognition_failed"])
        self.assertEqual(audit["cognition_status"], "failed")
        self.assertIsNone(audit["n1"]["baseline_sufficient"])
        self.assertEqual(
            audit["environmental_response_obligations"][0]["render_behavior"],
            "cognition_unavailable",
        )


class ScenarioIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.service = StoryKnowledgeService(StoryKnowledgeRepository(self._tmpdir))
        self.kernel = DomainKernel.for_fixture_store()

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _commit_kizzie_lookaround(self) -> tuple[str, str, str, int]:
        from domain_api.contract import CommitRequest, RoundStartRequest

        scene = self.kernel.create_scene(cast=["Kizzie"], location="Ayame doorstep")
        rnd = self.kernel.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
        commit = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-kizzie-look",
                hg_scene_id=scene.hg_scene_id,
                hg_round_id=rnd.hg_round_id,
                character_id="Kizzie",
                validated_move={
                    "move_schema_version": 2,
                    "beats": [
                        {
                            "type": "action",
                            "action": "looked around, hesitating to knock on the door",
                        }
                    ],
                },
                director_decision={
                    "next_actor": "Kizzie",
                    "end_round": True,
                    "reason": "test",
                    "environment_event": "",
                    "tension_shift": "",
                },
                expected_turn_index=0,
            )
        )
        assert commit.committed and commit.domain_commit_id is not None
        return (
            scene.hg_scene_id,
            rnd.hg_round_id,
            commit.domain_commit_id,
            commit.continuity_turn_index or 1,
        )

    def test_s1_kizzie_injected_empty_output_manifest_undetermined(self) -> None:
        from domain_api.contract import NarratorContextPrepareRequest

        scene_id, rnd_id, commit_id, turn_idx = self._commit_kizzie_lookaround()
        rnd = self.kernel._require_round(self.kernel.store.require(scene_id), rnd_id)
        turn = next(
            item for item in rnd.character_turns if item.domain_commit_id == commit_id
        )
        fixture = self.kernel.store.require(scene_id)
        finalized = finalize_narrator_environment_cognition(
            fixture,
            turn,
            story_service=self.service,
            cognition_raw="",
            inference_envelope={
                "finish_kind": "max-tokens",
                "inference_failed": False,
                "inference_attempt_id": "inf-kizzie-env-cog",
            },
        )
        self.assertEqual(finalized["cognition_status"], "indeterminate")
        self.assertNotEqual(
            finalized["environmental_response_obligations"][0]["render_behavior"],
            "no_material_obligation",
        )
        manifest = self.kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=rnd_id,
                inference_id="inf-nar-kizzie",
                character_id="Kizzie",
                domain_commit_id=commit_id,
                continuity_turn_index=turn_idx,
                attempt_index=0,
                environmental_response_obligations_text=finalized[
                    "environmental_response_obligations_text"
                ],
                environmental_response_obligations=finalized[
                    "environmental_response_obligations"
                ],
            )
        )
        obligation = next(
            c
            for c in manifest.contributions
            if c.source_kind == "environmental_response_obligation"
        )
        self.assertIn("sufficiency_undetermined", obligation.content)
        self.assertIn("could NOT be determined", obligation.content)

    def test_s3_determined_sufficient_still_no_material_obligation(self) -> None:
        from domain_api.contract import NarratorContextPrepareRequest

        scene_id, rnd_id, commit_id, turn_idx = self._commit_kizzie_lookaround()
        fixture = self.kernel.store.require(scene_id)
        rnd = self.kernel._require_round(fixture, rnd_id)
        turn = next(
            item for item in rnd.character_turns if item.domain_commit_id == commit_id
        )
        finalized = finalize_narrator_environment_cognition(
            fixture,
            turn,
            story_service=self.service,
            n1_raw={
                "baseline_sufficient": True,
                "information_needs": [],
                "resolutions": [],
            },
            n2_raw={"resolutions": []},
        )
        self.assertEqual(finalized["cognition_status"], "determined")
        manifest = self.kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=rnd_id,
                inference_id="inf-nar-sufficient",
                character_id="Kizzie",
                domain_commit_id=commit_id,
                continuity_turn_index=turn_idx,
                attempt_index=0,
                environmental_response_obligations_text=finalized[
                    "environmental_response_obligations_text"
                ],
                environmental_response_obligations=finalized[
                    "environmental_response_obligations"
                ],
            )
        )
        obligation = next(
            c
            for c in manifest.contributions
            if c.source_kind == "environmental_response_obligation"
        )
        self.assertIn("no_material_obligation", obligation.content)
    def test_undetermined_obligation_has_no_grounded_material(self) -> None:
        obligation = build_sufficiency_undetermined_obligation("empty_output")
        self.assertEqual(obligation.grounded_material, ())
        self.assertEqual(obligation.render_behavior, "sufficiency_undetermined")

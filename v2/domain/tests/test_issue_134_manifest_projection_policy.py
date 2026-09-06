"""Issue #134 — model-only prompt contribution policy and fail-closed validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    NarratorContextPrepareRequest,
    PromptContribution,
    RoundStartRequest,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.manifest_projection_policy import (  # noqa: E402
    ManifestProjectionPolicyError,
    validate_model_context_contributions,
)
from domain_api.manifest_validation import finalize_prompt_contribution_manifest  # noqa: E402


class ManifestProjectionPolicyTests(unittest.TestCase):
    def test_semantic_correction_allowed_for_character_turn(self) -> None:
        validate_model_context_contributions(
            "character_turn",
            [
                PromptContribution(
                    contribution_id="c-semantic-correction",
                    source_kind="semantic_correction",
                    authority_class="suggestive",
                    knowledge_ids=("eval-1",),
                    priority=29,
                    content='{"reason":"retry"}',
                    provenance={"visibility": "orchestration_only"},
                )
            ],
        )

    def test_narrator_environment_cognition_rejected_for_presentation(self) -> None:
        with self.assertRaises(ManifestProjectionPolicyError):
            validate_model_context_contributions(
                "narrator_presentation",
                [
                    PromptContribution(
                        contribution_id="c-env-cog",
                        source_kind="narrator_environment_cognition",
                        authority_class="derived",
                        knowledge_ids=("audit-1",),
                        priority=28,
                        content='{"forensic":"audit"}',
                        provenance={"visibility": "orchestration_only"},
                    )
                ],
            )

    def test_provenance_visibility_does_not_affect_policy(self) -> None:
        with self.assertRaises(ManifestProjectionPolicyError):
            validate_model_context_contributions(
                "narrator_presentation",
                [
                    PromptContribution(
                        contribution_id="c-env-cog",
                        source_kind="narrator_environment_cognition",
                        authority_class="derived",
                        knowledge_ids=("audit-1",),
                        priority=28,
                        content='{"forensic":"audit"}',
                        provenance={"visibility": "model"},
                    )
                ],
            )


class NarratorPresentationPolicyIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = DomainKernel.for_fixture_store()
        self.scene_id = self.kernel.create_scene().hg_scene_id
        self.rnd_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=self.scene_id)
        ).hg_round_id
        commit = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-commit-134",
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                character_id="Alice",
                validated_move={
                    "move_schema_version": 2,
                    "beats": [{"type": "action", "action": "looks around"}],
                },
                director_decision={
                    "next_actor": "Alice",
                    "end_round": True,
                    "reason": "test",
                    "environment_event": "",
                    "tension_shift": "",
                },
                expected_turn_index=0,
            )
        )
        assert commit.committed and commit.domain_commit_id
        self.commit_id = commit.domain_commit_id
        self.turn_idx = commit.continuity_turn_index or 1

    def test_presentation_manifest_has_inference_kind(self) -> None:
        manifest = self.kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                inference_id="inf-nar-134",
                character_id="Alice",
                domain_commit_id=self.commit_id,
                continuity_turn_index=self.turn_idx,
                attempt_index=0,
            )
        )
        self.assertEqual(manifest.inference_kind, "narrator_presentation")
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertNotIn("narrator_environment_cognition", kinds)

    def test_finalize_rejects_disallowed_kind(self) -> None:
        with self.assertRaises(ManifestProjectionPolicyError):
            finalize_prompt_contribution_manifest(
                "narrator_presentation",
                manifest_id="manifest-bad",
                inference_id="inf-bad",
                hg_scene_id=self.scene_id,
                hg_round_id=self.rnd_id,
                role="narrator",
                character_id="Alice",
                turn_index=1,
                attempt_index=0,
                contributions=[
                    PromptContribution(
                        contribution_id="bad",
                        source_kind="narrator_environment_cognition",
                        authority_class="derived",
                        knowledge_ids=("x",),
                        priority=1,
                        content="{}",
                    )
                ],
            )

    def test_validate_prompt_contribution_manifest_requires_inference_kind(self) -> None:
        from domain_api.contract import PromptContributionManifest
        from domain_api.manifest_validation import validate_prompt_contribution_manifest

        manifest = PromptContributionManifest(
            manifest_id="manifest-no-kind",
            inference_id="inf-no-kind",
            inference_kind="",
            hg_scene_id=self.scene_id,
            hg_round_id=self.rnd_id,
            role="narrator",
            character_id="Alice",
            turn_index=1,
            attempt_index=0,
            contributions=(),
        )
        with self.assertRaises(ValueError):
            validate_prompt_contribution_manifest(manifest)


if __name__ == "__main__":
    unittest.main()

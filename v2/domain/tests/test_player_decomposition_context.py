"""Tests for player decomposition prepare-context (#109)."""

from __future__ import annotations

import unittest

from domain_api.contract import PlayerDecompositionContextPrepareRequest
from domain_api.kernel import DomainKernel
from domain_api.player_decomposition_context import prepare_player_decomposition_context
from narrative_visibility_prompt import PLAYER_DECOMPOSITION_OUTPUT_INSTRUCTION


class PlayerDecompositionContextTests(unittest.TestCase):
    def test_prepare_manifest_contains_canonical_output_contract(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=["Ayame", "Kizzie"])
        fixture = kernel.store.require(created.hg_scene_id)
        req = PlayerDecompositionContextPrepareRequest(
            hg_session_id=created.hg_scene_id,
            inference_id="player-decomposition-test-1",
            hg_round_id="hg-round-test",
            attempt_index=0,
        )
        manifest = prepare_player_decomposition_context(fixture, req)

        self.assertEqual(manifest.role, "player_decomposition")
        self.assertEqual(manifest.manifest_id, "manifest-player-decomposition-player-decomposition-test-1")
        self.assertEqual(len(manifest.contributions), 1)

        instruction = manifest.contributions[0]
        self.assertEqual(instruction.source_kind, "inference_instruction")
        self.assertEqual(
            instruction.contribution_id,
            "manifest-player-decomposition-player-decomposition-test-1-instruction",
        )
        self.assertIn("OUTPUT FORMAT — return ONLY valid JSON", instruction.content)
        self.assertIn('"perceptual_visibility"', instruction.content)
        self.assertIn('"source_accounting"', instruction.content)
        self.assertIn(PLAYER_DECOMPOSITION_OUTPUT_INSTRUCTION.strip(), instruction.content)

    def test_kernel_prepare_player_decomposition_context(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=["Ayame"])
        manifest = kernel.prepare_player_decomposition_context(
            PlayerDecompositionContextPrepareRequest(
                hg_session_id=created.hg_scene_id,
                inference_id="kernel-test",
            )
        )
        instruction = next(
            item for item in manifest.contributions if item.source_kind == "inference_instruction"
        )
        self.assertIn("Do not use presentation_only.", instruction.content)
        self.assertIn("intrinsically nonperceptual player information", instruction.content)
        self.assertIn("NOT internal", instruction.content)
        self.assertNotIn("Unexpressed cognition: internal", instruction.content)


if __name__ == "__main__":
    unittest.main()

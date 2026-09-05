"""Kernel normalize endpoint tests (#124)."""

from __future__ import annotations

import unittest

from domain_api.contract import PlayerDecompositionNormalizeRequest
from domain_api.kernel import DomainKernel


class PlayerDecompositionNormalizeKernelTests(unittest.TestCase):
    def test_kernel_normalize_accepts_simple_sir(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=["Ayame", "Kizzie"])
        result = kernel.normalize_player_decomposition(
            PlayerDecompositionNormalizeRequest(
                hg_session_id=created.hg_scene_id,
                content="Hello.",
                speaker="Player",
                semantic_decomposition={
                    "units": [
                        {
                            "kind": "speech",
                            "text": "Hello.",
                            "recipients": {"scope": "public", "characters": [], "roles": []},
                        }
                    ]
                },
            )
        )
        self.assertTrue(result["accepted"])
        self.assertIsNotNone(result["player_decomposition"])


if __name__ == "__main__":
    unittest.main()

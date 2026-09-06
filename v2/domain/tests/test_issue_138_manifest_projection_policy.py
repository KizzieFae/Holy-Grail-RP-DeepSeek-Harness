"""Issue #138 — plot-cognition inference-kind registry and envelope contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.manifest_projection_policy import (  # noqa: E402
    ALLOWED_SOURCE_KINDS,
    INFERENCE_KINDS,
    ManifestProjectionPolicyError,
    validate_model_context_contributions,
)
from domain_api.contract import PromptContribution  # noqa: E402


class Issue138PlotCognitionPolicyTests(unittest.TestCase):
    def test_plot_cognition_kinds_registered(self) -> None:
        expected = {
            "plot_cognition_init",
            "plot_cognition_init_contract_correction",
            "plot_cognition_update",
            "plot_cognition_update_contract_correction",
            "plot_cognition_epistemic_eval",
            "plot_cognition_epistemic_eval_contract_correction",
            "character_advisory_generation",
        }
        self.assertTrue(expected.issubset(set(INFERENCE_KINDS)))
        self.assertNotIn("plot_cognition_replan", INFERENCE_KINDS)

    def test_plot_cognition_init_allowlist_is_narrow(self) -> None:
        allowed = ALLOWED_SOURCE_KINDS["plot_cognition_init"]
        self.assertEqual(allowed, frozenset({"active_constraints"}))
        validate_model_context_contributions(
            "plot_cognition_init",
            [
                PromptContribution(
                    contribution_id="c-init",
                    source_kind="active_constraints",
                    authority_class="derived",
                    knowledge_ids=("plot_cognition:init_sources",),
                    priority=10,
                    content="{}",
                )
            ],
        )

    def test_plot_cognition_update_allows_advisory_context(self) -> None:
        validate_model_context_contributions(
            "plot_cognition_update",
            [
                PromptContribution(
                    contribution_id="c-update",
                    source_kind="advisory_context",
                    authority_class="advisory",
                    knowledge_ids=("plot_cognition:prior",),
                    priority=20,
                    content="{}",
                )
            ],
        )

    def test_plot_cognition_epistemic_allows_derived(self) -> None:
        validate_model_context_contributions(
            "plot_cognition_epistemic_eval",
            [
                PromptContribution(
                    contribution_id="c-derived",
                    source_kind="derived",
                    authority_class="derived",
                    knowledge_ids=("epistemic:1",),
                    priority=21,
                    content="material",
                )
            ],
        )

    def test_correction_kind_shares_primary_allowlist(self) -> None:
        self.assertEqual(
            ALLOWED_SOURCE_KINDS["plot_cognition_init_contract_correction"],
            ALLOWED_SOURCE_KINDS["plot_cognition_init"],
        )
        self.assertEqual(
            ALLOWED_SOURCE_KINDS["plot_cognition_update_contract_correction"],
            ALLOWED_SOURCE_KINDS["plot_cognition_update"],
        )

    def test_unknown_plot_cognition_kind_still_rejected(self) -> None:
        with self.assertRaises(ManifestProjectionPolicyError):
            validate_model_context_contributions(
                "plot_cognition_replan",
                [
                    PromptContribution(
                        contribution_id="c",
                        source_kind="active_constraints",
                        authority_class="derived",
                        knowledge_ids=("x",),
                        priority=1,
                        content="{}",
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()

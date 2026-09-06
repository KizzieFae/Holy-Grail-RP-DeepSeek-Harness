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
        self.assertEqual(
            ALLOWED_SOURCE_KINDS["librarian_proposal_contract_correction"],
            ALLOWED_SOURCE_KINDS["librarian_proposal"],
        )

    def test_librarian_proposal_correction_accepts_host_shaped_contributions(self) -> None:
        contributions = [
            PromptContribution(
                contribution_id="manifest-req",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=("librarian_proposal_request:req-1",),
                priority=10,
                content="request",
            ),
            PromptContribution(
                contribution_id="manifest-epistemic",
                source_kind="active_constraints",
                authority_class="authoritative",
                knowledge_ids=("librarian_proposal_epistemic:req-1",),
                priority=10,
                content="epistemic",
            ),
            PromptContribution(
                contribution_id="manifest-catalog",
                source_kind="librarian_knowledge",
                authority_class="derived",
                knowledge_ids=("committed_move:commit-1",),
                priority=12,
                content="catalog",
            ),
        ]
        validate_model_context_contributions(
            "librarian_proposal_contract_correction",
            contributions,
        )
        with self.assertRaises(ManifestProjectionPolicyError):
            validate_model_context_contributions(
                "librarian_proposal_contract_correction",
                [
                    PromptContribution(
                        contribution_id="bad",
                        source_kind="semantic_correction",
                        authority_class="derived",
                        knowledge_ids=("x",),
                        priority=1,
                        content="{}",
                    )
                ],
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

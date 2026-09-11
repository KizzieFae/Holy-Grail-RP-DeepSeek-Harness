"""Tests for S2a mediation inference contract projection (#169)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_contract import (  # noqa: E402
    BudgetExpectations,
    InformationNeed,
    KnowledgeAccessRequest,
    MediationCatalogItem,
    VisibilityEnvelope,
)
from domain_api.librarian_mediation_context import build_mediation_manifest_contributions  # noqa: E402
from domain_api.librarian_mediation_inference_contract import (  # noqa: E402
    load_librarian_mediation_inference_contract,
    render_mediation_inference_contract_lines,
)


def _base_request() -> KnowledgeAccessRequest:
    return KnowledgeAccessRequest(
        request_id="req-contract-1",
        consumer_role="storyteller",
        audit_reason="unit_test",
        hg_scene_id="scene-1",
        hg_round_id="round-1",
        turn_index=0,
        pipeline_stage="host_default",
        visibility_envelope=VisibilityEnvelope(
            viewer_role="orchestration",
            authority_ceiling_enforced="derived",
            session_template_id="template-1",
        ),
        information_need=InformationNeed(
            focus_questions=("Who is present?",),
            recall_breadth_preference="focused",
        ),
        host_allowed_information_classes=frozenset({"authored_static"}),
        budget_expectations=BudgetExpectations(max_bundle_entries=8, max_bundle_chars=8000),
    )


class LibrarianMediationInferenceContractTests(unittest.TestCase):
    def test_contract_json_requires_relevance_rank(self) -> None:
        contract = load_librarian_mediation_inference_contract()
        item_fields = contract["field_specs"]["selected_items"]["item_fields"]
        self.assertTrue(item_fields["relevance_rank"]["required"])
        self.assertIn(
            "selected_items[].rank",
            [alias["path"] for alias in contract["forbidden_field_aliases"]],
        )

    def test_host_manifest_contract_contribution_includes_relevance_rank(self) -> None:
        request = _base_request()
        catalog = (
            MediationCatalogItem(
                source_id="lmi:cand:example",
                source_kind="retrieval_candidate",
                stable_ref="example",
                content="fixture",
                information_class="authored_static",
                authority_class="suggestive",
                visibility_scope="template_participants",
                source_tier="retrieval_candidate",
                provenance={},
            ),
        )
        contributions = build_mediation_manifest_contributions(
            request,
            manifest_id="manifest-test",
            inference_id="inf-test",
            catalog=catalog,
            authoritative_snapshot_id="snap-1",
        )
        contract = next(c for c in contributions if c.contribution_id.endswith("-contract"))
        rendered = render_mediation_inference_contract_lines(sample_source_id="lmi:cand:example")
        self.assertIn("relevance_rank", contract.content)
        self.assertIn("synthesis_entries", contract.content)
        self.assertEqual(contract.content, rendered)


if __name__ == "__main__":
    unittest.main()

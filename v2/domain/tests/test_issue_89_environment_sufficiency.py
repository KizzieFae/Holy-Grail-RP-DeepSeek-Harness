"""Issue #89 — environmental response sufficiency and presentation obligations."""

from __future__ import annotations

import shutil
import tempfile
import unittest

from domain_api.narrator_environment_authority import (
    evaluate_host_environmental_b2_establishment,
    mediation_allows_bounded_composition,
    mediation_blocks_invention,
    NarratorEnvironmentalB2Proposal,
)
from domain_api.narrator_environment_cognition import (
    finalize_narrator_environment_cognition,
    parse_n2_cognition_results,
)
from domain_api.narrator_environment_location_binding import bind_location_stable_ref
from domain_api.narrator_environment_sufficiency import (
    extract_composed_grounding_from_librarian,
    reconcile_post_mediation_environmental_resolutions,
)
from domain_api.narrator_environment_projection import build_environmental_current_view
from domain_api.narrator_environment_cognition import parse_n1_cognition_result
from domain_api.story_knowledge_repository import StoryKnowledgeRepository
from domain_api.story_knowledge_service import StoryKnowledgeService
from domain_api.session_state import CharacterTurnRecord, initialize_live_session


class SufficiencyReconciliationTests(unittest.TestCase):
    def test_match_plus_sufficient_promotes_category_a(self) -> None:
        n1 = parse_n1_cognition_result(
            {
                "baseline_sufficient": False,
                "information_needs": [
                    {"need_id": "need-1", "question": "Is the parcel small?"}
                ],
                "resolutions": [
                    {
                        "need_id": "need-1",
                        "category": "cannot_safely_resolve",
                        "response_sufficient": True,
                        "detail": "small parcel",
                    }
                ],
            }
        )
        resolutions = parse_n2_cognition_results(
            {
                "resolutions": [
                    {
                        "need_id": "need-1",
                        "category": "cannot_safely_resolve",
                        "response_sufficient": True,
                        "detail": "small parcel",
                    }
                ]
            }
        )
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        view = build_environmental_current_view(fixture, story_records=[])
        reconciled, evaluations, obligations = reconcile_post_mediation_environmental_resolutions(
            n1=n1,
            resolutions=resolutions,
            librarian_outcomes=[
                {
                    "need_id": "need-1",
                    "mediation_outcome": "match",
                    "composed_grounding": "small, heavy parcel wrapped in brown paper",
                }
            ],
            n2_raw_items=[
                {
                    "need_id": "need-1",
                    "category": "cannot_safely_resolve",
                    "response_sufficient": True,
                }
            ],
            current_view=view,
        )
        self.assertEqual(reconciled[0].category, "A")
        self.assertEqual(reconciled[0].mediation_outcome, "match")
        self.assertTrue(evaluations[0].response_sufficient)
        self.assertEqual(obligations[0].render_behavior, "communicate_grounded")

    def test_match_plus_insufficient_allows_b2_path(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.memory_scope_id = "scope-89b"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            turn = CharacterTurnRecord(
                character_id="Alice",
                committed_move={"move_schema_version": 2, "beats": []},
                domain_commit_id="commit-89b",
                continuity_turn_index=1,
                director_decision={},
            )
            loc = bind_location_stable_ref("Workshop").stable_ref
            result = finalize_narrator_environment_cognition(
                fixture,
                turn,
                story_service=service,
                n1_raw={
                    "baseline_sufficient": False,
                    "information_needs": [
                        {"need_id": "need-1", "question": "How big is the parcel?"}
                    ],
                },
                n2_raw={
                    "resolutions": [
                        {
                            "need_id": "need-1",
                            "category": "B2",
                            "response_sufficient": False,
                            "detail": "small and heavy but dimensions needed",
                            "property_key": "parcel_size",
                            "value": "roughly forearm-length",
                            "stable_refs": [loc],
                        }
                    ]
                },
                librarian_outcomes=[
                    {
                        "need_id": "need-1",
                        "mediation_outcome": "match",
                        "composed_grounding": "small, heavy parcel wrapped in brown paper",
                    }
                ],
            )
            self.assertTrue(result["establishment_decisions"][0]["accepted"])
            obligations = result["audit"]["environmental_response_obligations"]
            self.assertEqual(obligations[0]["render_behavior"], "communicate_grounded")
            self.assertEqual(result["audit"]["n2_resolutions"][0]["mediation_outcome"], "match")
            self.assertEqual(len(service.list_records("scope-89b")), 1)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_retrieval_failure_blocks_b2(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.memory_scope_id = "scope-89g"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            turn = CharacterTurnRecord(
                character_id="Alice",
                committed_move={"move_schema_version": 2, "beats": []},
                domain_commit_id="commit-89g",
                continuity_turn_index=1,
                director_decision={},
            )
            result = finalize_narrator_environment_cognition(
                fixture,
                turn,
                story_service=service,
                n1_raw={
                    "baseline_sufficient": False,
                    "information_needs": [
                        {"need_id": "need-1", "question": "What is on the table?"}
                    ],
                },
                n2_raw={
                    "resolutions": [
                        {
                            "need_id": "need-1",
                            "category": "B2",
                            "response_sufficient": False,
                            "property_key": "table_contents",
                            "value": "a ledger",
                        }
                    ]
                },
                librarian_outcomes=[
                    {"need_id": "need-1", "mediation_outcome": "retrieval_failure"}
                ],
            )
            self.assertEqual(service.list_records("scope-89g"), [])
            self.assertFalse(
                any(item.get("accepted") for item in result["establishment_decisions"])
            )
            obligations = result["audit"]["environmental_response_obligations"]
            self.assertTrue(obligations)
            obligation = obligations[0]
            self.assertEqual(obligation["render_behavior"], "bounded_refusal")
            self.assertEqual(obligation["sufficiency_state"], "failure")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_baseline_sufficient_emits_no_material_obligation(self) -> None:
        n1 = parse_n1_cognition_result(
            {"baseline_sufficient": True, "information_needs": [], "resolutions": []}
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

    def test_extract_composed_grounding_from_librarian(self) -> None:
        text = extract_composed_grounding_from_librarian(
            {
                "composed_grounding": "small parcel",
                "entries": [{"content": "wrapped in brown paper"}],
            }
        )
        self.assertIn("small parcel", text)
        self.assertIn("brown paper", text)


class B2EligibilityTests(unittest.TestCase):
    def test_match_and_no_match_allow_bounded_composition(self) -> None:
        self.assertTrue(mediation_allows_bounded_composition("match"))
        self.assertTrue(mediation_allows_bounded_composition("no_match"))
        self.assertFalse(mediation_allows_bounded_composition("retrieval_failure"))

    def test_match_may_pass_host_b2_validation(self) -> None:
        loc = bind_location_stable_ref("Workshop").stable_ref
        proposal = NarratorEnvironmentalB2Proposal(
            cognition_id="cog-89",
            need_id="need-1",
            property_key="house_number",
            value="14",
            stable_refs=(loc,),
            mediation_outcome="match",
        )
        decision = evaluate_host_environmental_b2_establishment(proposal)
        self.assertTrue(decision.authorized)
        self.assertEqual(decision.reason_code, "host_accepted")

    def test_retrieval_failure_blocked_by_mediation(self) -> None:
        loc = bind_location_stable_ref("Workshop").stable_ref
        proposal = NarratorEnvironmentalB2Proposal(
            cognition_id="cog-89",
            need_id="need-1",
            property_key="house_number",
            value="14",
            stable_refs=(loc,),
            mediation_outcome="retrieval_failure",
        )
        decision = evaluate_host_environmental_b2_establishment(proposal)
        self.assertFalse(decision.authorized)
        self.assertTrue(mediation_blocks_invention("retrieval_failure"))


if __name__ == "__main__":
    unittest.main()

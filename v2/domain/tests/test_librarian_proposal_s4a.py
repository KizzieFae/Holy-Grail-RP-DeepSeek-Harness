"""#34 S4a Librarian grounded semantic-proposal boundary tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_contract import VisibilityEnvelope  # noqa: E402
from domain_api.librarian_proposal_contract import (  # noqa: E402
    LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    LibrarianProposalContextRequest,
    ProposalCommitBinding,
    ProposalEvidenceCatalogItem,
    ProposalProvenance,
    new_proposal_id,
    new_proposal_request_id,
    validate_proposal_payload_schema,
)
from domain_api.librarian_proposal_service import (  # noqa: E402
    LibrarianProposalService,
    build_post_commit_proposal_request,
)
from domain_api.librarian_proposal_validate import (  # noqa: E402
    parse_librarian_proposal_result,
    validate_host_proposal_batch,
    validate_host_proposal_item,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from continuity_librarian_proposals import (  # noqa: E402
    build_evidence_closure,
    evaluate_librarian_proposal_batch,
    evaluate_librarian_proposal_continuity,
)
from domain_api.librarian_proposal_contract import (  # noqa: E402
    EvidenceAnchor,
    LibrarianSemanticProposal,
)
from continuity_semantic_proposals import (  # noqa: E402
    ProposalAuthorityOutcome,
    evaluate_proposal_legality,
)


def _minimal_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "opens the door"}],
        "motivation": {
            "goal": "enter",
            "tactic": "open door",
            "emotional_driver": "curious",
            "risk_level": "low",
        },
    }


def _session_with_commit(*, commit_id: str = "commit-1") -> tuple:
    fixture = initialize_live_session(
        cast=["Alice"],
        hg_session_id="session-1",
    )
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="opens the door",
        hg_round_id="round-1",
        domain_commit_id=commit_id,
        actor_id="Alice",
        metadata={
            "continuity_turn_index": 1,
            "structured_move": _minimal_move(),
        },
    )
    request = build_post_commit_proposal_request(
        hg_scene_id="scene-1",
        hg_round_id="round-1",
        turn_index=1,
        domain_commit_id=commit_id,
        librarian_inference_id="inf-librarian-1",
    )
    return fixture, request


def _catalog(commit_id: str) -> tuple[ProposalEvidenceCatalogItem, ...]:
    return (
        ProposalEvidenceCatalogItem(
            anchor_id=f"committed_move:{commit_id}",
            evidence_kind="committed_move",
            stable_ref=f"commit:{commit_id}",
            authority_class="authoritative",
            visibility_scope="public",
            content="{}",
            anchor_commit_id=commit_id,
        ),
        ProposalEvidenceCatalogItem(
            anchor_id=f"scene_state:{commit_id}",
            evidence_kind="scene_state",
            stable_ref=f"scene_state:{commit_id}",
            authority_class="authoritative",
            visibility_scope="scene_orchestration",
            content="{}",
            anchor_commit_id=commit_id,
        ),
    )


def _valid_proposal_result(commit_id: str) -> dict:
    return {
        "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
        "proposals": [
            {
                "proposal_id": "prop-1",
                "proposal_kind": "information_salience",
                "derivation_summary": "Committed move advances the scene objective.",
                "confidence": "likely",
                "evidence_anchors": [
                    {
                        "anchor_id": f"committed_move:{commit_id}",
                        "evidence_kind": "committed_move",
                        "anchor_commit_id": commit_id,
                    }
                ],
                "proposed_payload": {
                    "subject_ref": f"commit:{commit_id}",
                    "salience_level": "major",
                },
            }
        ],
    }


class LibrarianProposalS4aTests(unittest.TestCase):
    def test_valid_grounded_proposal_accepted(self) -> None:
        fixture, request = _session_with_commit()
        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_valid_proposal_result("commit-1"),
            evidence_catalog=_catalog("commit-1"),
        )
        self.assertTrue(result.host_validation.accepted)
        self.assertIsNotNone(result.continuity_decision)
        assert result.continuity_decision is not None
        self.assertEqual(result.continuity_decision.accepted_count, 1)
        self.assertFalse(result.audit.host_validation.rejection_codes)
        self.assertEqual(len(fixture.librarian_proposal_audit_log), 1)
        self.assertFalse(fixture.librarian_proposal_audit_log[0]["librarian_proposal_durable_mutation_applied"])

    def test_missing_evidence_anchors_rejected(self) -> None:
        commit_id = "commit-1"
        parsed, _err = parse_librarian_proposal_result(
            {
                "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
                "proposals": [
                    {
                        "proposal_kind": "information_salience",
                        "derivation_summary": "no anchors",
                        "confidence": "likely",
                        "evidence_anchors": [],
                        "proposed_payload": {
                            "subject_ref": "x",
                            "salience_level": "minor",
                        },
                    }
                ],
            },
            batch_id="batch-1",
            commit_binding=ProposalCommitBinding(
                domain_commit_id=commit_id,
                hg_round_id="round-1",
                turn_index=1,
            ),
            librarian_inference_id="inf-1",
        )
        assert parsed is not None
        item = validate_host_proposal_item(
            parsed[0],
            catalog=_catalog(commit_id),
            domain_commit_id=commit_id,
        )
        self.assertFalse(item.accepted)
        self.assertIn("missing_evidence_anchors", item.rejection_codes)

    def test_unknown_anchor_rejected(self) -> None:
        commit_id = "commit-1"
        proposal = LibrarianSemanticProposal(
            proposal_id="p1",
            proposal_batch_id="b1",
            proposal_origin="librarian",
            proposal_kind="information_salience",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id="unknown:anchor",
                    evidence_kind="committed_move",
                    anchor_commit_id=commit_id,
                ),
            ),
            derivation_summary="bad anchor",
            confidence="likely",
            proposed_payload={"subject_ref": "x", "salience_level": "minor"},
            commit_binding=ProposalCommitBinding(
                domain_commit_id=commit_id,
                hg_round_id="round-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-1"),
        )
        item = validate_host_proposal_item(
            proposal,
            catalog=_catalog(commit_id),
            domain_commit_id=commit_id,
        )
        self.assertIn("unknown_evidence_anchor", item.rejection_codes)

    def test_authority_elevation_rejected(self) -> None:
        commit_id = "commit-1"
        proposal = LibrarianSemanticProposal(
            proposal_id="p1",
            proposal_batch_id="b1",
            proposal_origin="librarian",
            proposal_kind="information_salience",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id=f"committed_move:{commit_id}",
                    evidence_kind="committed_move",
                    anchor_commit_id=commit_id,
                ),
            ),
            derivation_summary="elevated",
            confidence="confirmed",
            proposed_payload={
                "subject_ref": "x",
                "salience_level": "minor",
                "authority_class": "authoritative",
            },
            commit_binding=ProposalCommitBinding(
                domain_commit_id=commit_id,
                hg_round_id="round-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-1"),
        )
        item = validate_host_proposal_item(
            proposal,
            catalog=_catalog(commit_id),
            domain_commit_id=commit_id,
        )
        self.assertIn("authority_elevation_attempt", item.rejection_codes)

    def test_preservation_signal_not_evidence(self) -> None:
        commit_id = "commit-1"
        proposal = LibrarianSemanticProposal(
            proposal_id="p1",
            proposal_batch_id="b1",
            proposal_origin="librarian",
            proposal_kind="information_salience",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id="preservation_signal:hint-1",
                    evidence_kind="preservation_signal",
                ),
            ),
            derivation_summary="storyteller hint",
            confidence="likely",
            proposed_payload={"subject_ref": "x", "salience_level": "minor"},
            commit_binding=ProposalCommitBinding(
                domain_commit_id=commit_id,
                hg_round_id="round-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-1"),
        )
        item = validate_host_proposal_item(
            proposal,
            catalog=_catalog(commit_id),
            domain_commit_id=commit_id,
        )
        self.assertIn("preservation_signal_not_evidence", item.rejection_codes)

    def test_manufactured_fact_rejected(self) -> None:
        ok, _reason, codes = validate_proposal_payload_schema(
            "information_salience",
            {"subject_ref": "x", "salience_level": "minor", "manufactured_fact": True},
        )
        self.assertFalse(ok)

    def test_malformed_result_rejected(self) -> None:
        fixture, request = _session_with_commit()
        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result={"schema": "wrong_schema", "proposals": []},
        )
        self.assertEqual(result.degradation_mode, "malformed_result")
        self.assertFalse(result.host_validation.accepted)

    def test_inference_failure_baseline_continues(self) -> None:
        fixture, request = _session_with_commit()
        service = LibrarianProposalService()
        result = service.finalize_proposals(request, fixture, proposal_result=None)
        self.assertEqual(result.degradation_mode, "inference_failed")
        self.assertEqual(result.proposals, ())

    def test_acceptance_does_not_apply_durable_mutation(self) -> None:
        fixture, request = _session_with_commit()
        service = LibrarianProposalService()
        before_version = fixture.continuity_version
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_valid_proposal_result("commit-1"),
            evidence_catalog=_catalog("commit-1"),
        )
        self.assertEqual(fixture.continuity_version, before_version)
        assert result.continuity_decision is not None
        for item in result.continuity_decision.item_decisions:
            self.assertFalse(item.durable_mutation_applied)

    def test_issue232_character_proposals_remain_compatible(self) -> None:
        ctx = evaluate_proposal_legality(
            _minimal_move(),
            acting_character="Alice",
            scene_state={"present_characters": ["Alice", "Bob"]},
        )
        self.assertEqual(ctx.outcome, ProposalAuthorityOutcome.NO_PROPOSAL)

    def test_prepare_context_builds_catalog(self) -> None:
        fixture, request = _session_with_commit()
        service = LibrarianProposalService()
        prepared = service.prepare_proposal_context(request, fixture)
        self.assertTrue(prepared.evidence_catalog)
        self.assertEqual(prepared.domain_commit_id, "commit-1")
        self.assertTrue(prepared.contributions)


if __name__ == "__main__":
    unittest.main()

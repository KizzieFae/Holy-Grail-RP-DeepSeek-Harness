"""#34 S4b knowledge_revelation_significance production mutation tests."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_state import PublicEvent  # noqa: E402
from domain_api.librarian_proposal_contract import (  # noqa: E402
    LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    ProposalCommitBinding,
    ProposalProvenance,
    validate_proposal_payload_schema,
)
from domain_api.librarian_proposal_service import (  # noqa: E402
    LibrarianProposalService,
    build_post_commit_proposal_request,
)
from domain_api.librarian_proposal_context import build_post_commit_evidence_catalog  # noqa: E402
from domain_api.librarian_proposal_validate import validate_host_proposal_item  # noqa: E402
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from domain_api.librarian_proposal_contract import (  # noqa: E402
    EvidenceAnchor,
    LibrarianSemanticProposal,
)
from continuity_librarian_knowledge_significance import (  # noqa: E402
    REASON_EQUAL_RANK_UNCHANGED,
    apply_knowledge_revelation_significance,
)
from continuity_librarian_proposals import (  # noqa: E402
    build_evidence_closure,
    evaluate_librarian_proposal_continuity,
)


def _minimal_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "dialogue", "dialogue": "The crown is hidden in the vault."}],
        "motivation": {
            "goal": "reveal",
            "tactic": "confide",
            "emotional_driver": "trust",
            "risk_level": "medium",
        },
    }


def _session_with_event(
    *,
    commit_id: str = "commit-s4b-1",
    event_id: str = "evt-revelation-1",
    known_by: list[str] | None = None,
) -> tuple:
    fixture = initialize_live_session(
        cast=["Alice", "Bob"],
        hg_session_id="session-s4b",
    )
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="reveals secret",
        hg_round_id="round-s4b-1",
        domain_commit_id=commit_id,
        actor_id="Alice",
        metadata={
            "continuity_turn_index": 1,
            "structured_move": _minimal_move(),
        },
    )
    event = PublicEvent(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        event_type="revelation",
        participants=["Alice"],
        summary="Alice reveals the crown is hidden in the vault.",
        turn_index=1,
        significance="minor",
        observed_by=list(known_by or ["Alice"]),
        known_by=list(known_by or ["Alice"]),
    )
    fixture.manager.public_events.append(event)
    request = build_post_commit_proposal_request(
        hg_scene_id="scene-s4b",
        hg_round_id="round-s4b-1",
        turn_index=1,
        domain_commit_id=commit_id,
        librarian_inference_id="inf-librarian-s4b",
    )
    return fixture, request, event


def _s4b_proposal_result(
    *,
    commit_id: str,
    event_id: str,
    proposal_id: str = "prop-s4b-1",
    subject_character: str = "Alice",
    level: str = "major",
    note: str = "Late-emerging plot significance.",
    grant_knowledge: bool = False,
) -> dict:
    payload = {
        "event_ref": event_id,
        "subject_character": subject_character,
        "revelation_significance_level": level,
        "interpretation_scope": "utterance_occurrence",
        "annotation_note": note,
    }
    if grant_knowledge:
        payload["grant_knowledge"] = True
    return {
        "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
        "proposals": [
            {
                "proposal_id": proposal_id,
                "proposal_kind": "knowledge_revelation_significance",
                "derivation_summary": "The revelation materially advances the hidden-crown thread.",
                "confidence": "likely",
                "evidence_anchors": [
                    {
                        "anchor_id": f"committed_move:{commit_id}",
                        "evidence_kind": "committed_move",
                        "anchor_commit_id": commit_id,
                    },
                    {
                        "anchor_id": f"public_event:{event_id}",
                        "evidence_kind": "public_event",
                        "anchor_commit_id": commit_id,
                    },
                ],
                "proposed_payload": payload,
            }
        ],
    }


def _apply_pair(
    fixture,
    event,
    *,
    first_subject: str,
    first_level: str,
    second_subject: str,
    second_level: str,
) -> tuple:
    first = apply_knowledge_revelation_significance(
        fixture.manager,
        LibrarianSemanticProposal(
            proposal_id=f"prop-{first_subject}-{first_level}",
            proposal_batch_id="batch-1",
            proposal_origin="librarian",
            proposal_kind="knowledge_revelation_significance",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id=f"public_event:{event.event_id}",
                    evidence_kind="public_event",
                ),
            ),
            derivation_summary="significance",
            confidence="likely",
            proposed_payload={
                "event_ref": event.event_id,
                "subject_character": first_subject,
                "revelation_significance_level": first_level,
                "interpretation_scope": "utterance_occurrence",
            },
            commit_binding=ProposalCommitBinding(
                domain_commit_id="commit-s4b-1",
                hg_round_id="round-s4b-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-1"),
        ),
    )
    second = apply_knowledge_revelation_significance(
        fixture.manager,
        LibrarianSemanticProposal(
            proposal_id=f"prop-{second_subject}-{second_level}",
            proposal_batch_id="batch-2",
            proposal_origin="librarian",
            proposal_kind="knowledge_revelation_significance",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id=f"public_event:{event.event_id}",
                    evidence_kind="public_event",
                ),
            ),
            derivation_summary="significance",
            confidence="likely",
            proposed_payload={
                "event_ref": event.event_id,
                "subject_character": second_subject,
                "revelation_significance_level": second_level,
                "interpretation_scope": "utterance_occurrence",
            },
            commit_binding=ProposalCommitBinding(
                domain_commit_id="commit-s4b-1",
                hg_round_id="round-s4b-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-2"),
        ),
    )
    return first, second


class LibrarianProposalS4bTests(unittest.TestCase):
    def test_schema_requires_subject_character(self) -> None:
        ok, _reason, _codes = validate_proposal_payload_schema(
            "knowledge_revelation_significance",
            {
                "event_ref": "evt-revelation-1",
                "revelation_significance_level": "major",
            },
        )
        self.assertFalse(ok)

    def test_schema_accepts_bounded_payload(self) -> None:
        ok, _reason, _codes = validate_proposal_payload_schema(
            "knowledge_revelation_significance",
            {
                "event_ref": "evt-revelation-1",
                "subject_character": "Alice",
                "revelation_significance_level": "major",
                "interpretation_scope": "utterance_occurrence",
            },
        )
        self.assertTrue(ok)

    def test_grounded_happy_path_applies_annotation(self) -> None:
        fixture, request, event = _session_with_event()
        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_proposal_result(
                commit_id="commit-s4b-1",
                event_id=event.event_id,
            ),
        )
        self.assertTrue(result.host_validation.accepted)
        assert result.continuity_decision is not None
        self.assertEqual(result.continuity_decision.accepted_count, 1)
        decision = result.continuity_decision.item_decisions[0]
        self.assertTrue(decision.durable_mutation_applied)
        annotations = event.revelation_significance_by_character
        assert isinstance(annotations, dict)
        self.assertEqual(annotations["Alice"]["revelation_significance_level"], "major")
        self.assertEqual(event.significance, "minor")
        self.assertTrue(
            fixture.librarian_proposal_audit_log[-1]["librarian_proposal_durable_mutation_applied"]
        )

    def test_multi_knower_independent_significance(self) -> None:
        fixture, _request, event = _session_with_event(known_by=["Alice", "Bob"])
        first, second = _apply_pair(
            fixture,
            event,
            first_subject="Alice",
            first_level="pivotal",
            second_subject="Bob",
            second_level="minor",
        )
        self.assertTrue(first.applied)
        self.assertTrue(second.applied)
        annotations = event.revelation_significance_by_character
        assert isinstance(annotations, dict)
        self.assertEqual(annotations["Alice"]["revelation_significance_level"], "pivotal")
        self.assertEqual(annotations["Bob"]["revelation_significance_level"], "minor")

    def test_multi_knower_order_independent(self) -> None:
        fixture, _request, event = _session_with_event(known_by=["Alice", "Bob"])
        first, second = _apply_pair(
            fixture,
            event,
            first_subject="Bob",
            first_level="minor",
            second_subject="Alice",
            second_level="pivotal",
        )
        self.assertTrue(first.applied)
        self.assertTrue(second.applied)
        annotations = event.revelation_significance_by_character
        assert isinstance(annotations, dict)
        self.assertEqual(annotations["Bob"]["revelation_significance_level"], "minor")
        self.assertEqual(annotations["Alice"]["revelation_significance_level"], "pivotal")

    def test_character_not_in_known_by_rejected(self) -> None:
        fixture, request, event = _session_with_event(known_by=["Alice"])
        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_proposal_result(
                commit_id="commit-s4b-1",
                event_id=event.event_id,
                subject_character="Bob",
            ),
        )
        assert result.continuity_decision is not None
        self.assertEqual(result.continuity_decision.accepted_count, 0)
        self.assertIsNone(event.revelation_significance_by_character)

    def test_unknown_event_reference_rejected(self) -> None:
        fixture, request, event = _session_with_event()
        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_proposal_result(
                commit_id="commit-s4b-1",
                event_id="evt-does-not-exist",
            ),
        )
        assert result.continuity_decision is not None
        self.assertEqual(result.continuity_decision.accepted_count, 0)
        self.assertIsNone(event.revelation_significance_by_character)

    def test_grant_knowledge_payload_rejected(self) -> None:
        ok, _reason, codes = validate_proposal_payload_schema(
            "knowledge_revelation_significance",
            {
                "event_ref": "evt-1",
                "subject_character": "Alice",
                "revelation_significance_level": "major",
                "interpretation_scope": "utterance_occurrence",
                "grant_knowledge": True,
            },
        )
        self.assertFalse(ok)
        self.assertIn("authority_elevation_attempt", codes)

    def test_idempotent_replay(self) -> None:
        fixture, request, event = _session_with_event()
        service = LibrarianProposalService()
        proposal = _s4b_proposal_result(
            commit_id="commit-s4b-1",
            event_id=event.event_id,
            proposal_id="prop-idem-1",
        )
        first = service.finalize_proposals(request, fixture, proposal_result=proposal)
        second = service.finalize_proposals(request, fixture, proposal_result=proposal)
        assert first.continuity_decision is not None
        assert second.continuity_decision is not None
        self.assertTrue(first.continuity_decision.item_decisions[0].durable_mutation_applied)
        self.assertFalse(second.continuity_decision.item_decisions[0].durable_mutation_applied)
        self.assertEqual(
            first.continuity_decision.item_decisions[0].outcome,
            second.continuity_decision.item_decisions[0].outcome,
        )

    def test_same_subject_lower_rank_rejected(self) -> None:
        fixture, request, event = _session_with_event()
        service = LibrarianProposalService()
        high = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_proposal_result(
                commit_id="commit-s4b-1",
                event_id=event.event_id,
                proposal_id="prop-high",
                level="pivotal",
            ),
        )
        self.assertEqual(high.continuity_decision.accepted_count, 1)
        low = service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_proposal_result(
                commit_id="commit-s4b-1",
                event_id=event.event_id,
                proposal_id="prop-low",
                level="minor",
            ),
        )
        assert low.continuity_decision is not None
        self.assertEqual(low.continuity_decision.accepted_count, 0)
        annotations = event.revelation_significance_by_character
        assert isinstance(annotations, dict)
        self.assertEqual(annotations["Alice"]["revelation_significance_level"], "pivotal")

    def test_equal_rank_does_not_churn_note(self) -> None:
        fixture, _request, event = _session_with_event()
        first = apply_knowledge_revelation_significance(
            fixture.manager,
            LibrarianSemanticProposal(
                proposal_id="prop-major-1",
                proposal_batch_id="batch-1",
                proposal_origin="librarian",
                proposal_kind="knowledge_revelation_significance",
                evidence_anchors=(
                    EvidenceAnchor(
                        anchor_id=f"public_event:{event.event_id}",
                        evidence_kind="public_event",
                    ),
                ),
                derivation_summary="first",
                confidence="likely",
                proposed_payload={
                    "event_ref": event.event_id,
                    "subject_character": "Alice",
                    "revelation_significance_level": "major",
                    "interpretation_scope": "utterance_occurrence",
                    "annotation_note": "original note",
                },
                commit_binding=ProposalCommitBinding(
                    domain_commit_id="commit-s4b-1",
                    hg_round_id="round-s4b-1",
                    turn_index=1,
                ),
                provenance=ProposalProvenance(librarian_inference_id="inf-1"),
            ),
        )
        second = apply_knowledge_revelation_significance(
            fixture.manager,
            LibrarianSemanticProposal(
                proposal_id="prop-major-2",
                proposal_batch_id="batch-2",
                proposal_origin="librarian",
                proposal_kind="knowledge_revelation_significance",
                evidence_anchors=(
                    EvidenceAnchor(
                        anchor_id=f"public_event:{event.event_id}",
                        evidence_kind="public_event",
                    ),
                ),
                derivation_summary="second",
                confidence="likely",
                proposed_payload={
                    "event_ref": event.event_id,
                    "subject_character": "Alice",
                    "revelation_significance_level": "major",
                    "interpretation_scope": "utterance_occurrence",
                    "annotation_note": "different note should not apply",
                },
                commit_binding=ProposalCommitBinding(
                    domain_commit_id="commit-s4b-1",
                    hg_round_id="round-s4b-1",
                    turn_index=1,
                ),
                provenance=ProposalProvenance(librarian_inference_id="inf-2"),
            ),
        )
        self.assertTrue(first.applied)
        self.assertTrue(second.applied)
        self.assertEqual(second.reason_code, REASON_EQUAL_RANK_UNCHANGED)
        annotations = event.revelation_significance_by_character
        assert isinstance(annotations, dict)
        self.assertEqual(annotations["Alice"]["annotation_note"], "original note")

    def test_inference_failure_leaves_baseline(self) -> None:
        fixture, request, event = _session_with_event()
        service = LibrarianProposalService()
        result = service.finalize_proposals(request, fixture, proposal_result=None)
        self.assertEqual(result.degradation_mode, "inference_failed")
        self.assertIsNone(event.revelation_significance_by_character)

    def test_catalog_includes_public_event(self) -> None:
        fixture, request, event = _session_with_event()
        catalog, _commit = build_post_commit_evidence_catalog(request, fixture)
        public_items = [item for item in catalog if item.evidence_kind == "public_event"]
        self.assertEqual(len(public_items), 1)
        payload = json.loads(public_items[0].content)
        self.assertEqual(payload["event_id"], event.event_id)
        self.assertEqual(payload["known_by"], ["Alice"])

    def test_scenario_learned_revelation_exposes_annotation(self) -> None:
        fixture, request, event = _session_with_event(known_by=["Alice"])
        service = LibrarianProposalService()
        service.finalize_proposals(
            request,
            fixture,
            proposal_result=_s4b_proposal_result(
                commit_id="commit-s4b-1",
                event_id=event.event_id,
            ),
        )
        stored = fixture.manager.public_events[0].to_dict()
        self.assertIn("Alice", stored["known_by"])
        self.assertIsNotNone(stored["revelation_significance_by_character"])
        self.assertEqual(stored["significance"], "minor")

    def test_to_dict_preserves_multi_knower_annotations(self) -> None:
        fixture, _request, event = _session_with_event(known_by=["Alice", "Bob"])
        _apply_pair(
            fixture,
            event,
            first_subject="Alice",
            first_level="pivotal",
            second_subject="Bob",
            second_level="minor",
        )
        restored = PublicEvent.from_dict(event.to_dict())
        assert restored.revelation_significance_by_character is not None
        self.assertEqual(
            restored.revelation_significance_by_character["Alice"]["revelation_significance_level"],
            "pivotal",
        )
        self.assertEqual(
            restored.revelation_significance_by_character["Bob"]["revelation_significance_level"],
            "minor",
        )

    def test_scenario_not_learned_cannot_grant_knowledge(self) -> None:
        fixture, request, event = _session_with_event(known_by=["Alice"])
        event.known_by = ["Alice"]
        proposal = LibrarianSemanticProposal(
            proposal_id="prop-bob",
            proposal_batch_id="batch-1",
            proposal_origin="librarian",
            proposal_kind="knowledge_revelation_significance",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id=f"public_event:{event.event_id}",
                    evidence_kind="public_event",
                ),
            ),
            derivation_summary="attempt grant via significance",
            confidence="likely",
            proposed_payload={
                "event_ref": event.event_id,
                "subject_character": "Bob",
                "revelation_significance_level": "pivotal",
                "interpretation_scope": "utterance_occurrence",
            },
            commit_binding=ProposalCommitBinding(
                domain_commit_id="commit-s4b-1",
                hg_round_id="round-s4b-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-1"),
        )
        result = apply_knowledge_revelation_significance(fixture.manager, proposal)
        self.assertFalse(result.applied)
        self.assertEqual(result.reason_code, "subject_not_in_known_by")
        self.assertNotIn("Bob", event.known_by)

    def test_s4a_non_mutating_kinds_remain_non_mutating(self) -> None:
        fixture, request, _event = _session_with_event()
        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result={
                "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
                "proposals": [
                    {
                        "proposal_id": "prop-s4a",
                        "proposal_kind": "information_salience",
                        "derivation_summary": "still non-mutating",
                        "confidence": "likely",
                        "evidence_anchors": [
                            {
                                "anchor_id": "committed_move:commit-s4b-1",
                                "evidence_kind": "committed_move",
                                "anchor_commit_id": "commit-s4b-1",
                            }
                        ],
                        "proposed_payload": {
                            "subject_ref": "commit:commit-s4b-1",
                            "salience_level": "minor",
                        },
                    }
                ],
            },
        )
        assert result.continuity_decision is not None
        self.assertFalse(result.continuity_decision.item_decisions[0].durable_mutation_applied)

    def test_host_rejects_unknown_event_ref(self) -> None:
        fixture, request, event = _session_with_event()
        catalog, _commit = build_post_commit_evidence_catalog(request, fixture)
        proposal = LibrarianSemanticProposal(
            proposal_id="prop-host",
            proposal_batch_id="batch-1",
            proposal_origin="librarian",
            proposal_kind="knowledge_revelation_significance",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id=f"public_event:{event.event_id}",
                    evidence_kind="public_event",
                ),
            ),
            derivation_summary="bad ref",
            confidence="likely",
            proposed_payload={
                "event_ref": "evt-missing",
                "subject_character": "Alice",
                "revelation_significance_level": "major",
                "interpretation_scope": "utterance_occurrence",
            },
            commit_binding=ProposalCommitBinding(
                domain_commit_id="commit-s4b-1",
                hg_round_id="round-s4b-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-1"),
        )
        item = validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id="commit-s4b-1",
        )
        self.assertIn("unknown_event_reference", item.rejection_codes)

    def test_continuity_rejects_missing_public_event_anchor(self) -> None:
        fixture, request, event = _session_with_event()
        catalog, _commit = build_post_commit_evidence_catalog(request, fixture)
        proposal = LibrarianSemanticProposal(
            proposal_id="prop-no-anchor",
            proposal_batch_id="batch-1",
            proposal_origin="librarian",
            proposal_kind="knowledge_revelation_significance",
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id="committed_move:commit-s4b-1",
                    evidence_kind="committed_move",
                    anchor_commit_id="commit-s4b-1",
                ),
            ),
            derivation_summary="missing public_event anchor",
            confidence="likely",
            proposed_payload={
                "event_ref": event.event_id,
                "subject_character": "Alice",
                "revelation_significance_level": "major",
                "interpretation_scope": "utterance_occurrence",
            },
            commit_binding=ProposalCommitBinding(
                domain_commit_id="commit-s4b-1",
                hg_round_id="round-s4b-1",
                turn_index=1,
            ),
            provenance=ProposalProvenance(librarian_inference_id="inf-1"),
        )
        closure = build_evidence_closure(
            domain_commit_id="commit-s4b-1",
            catalog_anchor_ids=tuple(item.anchor_id for item in catalog),
            catalog_visibility={item.anchor_id: item.visibility_scope for item in catalog},
            catalog_authority={item.anchor_id: item.authority_class for item in catalog},
        )
        decision = evaluate_librarian_proposal_continuity(
            proposal,
            closure=closure,
            host_accepted=True,
            catalog=catalog,
        )
        self.assertEqual(decision.outcome, "reject")
        self.assertEqual(decision.reason_code, "missing_evidence_anchors")


if __name__ == "__main__":
    unittest.main()

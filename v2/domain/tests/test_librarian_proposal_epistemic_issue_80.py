"""Issue #80 — Librarian significance epistemic contract tests."""

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
    EvidenceAnchor,
    LibrarianSemanticProposal,
    ProposalCommitBinding,
    ProposalProvenance,
    validate_proposal_payload_schema,
)
from domain_api.librarian_proposal_context import (  # noqa: E402
    build_post_commit_evidence_catalog,
)
from domain_api.librarian_proposal_epistemic import (  # noqa: E402
    INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
    INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE,
    REASON_INVALID_INTERPRETATION_SCOPE,
    REASON_PROPOSITION_TRUTH_UNSUPPORTED,
    sanitize_revelation_annotation_for_catalog,
    sanitize_revelation_significance_by_character,
)
from domain_api.librarian_proposal_service import (  # noqa: E402
    build_post_commit_proposal_request,
)
from domain_api.librarian_proposal_validate import validate_host_proposal_item  # noqa: E402
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from continuity_librarian_knowledge_significance import (  # noqa: E402
    apply_knowledge_revelation_significance,
)


def _house_dialogue_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {
                "type": "dialogue",
                "dialogue": (
                    "The house has a way of telling me what kind of person is standing in it."
                ),
            }
        ],
        "motivation": {
            "goal": "impress",
            "tactic": "speak",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
    }


def _session_with_premise(
    *,
    commit_id: str = "commit-80-1",
    event_id: str = "evt-house-1",
    premise: str = "The mansion evaluates visitors through household ritual.",
    template_id: str = "test_template",
) -> tuple:
    fixture = initialize_live_session(
        cast=["Ayame", "Guest"],
        hg_session_id="session-80",
    )
    fixture.manager.scene_state.scene_premise = premise
    fixture.manager.scene_state.role_assignments = {"Ayame": "host", "Guest": "applicant"}
    fixture.setup_snapshot = {
        "scene_template_id": template_id,
        "scene_template": {
            "template_id": template_id,
            "premise": premise,
            "role_private_knowledge": {
                "host": "The host engineered the applicant's losses before this interview.",
            },
        },
    }
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="house line",
        hg_round_id="round-80-1",
        domain_commit_id=commit_id,
        actor_id="Ayame",
        metadata={
            "continuity_turn_index": 2,
            "structured_move": _house_dialogue_move(),
        },
    )
    event = PublicEvent(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        event_type="dialogue",
        participants=["Ayame"],
        summary='Ayame said: "The house has a way of telling me what kind of person is standing in it."',
        turn_index=2,
        significance="minor",
        observed_by=["Ayame", "Guest"],
        known_by=["Ayame", "Guest"],
    )
    fixture.manager.public_events.append(event)
    request = build_post_commit_proposal_request(
        hg_scene_id="scene-80",
        hg_round_id="round-80-1",
        turn_index=2,
        domain_commit_id=commit_id,
        librarian_inference_id="inf-80",
    )
    return fixture, request, event


def _revelation_proposal(
    *,
    event_id: str,
    interpretation_scope: str,
    proposition_authority_refs: list[str] | None = None,
    derivation_summary: str = "Significance note.",
) -> LibrarianSemanticProposal:
    payload: dict = {
        "event_ref": event_id,
        "subject_character": "Ayame",
        "revelation_significance_level": "major",
        "interpretation_scope": interpretation_scope,
    }
    if proposition_authority_refs is not None:
        payload["proposition_authority_refs"] = proposition_authority_refs
    return LibrarianSemanticProposal(
        proposal_id="prop-80",
        proposal_batch_id="batch-80",
        proposal_origin="librarian",
        proposal_kind="knowledge_revelation_significance",
        evidence_anchors=(
            EvidenceAnchor(
                anchor_id=f"public_event:{event_id}",
                evidence_kind="public_event",
            ),
        ),
        derivation_summary=derivation_summary,
        confidence="likely",
        proposed_payload=payload,
        commit_binding=ProposalCommitBinding(
            domain_commit_id="commit-80-1",
            hg_round_id="round-80-1",
            turn_index=2,
        ),
        provenance=ProposalProvenance(librarian_inference_id="inf-80"),
    )


class Issue80EpistemicTests(unittest.TestCase):
    def test_schema_requires_interpretation_scope(self) -> None:
        ok, detail, codes = validate_proposal_payload_schema(
            "knowledge_revelation_significance",
            {
                "event_ref": "evt-1",
                "subject_character": "Ayame",
                "revelation_significance_level": "major",
            },
        )
        self.assertFalse(ok)
        self.assertIn("invalid_interpretation_scope", detail)

    def test_utterance_occurrence_accepts_without_authority_refs(self) -> None:
        ok, _, _ = validate_proposal_payload_schema(
            "knowledge_revelation_significance",
            {
                "event_ref": "evt-1",
                "subject_character": "Ayame",
                "revelation_significance_level": "major",
                "interpretation_scope": INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE,
            },
        )
        self.assertTrue(ok)

    def test_referenced_scope_requires_authority_refs(self) -> None:
        ok, _, codes = validate_proposal_payload_schema(
            "knowledge_revelation_significance",
            {
                "event_ref": "evt-1",
                "subject_character": "Ayame",
                "revelation_significance_level": "major",
                "interpretation_scope": INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
            },
        )
        self.assertFalse(ok)
        self.assertIn("missing_proposition_authority", codes)

    def test_unsupported_assertion_rejects_dialogue_only_world_truth(self) -> None:
        fixture, request, event = _session_with_premise()
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        proposal = _revelation_proposal(
            event_id=event.event_id,
            interpretation_scope=INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
            proposition_authority_refs=[f"public_event:{event.event_id}"],
            derivation_summary="The house has a supernatural evaluative capability.",
        )
        host = validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id=request.domain_commit_id,
        )
        self.assertFalse(host.accepted)
        self.assertIn(REASON_PROPOSITION_TRUTH_UNSUPPORTED, host.rejection_codes)

    def test_utterance_occurrence_passes_host_and_persists_scope(self) -> None:
        fixture, request, event = _session_with_premise()
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        proposal = _revelation_proposal(
            event_id=event.event_id,
            interpretation_scope=INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE,
            derivation_summary=(
                "Ayame claimed the house tells her about people — narratively significant utterance."
            ),
        )
        host = validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id=request.domain_commit_id,
        )
        self.assertTrue(host.accepted)
        result = apply_knowledge_revelation_significance(fixture.manager, proposal)
        self.assertTrue(result.applied)
        annotation = event.revelation_significance_by_character["Ayame"]
        self.assertEqual(annotation["interpretation_scope"], INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE)
        self.assertEqual(event.summary, proposal.proposed_payload and event.summary)

    def test_legitimate_scenario_revelation_with_premise_ref(self) -> None:
        fixture, request, event = _session_with_premise()
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        premise_anchor = "scenario_premise:test_template"
        proposal = _revelation_proposal(
            event_id=event.event_id,
            interpretation_scope=INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
            proposition_authority_refs=[premise_anchor],
            derivation_summary="Utterance references scenario-established household evaluation context.",
        )
        host = validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id=request.domain_commit_id,
        )
        self.assertTrue(host.accepted)

    def test_role_private_alone_cannot_satisfy_world_truth(self) -> None:
        fixture, request, event = _session_with_premise()
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        proposal = _revelation_proposal(
            event_id=event.event_id,
            interpretation_scope=INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
            proposition_authority_refs=["authored_role_private:Ayame"],
        )
        host = validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id=request.domain_commit_id,
        )
        self.assertFalse(host.accepted)
        self.assertIn(REASON_PROPOSITION_TRUTH_UNSUPPORTED, host.rejection_codes)

    def test_role_private_plus_premise_passes(self) -> None:
        fixture, request, event = _session_with_premise()
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        proposal = _revelation_proposal(
            event_id=event.event_id,
            interpretation_scope=INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
            proposition_authority_refs=[
                "authored_role_private:Ayame",
                "scenario_premise:test_template",
            ],
        )
        host = validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id=request.domain_commit_id,
        )
        self.assertTrue(host.accepted)

    def test_missing_scope_rejected_by_host(self) -> None:
        fixture, request, event = _session_with_premise()
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        proposal = _revelation_proposal(
            event_id=event.event_id,
            interpretation_scope="",
        )
        host = validate_host_proposal_item(
            proposal,
            catalog=catalog,
            domain_commit_id=request.domain_commit_id,
        )
        self.assertFalse(host.accepted)
        self.assertIn(REASON_INVALID_INTERPRETATION_SCOPE, host.rejection_codes)

    def test_unscoped_annotation_excluded_from_sanitize(self) -> None:
        raw = {
            "Ayame": {
                "revelation_significance_level": "major",
                "derivation_summary": "The house watches everything as world truth.",
                "confidence": "likely",
            }
        }
        sanitized = sanitize_revelation_significance_by_character(raw)
        self.assertIsNone(sanitized)
        self.assertEqual(sanitize_revelation_annotation_for_catalog(raw["Ayame"]), {})

    def test_catalog_feedback_omits_unscoped_annotations(self) -> None:
        fixture, request, event = _session_with_premise()
        event.revelation_significance_by_character = {
            "Ayame": {
                "revelation_significance_level": "pivotal",
                "derivation_summary": "Unsafe historical world ontology prose.",
                "confidence": "likely",
            }
        }
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        public_items = [item for item in catalog if item.evidence_kind == "public_event"]
        self.assertEqual(len(public_items), 1)
        payload = json.loads(public_items[0].content)
        annotations = payload.get("revelation_significance_by_character")
        self.assertIsNone(annotations)

    def test_catalog_feedback_mixed_scoped_and_unscoped(self) -> None:
        fixture, request, event = _session_with_premise()
        event.revelation_significance_by_character = {
            "Ayame": {
                "revelation_significance_level": "pivotal",
                "derivation_summary": "Excluded historical prose.",
            },
            "Guest": {
                "revelation_significance_level": "major",
                "interpretation_scope": INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE,
                "annotation_note": "Guest overheard a significant claim.",
            },
        }
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        payload = json.loads(
            next(item for item in catalog if item.evidence_kind == "public_event").content
        )
        annotations = payload.get("revelation_significance_by_character") or {}
        self.assertNotIn("Ayame", annotations)
        self.assertIn("Guest", annotations)
        self.assertEqual(
            annotations["Guest"]["interpretation_scope"],
            INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE,
        )
        self.assertNotIn("derivation_summary", annotations["Guest"])

    def test_scenario_premise_anchor_in_catalog(self) -> None:
        fixture, request, _event = _session_with_premise()
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        premise_items = [item for item in catalog if item.evidence_kind == "scenario_premise"]
        self.assertEqual(len(premise_items), 1)
        metadata = dict(premise_items[0].provenance or {}).get("authority_metadata") or {}
        self.assertTrue(metadata.get("world_truth_eligible"))

    def test_occurrence_query_preserved_in_public_event_summary(self) -> None:
        fixture, _request, event = _session_with_premise()
        self.assertIn("Ayame said:", event.summary)
        self.assertIn("house has a way", event.summary)

    def test_scoped_annotation_preserves_refs_in_catalog(self) -> None:
        fixture, request, event = _session_with_premise()
        event.revelation_significance_by_character = {
            "Ayame": {
                "revelation_significance_level": "major",
                "interpretation_scope": INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
                "proposition_authority_refs": ["scenario_premise:test_template"],
                "derivation_summary": "Should not appear in catalog export.",
            }
        }
        catalog, _ = build_post_commit_evidence_catalog(request, fixture)
        payload = json.loads(
            next(item for item in catalog if item.evidence_kind == "public_event").content
        )
        ann = payload["revelation_significance_by_character"]["Ayame"]
        self.assertEqual(
            ann["interpretation_scope"],
            INTERPRETATION_SCOPE_REFERENCED_AUTHORITATIVE,
        )
        self.assertEqual(ann["proposition_authority_refs"], ["scenario_premise:test_template"])
        self.assertNotIn("derivation_summary", ann)

    def test_sanitize_scoped_keeps_annotation_note_not_derivation_summary(self) -> None:
        cleaned = sanitize_revelation_annotation_for_catalog(
            {
                "interpretation_scope": INTERPRETATION_SCOPE_UTTERANCE_OCCURRENCE,
                "derivation_summary": "bad",
                "annotation_note": "Ayame's figurative claim was pivotal.",
                "revelation_significance_level": "major",
            }
        )
        self.assertNotIn("derivation_summary", cleaned)
        self.assertEqual(cleaned.get("annotation_note"), "Ayame's figurative claim was pivotal.")


if __name__ == "__main__":
    unittest.main()

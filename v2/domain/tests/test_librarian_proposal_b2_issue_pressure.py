"""#40 B2 issue_tension_pressure semantic overlay tests."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_librarian_issue_pressure import (  # noqa: E402
    REASON_UNKNOWN_ISSUE,
    apply_issue_tension_pressure,
)
from continuity_scene_pressure_projection import (  # noqa: E402
    build_scene_pressure_entry,
    compute_issue_material_fingerprint,
    get_projectable_issue_pressure_overlay,
)
from continuity_state import IssueState, IssueStatus  # noqa: E402
from domain_api.librarian_proposal_contract import (  # noqa: E402
    EvidenceAnchor,
    LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
    ProposalCommitBinding,
    ProposalProvenance,
    LibrarianSemanticProposal,
    validate_proposal_payload_schema,
)
from domain_api.librarian_proposal_context import build_post_commit_evidence_catalog  # noqa: E402
from domain_api.librarian_proposal_service import (  # noqa: E402
    LibrarianProposalService,
    build_post_commit_proposal_request,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import initialize_live_session, RoundFixture  # noqa: E402
from continuity_librarian_proposals import (  # noqa: E402
    REASON_UNKNOWN_ISSUE as CONTINUITY_UNKNOWN_ISSUE,
    build_evidence_closure,
    evaluate_librarian_proposal_continuity,
)
from domain_api.character_context_projector import project_character_scene_pressures  # noqa: E402
from domain_api.director_context_digests import project_scene_pressures_digest  # noqa: E402
from domain_api.storyteller_orientation_context import (  # noqa: E402
    build_storyteller_orientation_context,
)


def _minimal_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "dialogue", "dialogue": "We cannot proceed until the vault opens."}],
        "motivation": {
            "goal": "advance",
            "tactic": "press",
            "emotional_driver": "urgency",
            "risk_level": "medium",
        },
    }


def _active_issue(*, issue_id: str = "issue-pressure-1", status: IssueStatus = IssueStatus.ACTIVE) -> IssueState:
    return IssueState(
        issue_id=issue_id,
        description="Vault access remains blocked.",
        participants=["Alice", "Bob"],
        status=status,
        created_at=datetime.now(timezone.utc),
        pressure_kind="access_conflict",
        blocked_what="Vault access",
        required_next_step="Someone must find the key.",
        last_change="Alice refused to leave.",
    )


def _session_with_issue(
    *,
    commit_id: str = "commit-b2-1",
    issue: IssueState | None = None,
) -> tuple:
    fixture = initialize_live_session(
        cast=["Alice", "Bob"],
        hg_session_id="session-b2",
    )
    issue = issue or _active_issue()
    fixture.manager.issues[issue.issue_id] = issue
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.active_issue_ids = [issue.issue_id]
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="blocked at vault",
        hg_round_id="round-b2-1",
        domain_commit_id=commit_id,
        actor_id="Alice",
        metadata={
            "continuity_turn_index": 1,
            "structured_move": _minimal_move(),
        },
    )
    request = build_post_commit_proposal_request(
        hg_scene_id="scene-b2",
        hg_round_id="round-b2-1",
        turn_index=1,
        domain_commit_id=commit_id,
        librarian_inference_id="inf-librarian-b2",
    )
    return fixture, request, issue


def _proposal(
    *,
    commit_id: str,
    issue_id: str,
    proposal_id: str = "prop-b2-1",
    semantic: str = "The vault remains sealed and the group lacks the key.",
    stakes: str | None = "Party progress toward the objective is stalled.",
    manufactured: bool = False,
    pressure_kind: str | None = None,
) -> LibrarianSemanticProposal:
    payload: dict = {
        "issue_ref": issue_id,
        "semantic_unmet_condition": semantic,
    }
    if stakes:
        payload["stakes_summary"] = stakes
    if manufactured:
        payload["manufactured_fact"] = True
    if pressure_kind:
        payload["pressure_kind"] = pressure_kind
    return LibrarianSemanticProposal(
        proposal_id=proposal_id,
        proposal_batch_id="batch-b2-1",
        proposal_origin="librarian",
        proposal_kind="issue_tension_pressure",
        evidence_anchors=(
            EvidenceAnchor(
                anchor_id=f"committed_move:{commit_id}",
                evidence_kind="committed_move",
                anchor_commit_id=commit_id,
            ),
            EvidenceAnchor(
                anchor_id=f"continuity_issue:{issue_id}",
                evidence_kind="continuity_issue",
                anchor_commit_id=commit_id,
            ),
        ),
        derivation_summary="The unresolved vault access pressure remains salient.",
        confidence="likely",
        proposed_payload=payload,
        commit_binding=ProposalCommitBinding(
            domain_commit_id=commit_id,
            hg_round_id="round-b2-1",
            turn_index=1,
        ),
        provenance=ProposalProvenance(
            librarian_inference_id="inf-librarian-b2",
            source_bundle_id="bundle-b2",
        ),
    )


class TestB2IssuePressureOverlay(unittest.TestCase):
    def test_valid_proposal_creates_active_overlay_outside_issue_state(self) -> None:
        fixture, _request, issue = _session_with_issue()
        proposal = _proposal(commit_id="commit-b2-1", issue_id=issue.issue_id)
        result = apply_issue_tension_pressure(fixture.manager, proposal)
        self.assertTrue(result.applied)
        self.assertEqual(result.reason_code, "applied")
        overlay = fixture.manager.issue_pressure_semantic_overlays[issue.issue_id]
        self.assertEqual(overlay["lifecycle"], "active")
        self.assertNotIn("semantic_unmet_condition", issue.to_dict())

    def test_schema_rejects_forbidden_pressure_kind_field(self) -> None:
        ok, detail, _codes = validate_proposal_payload_schema(
            "issue_tension_pressure",
            {
                "issue_ref": "issue-1",
                "semantic_unmet_condition": "blocked",
                "pressure_kind": "access_conflict",
            },
        )
        self.assertFalse(ok)
        self.assertIn("authority_elevation", detail)

    def test_unknown_issue_rejected_at_apply(self) -> None:
        fixture, _request, issue = _session_with_issue()
        proposal = _proposal(commit_id="commit-b2-1", issue_id="missing-issue")
        result = apply_issue_tension_pressure(fixture.manager, proposal)
        self.assertFalse(result.applied)
        self.assertEqual(result.reason_code, REASON_UNKNOWN_ISSUE)
        self.assertNotIn("missing-issue", fixture.manager.issue_pressure_semantic_overlays)

    def test_continuity_rejects_unknown_issue_in_catalog(self) -> None:
        fixture, request, issue = _session_with_issue()
        catalog, _commit = build_post_commit_evidence_catalog(request, fixture)
        closure = build_evidence_closure(
            domain_commit_id=request.domain_commit_id,
            catalog_anchor_ids=tuple(item.anchor_id for item in catalog),
            catalog_visibility={item.anchor_id: item.visibility_scope for item in catalog},
            catalog_authority={item.anchor_id: item.authority_class for item in catalog},
        )
        proposal = replace(
            _proposal(commit_id=request.domain_commit_id, issue_id="missing-issue"),
            evidence_anchors=(
                EvidenceAnchor(
                    anchor_id=f"committed_move:{request.domain_commit_id}",
                    evidence_kind="committed_move",
                    anchor_commit_id=request.domain_commit_id,
                ),
                EvidenceAnchor(
                    anchor_id=f"continuity_issue:{issue.issue_id}",
                    evidence_kind="continuity_issue",
                    anchor_commit_id=request.domain_commit_id,
                ),
            ),
        )
        decision = evaluate_librarian_proposal_continuity(
            proposal,
            closure=closure,
            host_accepted=True,
            catalog=catalog,
        )
        self.assertEqual(decision.outcome, "reject")
        self.assertEqual(decision.reason_code, CONTINUITY_UNKNOWN_ISSUE)

    def test_newer_annotation_supersedes_prior(self) -> None:
        fixture, _request, issue = _session_with_issue()
        first = apply_issue_tension_pressure(
            fixture.manager,
            _proposal(commit_id="commit-b2-1", issue_id=issue.issue_id, proposal_id="prop-1"),
        )
        second = apply_issue_tension_pressure(
            fixture.manager,
            _proposal(
                commit_id="commit-b2-1",
                issue_id=issue.issue_id,
                proposal_id="prop-2",
                semantic="The seal still holds and no alternate route exists.",
            ),
        )
        self.assertTrue(first.applied)
        self.assertTrue(second.applied)
        overlay = fixture.manager.issue_pressure_semantic_overlays[issue.issue_id]
        self.assertEqual(overlay["proposal_id"], "prop-2")

    def test_material_issue_update_stales_overlay_projection(self) -> None:
        fixture, _request, issue = _session_with_issue()
        apply_issue_tension_pressure(
            fixture.manager,
            _proposal(commit_id="commit-b2-1", issue_id=issue.issue_id),
        )
        self.assertIsNotNone(get_projectable_issue_pressure_overlay(fixture.manager, issue.issue_id))
        issue.last_change = "Bob found a hidden latch."
        self.assertIsNone(get_projectable_issue_pressure_overlay(fixture.manager, issue.issue_id))

    def test_resolved_issue_overlay_not_projected(self) -> None:
        fixture, _request, issue = _session_with_issue()
        apply_issue_tension_pressure(
            fixture.manager,
            _proposal(commit_id="commit-b2-1", issue_id=issue.issue_id),
        )
        issue.status = IssueStatus.RESOLVED
        self.assertIsNone(get_projectable_issue_pressure_overlay(fixture.manager, issue.issue_id))

    def test_missing_overlay_falls_back_to_deterministic_pressure(self) -> None:
        issue = _active_issue()
        entry = build_scene_pressure_entry(issue, None)
        self.assertEqual(entry["blocked_what"], issue.blocked_what)
        self.assertNotIn("semantic_unmet_condition", entry)

    def test_director_character_storyteller_receive_augmented_pressure(self) -> None:
        fixture, _request, issue = _session_with_issue()
        apply_issue_tension_pressure(
            fixture.manager,
            _proposal(commit_id="commit-b2-1", issue_id=issue.issue_id),
        )
        director_contrib, director_refs = project_scene_pressures_digest(fixture, "manifest-b2")
        assert director_contrib is not None
        director_payload = json.loads(director_contrib.content.split(":\n", 1)[1])
        director_issue = director_payload["active_issues"][0]
        self.assertIn("semantic_unmet_condition", director_issue)
        self.assertEqual(
            director_issue["semantic_authority"]["authority_class"],
            "derived",
        )
        semantic_ref = next(
            ref for ref in director_refs if ref["ref_id"].endswith(":semantic_unmet_condition")
        )
        self.assertEqual(semantic_ref["authority_class"], "derived")

        character_contrib = project_character_scene_pressures(fixture, character_id="Alice")
        assert character_contrib is not None
        self.assertIn("semantic_unmet_condition", character_contrib.content)

        rnd = RoundFixture(
            hg_round_id="round-b2-1",
            hg_scene_id=fixture.hg_scene_id,
            turn_index=1,
        )
        _manifest, contribs, _refs, _env = build_storyteller_orientation_context(
            fixture,
            rnd,
            inference_id="inf-b2",
        )
        storyteller_pressure = next(
            contrib for contrib in contribs if contrib.source_kind == "scene_pressures"
        )
        self.assertIn("semantic_unmet_condition", storyteller_pressure.content)

    def test_service_finalize_records_issue_pressure_audit(self) -> None:
        fixture, request, issue = _session_with_issue()
        proposal_result = {
            "schema": LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
            "proposals": [
                {
                    "proposal_id": "prop-b2-service",
                    "proposal_kind": "issue_tension_pressure",
                    "derivation_summary": "Vault pressure remains unresolved.",
                    "confidence": "likely",
                    "evidence_anchors": [
                        {
                            "anchor_id": f"committed_move:{request.domain_commit_id}",
                            "evidence_kind": "committed_move",
                            "anchor_commit_id": request.domain_commit_id,
                        },
                        {
                            "anchor_id": f"continuity_issue:{issue.issue_id}",
                            "evidence_kind": "continuity_issue",
                            "anchor_commit_id": request.domain_commit_id,
                        },
                    ],
                    "proposed_payload": {
                        "issue_ref": issue.issue_id,
                        "semantic_unmet_condition": "The vault remains sealed.",
                        "stakes_summary": "Progress is blocked.",
                    },
                }
            ],
        }
        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=proposal_result,
        )
        self.assertIsNotNone(result.continuity_decision)
        audit = fixture.librarian_proposal_audit_log[-1]
        self.assertIn("issue_pressure_apply_results", audit)
        self.assertTrue(audit["issue_pressure_apply_results"])
        self.assertIn(issue.issue_id, fixture.manager.issue_pressure_semantic_overlays)

    def test_inference_failure_retains_projectable_overlay(self) -> None:
        fixture, request, issue = _session_with_issue()
        apply_issue_tension_pressure(
            fixture.manager,
            _proposal(commit_id="commit-b2-1", issue_id=issue.issue_id),
        )
        self.assertIsNotNone(
            get_projectable_issue_pressure_overlay(fixture.manager, issue.issue_id)
        )
        service = LibrarianProposalService()
        result = service.finalize_proposals(request, fixture, proposal_result=None)
        self.assertEqual(result.degradation_mode, "inference_failed")
        self.assertIsNotNone(
            get_projectable_issue_pressure_overlay(fixture.manager, issue.issue_id)
        )

    def test_overlay_persists_round_trip(self) -> None:
        fixture, _request, issue = _session_with_issue()
        apply_issue_tension_pressure(
            fixture.manager,
            _proposal(commit_id="commit-b2-1", issue_id=issue.issue_id),
        )
        fingerprint_before = compute_issue_material_fingerprint(issue)
        blob = fixture.manager.to_dict()
        from continuity_manager import ContinuityManager

        restored = ContinuityManager.from_dict(blob)
        overlay = restored.issue_pressure_semantic_overlays[issue.issue_id]
        self.assertEqual(overlay["issue_material_fingerprint"], fingerprint_before)


if __name__ == "__main__":
    unittest.main()

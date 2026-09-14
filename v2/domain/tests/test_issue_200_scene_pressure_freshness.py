"""Issue #200 — scene-pressure freshness and inverse R16 contract tests."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_librarian_issue_pressure import apply_issue_tension_pressure  # noqa: E402
from continuity_scene_pressure_projection import (  # noqa: E402
    build_scene_pressure_entry,
    note_authoritative_player_contribution,
    overlay_semantic_fields_are_fresh,
)
from continuity_state import IssueState, IssueStatus  # noqa: E402
from domain_api.character_context_projector import (  # noqa: E402
    SCENE_PRESSURE_PRECEDENCE_NOTE,
    project_character_scene_pressures,
)
from domain_api.character_conversation_projection import (  # noqa: E402
    project_character_conversation_for_manifest,
)
from domain_api.director_context_digests import project_scene_pressures_digest  # noqa: E402
from domain_api.librarian_proposal_contract import (  # noqa: E402
    EvidenceAnchor,
    ProposalCommitBinding,
    ProposalProvenance,
    LibrarianSemanticProposal,
)
from domain_api.player_action_completion_authority import (  # noqa: E402
    build_player_action_completion_guardrail,
)
from domain_api.contract import SemanticEvaluationContextPrepareRequest  # noqa: E402
from domain_api.semantic_evaluation_context import prepare_semantic_evaluation_context  # noqa: E402
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from domain.tests.perceptual_test_helpers import ayame_threshold_context  # noqa: E402
from domain.tests.test_issue_155_player_perceptual_entitlement import (  # noqa: E402
    Issue155AyameProductionPathTests,
)
from perceptual_visibility_contract import PLAYER_SOURCE_KIND  # noqa: E402
from perceptual_visibility_projection import assemble_perceptual_history_entry_for_viewer  # noqa: E402
from player_uniform_projection import build_uniform_projection_decomposition  # noqa: E402
from player_perceptual_service import validate_player_perceptual_decomposition  # noqa: E402


def _active_issue() -> IssueState:
    return IssueState(
        issue_id="issue-pressure-200",
        description="Household entry protocol remains contested.",
        participants=["Ayame", "Kizzie"],
        status=IssueStatus.ESCALATING,
        created_at=datetime.now(timezone.utc),
        pressure_kind="control_conflict",
        blocked_what="Clear control of the immediate interaction",
        required_next_step="Authority dynamics must be resolved.",
        last_change="Ayame asserted authority or control.",
    )


def _proposal(*, commit_id: str, issue_id: str, semantic: str) -> LibrarianSemanticProposal:
    return LibrarianSemanticProposal(
        proposal_id="prop-issue-200",
        proposal_batch_id="batch-200",
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
        derivation_summary="test overlay",
        confidence="likely",
        proposed_payload={
            "issue_ref": issue_id,
            "semantic_unmet_condition": semantic,
            "stakes_summary": "Entry evaluation cannot proceed.",
        },
        commit_binding=ProposalCommitBinding(
            domain_commit_id=commit_id,
            hg_round_id="round-200",
            turn_index=1,
        ),
        provenance=ProposalProvenance(
            librarian_inference_id="inf-200",
            source_bundle_id="bundle-200",
        ),
    )


def _session_with_overlay(*, semantic: str) -> tuple:
    fixture = initialize_live_session(cast=["Ayame", "Kizzie"], hg_session_id="session-200")
    issue = _active_issue()
    fixture.manager.issues[issue.issue_id] = issue
    assert fixture.manager.scene_state is not None
    fixture.manager.scene_state.active_issue_ids = [issue.issue_id]
    append_history_entry(
        fixture.rp_history,
        kind="committed_turn",
        content="Ayame opened the door.",
        hg_round_id="round-200",
        domain_commit_id="commit-turn-1",
        actor_id="Ayame",
        metadata={"continuity_turn_index": 1, "structured_move": {"beats": []}},
    )
    apply_issue_tension_pressure(
        fixture.manager,
        _proposal(
            commit_id="commit-turn-1",
            issue_id=issue.issue_id,
            semantic=semantic,
        ),
    )
    return fixture, issue


class Issue200ScenePressureFreshnessTests(unittest.TestCase):
    def test_a_stale_overlay_withholds_objective_semantic_after_player_turn(self) -> None:
        fixture, issue = _session_with_overlay(
            semantic=(
                "Authority dynamics remain contested: compliance has not yet occurred, "
                "so clear control is unresolved."
            )
        )
        overlay = fixture.manager.issue_pressure_semantic_overlays[issue.issue_id]
        self.assertTrue(overlay_semantic_fields_are_fresh(fixture.manager, overlay))

        player_entry = append_history_entry(
            fixture.rp_history,
            kind="user",
            content="Kizzie hummed a tune and adjusted her scarf.",
            actor_id="Kizzie",
            hg_round_id="round-200-2",
        )
        note_authoritative_player_contribution(
            fixture.manager,
            int(player_entry["sequence_index"]),
        )
        self.assertFalse(overlay_semantic_fields_are_fresh(fixture.manager, overlay))

        entry = build_scene_pressure_entry(
            issue,
            overlay,
            manager=fixture.manager,
        )
        self.assertNotIn("semantic_unmet_condition", entry)
        self.assertIn("blocked_what", entry)

    def test_b_freshness_is_structural_not_lexical(self) -> None:
        fixture, issue = _session_with_overlay(
            semantic="Vault compliance has not yet occurred and access remains blocked."
        )
        overlay = fixture.manager.issue_pressure_semantic_overlays[issue.issue_id]
        player_entry = append_history_entry(
            fixture.rp_history,
            kind="user",
            content="Alice recited unrelated poetry about the weather.",
            actor_id="Kizzie",
            hg_round_id="round-200-3",
        )
        note_authoritative_player_contribution(
            fixture.manager,
            int(player_entry["sequence_index"]),
        )
        entry = build_scene_pressure_entry(issue, overlay, manager=fixture.manager)
        self.assertNotIn("semantic_unmet_condition", entry)

    def test_c_fresh_overlay_after_latest_player_projects_semantics(self) -> None:
        fixture, issue = _session_with_overlay(
            semantic="Compliance has not yet occurred."
        )
        player_entry = append_history_entry(
            fixture.rp_history,
            kind="user",
            content="Earlier player line.",
            actor_id="Kizzie",
            hg_round_id="round-200-4",
        )
        note_authoritative_player_contribution(
            fixture.manager,
            int(player_entry["sequence_index"]),
        )
        apply_issue_tension_pressure(
            fixture.manager,
            replace(
                _proposal(
                    commit_id="commit-turn-2",
                    issue_id=issue.issue_id,
                    semantic="Refreshed overlay after latest player contribution.",
                ),
                proposal_id="prop-issue-200-refreshed",
            ),
        )
        overlay = fixture.manager.issue_pressure_semantic_overlays[issue.issue_id]
        entry = build_scene_pressure_entry(issue, overlay, manager=fixture.manager)
        self.assertIn("semantic_unmet_condition", entry)
        self.assertIn("Refreshed overlay", entry["semantic_unmet_condition"])

    def test_character_manifest_includes_precedence_note(self) -> None:
        fixture, _issue = _session_with_overlay(semantic="Compliance has not yet occurred.")
        contrib = project_character_scene_pressures(fixture, character_id="Ayame")
        assert contrib is not None
        self.assertIn(SCENE_PRESSURE_PRECEDENCE_NOTE, contrib.content)

    def test_director_digest_withholds_stale_semantic_refs(self) -> None:
        fixture, issue = _session_with_overlay(semantic="Compliance has not yet occurred.")
        overlay = fixture.manager.issue_pressure_semantic_overlays[issue.issue_id]
        player_entry = append_history_entry(
            fixture.rp_history,
            kind="user",
            content="Unrelated player post.",
            actor_id="Kizzie",
            hg_round_id="round-200-5",
        )
        note_authoritative_player_contribution(
            fixture.manager,
            int(player_entry["sequence_index"]),
        )
        _contrib, refs = project_scene_pressures_digest(fixture, "manifest-200")
        ref_ids = [ref["ref_id"] for ref in refs]
        self.assertNotIn(f"issue:{issue.issue_id}:semantic_unmet_condition", ref_ids)


class Issue200InverseR16ContractTests(unittest.TestCase):
    def test_guardrail_documents_inverse_regression(self) -> None:
        text = str(build_player_action_completion_guardrail()["text"])
        self.assertIn("R16 inverse", text)
        self.assertIn("objective regression", text)
        self.assertIn("incomplete perception", text)

    def test_semantic_eval_instruction_documents_inverse_r16(self) -> None:
        fixture = initialize_live_session(cast=["Ayame"], hg_session_id="session-eval-200")
        req = SemanticEvaluationContextPrepareRequest(
            hg_scene_id=fixture.hg_scene_id,
            hg_round_id="round-eval",
            inference_id="inf-eval-200",
            character_id="Ayame",
            role="host",
            turn_index=1,
            evaluation_pass_id="eval-200",
            candidate_move={"beats": [], "move_schema_version": 2},
            raw_model_output="{}",
        )
        contributions, _refs, _package = prepare_semantic_evaluation_context(fixture, req)
        instruction = next(c for c in contributions if c.contribution_id.endswith("-eval-instruction"))
        self.assertIn("Objective regression", instruction.content)
        self.assertIn("incomplete perception", instruction.content)


class Issue200PerceptionPreservationTests(unittest.TestCase):
    def test_d_closed_opaque_withholding_unchanged(self) -> None:
        content = "Kizzie wiped her feet and stepped inside."
        decomposition = build_uniform_projection_decomposition(
            content,
            checker_audit={
                "uniform_projection_safe": True,
                "reason": "test",
                "inference_id": "issue-200-test",
            },
        )
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Kizzie",
            decomposition=decomposition,
        )
        entry = {
            "entry_id": "hist-200",
            "sequence_index": 3,
            "kind": "user",
            "content": content,
            "metadata": {"player_decomposition": record.to_dict(), "validation_audit": audit},
        }
        context = ayame_threshold_context(door_state="closed")
        result = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Ayame",
            present_characters=["Ayame", "Kizzie"],
            source_kind=PLAYER_SOURCE_KIND,
            perceptual_scene_context=context,
            player_character="Kizzie",
        )
        self.assertIsNone(result.content)

    def test_issue_155_production_withholding_regression(self) -> None:
        suite = Issue155AyameProductionPathTests()
        suite.setUp()
        try:
            suite.test_production_visual_only_turn_withheld_from_ayame()
        finally:
            suite.tearDown()


class Issue200F06ReplayTests(unittest.TestCase):
    def test_f06_stale_compliance_pressure_withheld_after_player_turn(self) -> None:
        fixture, issue = _session_with_overlay(
            semantic=(
                "Authority dynamics remain contested: Ayame has set protocol and is waiting "
                "for Kizzie to comply, but that compliance has not yet occurred, so clear "
                "control of the immediate interaction is still unresolved."
            )
        )
        player_content = (
            'Kizzie smiled, wiping her feet and stepping inside. "Thank you for seeing me," '
            "she offered politely as she toed off her shoes and positioned them to face the doorway."
        )
        player_entry = append_history_entry(
            fixture.rp_history,
            kind="user",
            content=player_content,
            actor_id="Kizzie",
            hg_round_id="round-f06",
        )
        note_authoritative_player_contribution(
            fixture.manager,
            int(player_entry["sequence_index"]),
        )
        contrib = project_character_scene_pressures(fixture, character_id="Ayame")
        assert contrib is not None
        payload = json.loads(contrib.content.split("\n", 2)[-1])
        issue_entry = payload["active_issues"][0]
        self.assertNotIn("semantic_unmet_condition", issue_entry)
        self.assertNotIn("compliance has not yet occurred", contrib.content)

        transcript, trigger, _audit = project_character_conversation_for_manifest(
            fixture,
            character_id="Ayame",
        )
        joined = f"{transcript or ''}{trigger or ''}"
        self.assertNotIn("wiping her feet", joined.lower())


if __name__ == "__main__":
    unittest.main()

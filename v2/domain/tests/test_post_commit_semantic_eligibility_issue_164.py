"""Issue #164 post-commit semantic eligibility and skip finalize."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_proposal_service import (  # noqa: E402
    LibrarianProposalService,
    build_post_commit_proposal_request,
)
from domain_api.post_commit_semantic_eligibility import (  # noqa: E402
    evaluate_post_commit_semantic_eligibility,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402


def _minimal_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "waits"}],
        "motivation": {
            "goal": "wait",
            "tactic": "pause",
            "emotional_driver": "calm",
            "risk_level": "low",
        },
    }


class PostCommitSemanticEligibilityTests(unittest.TestCase):
    def _session(self, *, commit_id: str = "commit-elig-1"):
        fixture = initialize_live_session(cast=["Alice"], hg_session_id="session-elig")
        append_history_entry(
            fixture.rp_history,
            kind="committed_turn",
            content="waits",
            hg_round_id="round-elig",
            domain_commit_id=commit_id,
            actor_id="Alice",
            metadata={
                "continuity_turn_index": 1,
                "structured_move": _minimal_move(),
            },
        )
        request = build_post_commit_proposal_request(
            hg_scene_id="scene-elig",
            hg_round_id="round-elig",
            turn_index=1,
            domain_commit_id=commit_id,
            librarian_inference_id="inf-semantic-1",
        )
        return fixture, request

    def test_no_active_issues_skips_inference(self) -> None:
        fixture, request = self._session()
        required, outcome = evaluate_post_commit_semantic_eligibility(fixture)
        self.assertFalse(required)
        self.assertEqual(outcome, "no_eligible_active_issues")

        service = LibrarianProposalService()
        result = service.finalize_proposals(
            request,
            fixture,
            proposal_result=None,
            proposal_generation_skip_reason=outcome,
        )
        self.assertEqual(result.degradation_mode, "eligibility_skipped")
        self.assertEqual(result.proposals, ())
        self.assertTrue(fixture.librarian_proposal_audit_log)
        audit = fixture.librarian_proposal_audit_log[-1]
        self.assertEqual(audit.get("semantic_eligibility_skip_reason"), outcome)
        self.assertEqual(audit.get("semantic_producer_role"), "storyteller")
        self.assertEqual(audit.get("post_commit_semantic_domain_commit_id"), "commit-elig-1")
        self.assertEqual(audit.get("post_commit_semantic_inference_id"), "inf-semantic-1")
        self.assertNotIn("librarian_inference_id", audit)

    def test_retired_kinds_rejected_on_new_runs(self) -> None:
        from domain_api.librarian_proposal_contract import validate_proposal_payload_schema

        ok, _, codes = validate_proposal_payload_schema(
            "information_salience",
            {"subject_ref": "x", "salience_level": "minor"},
        )
        self.assertFalse(ok)
        self.assertIn("retired_proposal_kind", codes)

        ok_legacy, _, _ = validate_proposal_payload_schema(
            "information_salience",
            {"subject_ref": "x", "salience_level": "minor"},
            allow_legacy_kinds=True,
        )
        self.assertTrue(ok_legacy)


if __name__ == "__main__":
    unittest.main()

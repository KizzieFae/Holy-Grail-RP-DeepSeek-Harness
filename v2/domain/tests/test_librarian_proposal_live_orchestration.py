"""#39 live S4 orchestration Host tests: persistence, at-most-once, audit hydration."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.librarian_proposal_contract import LIBRARIAN_PROPOSAL_RESULT_SCHEMA  # noqa: E402
from domain_api.librarian_proposal_service import (  # noqa: E402
    build_post_commit_proposal_request,
    find_terminal_audit_for_commit,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402


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


def _session_with_commit(*, commit_id: str = "commit-1", hg_scene_id: str = "scene-1") -> tuple:
    fixture = initialize_live_session(
        cast=["Alice"],
        hg_session_id=hg_scene_id,
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
        hg_scene_id=hg_scene_id,
        hg_round_id="round-1",
        turn_index=1,
        domain_commit_id=commit_id,
        librarian_inference_id="inf-librarian-1",
    )
    return fixture, request


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


class LibrarianLiveOrchestrationHostTests(unittest.TestCase):
    def test_find_terminal_audit_for_commit(self) -> None:
        fixture, request = _session_with_commit()
        repo = SessionRepository()
        repo._cache[fixture.hg_scene_id] = fixture  # type: ignore[attr-defined]
        kernel = DomainKernel.for_repository(repo)

        self.assertIsNone(find_terminal_audit_for_commit(fixture, request.domain_commit_id))

        kernel.finalize_librarian_proposals(
            hg_scene_id=fixture.hg_scene_id,
            inference_id=request.librarian_inference_id,
            proposal_context_request={
                "request_id": request.request_id,
                "hg_round_id": request.hg_round_id,
                "turn_index": request.turn_index,
                "domain_commit_id": request.domain_commit_id,
            },
            proposal_result=None,
        )
        audit = find_terminal_audit_for_commit(fixture, request.domain_commit_id)
        self.assertIsNotNone(audit)
        assert audit is not None
        self.assertEqual(audit["librarian_proposal_domain_commit_id"], request.domain_commit_id)

    def test_prepare_skips_when_audit_terminal(self) -> None:
        fixture, request = _session_with_commit()
        repo = SessionRepository()
        repo._cache[fixture.hg_scene_id] = fixture  # type: ignore[attr-defined]
        kernel = DomainKernel.for_repository(repo)

        kernel.finalize_librarian_proposals(
            hg_scene_id=fixture.hg_scene_id,
            inference_id=request.librarian_inference_id,
            proposal_context_request={
                "request_id": request.request_id,
                "hg_round_id": request.hg_round_id,
                "turn_index": request.turn_index,
                "domain_commit_id": request.domain_commit_id,
            },
            proposal_result=None,
        )

        prepared = kernel.prepare_librarian_proposal_context(
            hg_scene_id=fixture.hg_scene_id,
            inference_id="inf-librarian-reentry",
            proposal_context_request={
                "request_id": "lpr-reentry",
                "hg_round_id": request.hg_round_id,
                "turn_index": request.turn_index,
                "domain_commit_id": request.domain_commit_id,
            },
        )
        self.assertTrue(prepared.get("skipped"))
        self.assertEqual(prepared.get("orchestration_status"), "already_terminal")

    def test_audit_log_persists_and_rehydrates(self) -> None:
        fixture, request = _session_with_commit(hg_scene_id="scene-persist-1")
        with tempfile.TemporaryDirectory() as tmp:
            repo = SessionRepository(tmp)
            repo._cache[fixture.hg_scene_id] = fixture  # type: ignore[attr-defined]
            kernel = DomainKernel.for_repository(repo)

            result = kernel.finalize_librarian_proposals(
                hg_scene_id=fixture.hg_scene_id,
                inference_id=request.librarian_inference_id,
                proposal_context_request={
                    "request_id": request.request_id,
                    "hg_round_id": request.hg_round_id,
                    "turn_index": request.turn_index,
                    "domain_commit_id": request.domain_commit_id,
                },
                proposal_result=_valid_proposal_result(request.domain_commit_id),
            )
            self.assertTrue(result.get("persisted"))

            reloaded = repo.open_session(fixture.hg_session_id)
            self.assertEqual(len(reloaded.librarian_proposal_audit_log), 1)
            self.assertEqual(
                reloaded.librarian_proposal_audit_log[0]["librarian_proposal_domain_commit_id"],
                request.domain_commit_id,
            )
            self.assertIsNotNone(find_terminal_audit_for_commit(reloaded, request.domain_commit_id))

    def test_finalize_persist_failure_raises_without_leaving_partial_audit(self) -> None:
        from unittest.mock import patch

        from domain_api.session_repository import PersistenceError

        fixture, request = _session_with_commit(hg_scene_id="scene-persist-fail")
        repo = SessionRepository()
        repo._cache[fixture.hg_scene_id] = fixture  # type: ignore[attr-defined]
        kernel = DomainKernel.for_repository(repo)

        with patch.object(repo._session_manager, "save_session", side_effect=OSError("disk full")):
            with self.assertRaises(PersistenceError):
                kernel.finalize_librarian_proposals(
                    hg_scene_id=fixture.hg_scene_id,
                    inference_id=request.librarian_inference_id,
                    proposal_context_request={
                        "request_id": request.request_id,
                        "hg_round_id": request.hg_round_id,
                        "turn_index": request.turn_index,
                        "domain_commit_id": request.domain_commit_id,
                    },
                    proposal_result=None,
                )

        self.assertEqual(len(fixture.librarian_proposal_audit_log), 0)
        self.assertIsNone(find_terminal_audit_for_commit(fixture, request.domain_commit_id))


if __name__ == "__main__":
    unittest.main()

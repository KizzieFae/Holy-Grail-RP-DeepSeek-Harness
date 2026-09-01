"""M10.1 session-local memory write and retrieval tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
for path in (_V2,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    PresentationRecordRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
    ValidationRequest,
)
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.session_repository import SessionRepository  # noqa: E402


def _private_whisper_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {
                "type": "action",
                "action": "whispers to Bob",
            },
            {
                "type": "speech",
                "dialogue": "Meet me at midnight.",
                "audibility": "private",
                "audience": [],
            },
        ],
        "motivation": {
            "goal": "conspire",
            "tactic": "whisper",
            "emotional_driver": "focused",
            "risk_level": "medium",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }


class SessionMemoryM10Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_two_character_session(self) -> str:
        info = self.kernel.create_session(cast=["Alice", "Bob", "Carol"])
        return info.hg_session_id

    def _start_round(self, hg_scene_id: str) -> str:
        return self.kernel.start_round(RoundStartRequest(hg_scene_id=hg_scene_id)).hg_round_id

    def _commit_alice(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
        move: dict | None = None,
        turn_index: int = 0,
    ) -> None:
        fixture = self.repo.require(hg_scene_id)
        response = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-alice",
                hg_scene_id=hg_scene_id,
                hg_round_id=hg_round_id,
                character_id="Alice",
                validated_move=move or PROTOTYPE_VALID_MOVE,
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=turn_index,
            )
        )
        self.assertTrue(response.committed, response.reason)

    def test_character_turn_memory_respects_perception(self) -> None:
        session_id = self._create_two_character_session()
        round_id = self._start_round(session_id)
        self._commit_alice(
            hg_scene_id=session_id,
            hg_round_id=round_id,
            move=_private_whisper_move(),
        )

        alice = self.repo.require(session_id).character_states["Alice"]
        bob = self.repo.require(session_id).character_states["Bob"]
        carol = self.repo.require(session_id).character_states["Carol"]

        bob_private = " ".join(bob.private_memories)
        carol_private = " ".join(carol.private_memories)
        self.assertIn("Observed:", bob_private)
        self.assertNotIn("Observed:", carol_private)
        self.assertTrue(alice.character_memory_summary)

    def test_user_turn_memory_only_for_perceiving_present_characters(self) -> None:
        session_id = self._create_two_character_session()
        fixture = self.repo.require(session_id)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.present_characters = ["Alice", "Bob"]
        self.repo.persist(fixture)

        self.kernel.record_user_turn(
            UserTurnRecordRequest.from_content(
                hg_session_id=session_id,
                content="Bob, meet me at midnight.",
                speaker="Traveler",
            )
        )

        reopened = self.repo.require(session_id)
        alice_hist = reopened.character_states["Alice"].relationships.get("Traveler", {}).get(
            "history", []
        )
        bob_hist = reopened.character_states["Bob"].relationships.get("Traveler", {}).get(
            "history", []
        )
        carol_hist = reopened.character_states["Carol"].relationships.get("Traveler", {}).get(
            "history", []
        )
        self.assertTrue(alice_hist)
        self.assertTrue(bob_hist)
        self.assertFalse(carol_hist)

    def test_memory_survives_repository_restart(self) -> None:
        session_id = self._create_two_character_session()
        round_id = self._start_round(session_id)
        self._commit_alice(hg_scene_id=session_id, hg_round_id=round_id)

        before = self.repo.require(session_id).character_states["Alice"].character_memory_summary
        self.assertTrue(before)

        self.repo.clear_cache()
        reopened = self.repo.open_session(session_id)
        after = reopened.character_states["Alice"].character_memory_summary
        self.assertEqual(before, after)

    def test_prepare_context_projects_derived_character_memory(self) -> None:
        session_id = self._create_two_character_session()
        round_id = self._start_round(session_id)
        self._commit_alice(hg_scene_id=session_id, hg_round_id=round_id)

        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-alice",
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        memory = [
            c for c in manifest.contributions if c.source_kind == "character_memory"
        ]
        self.assertEqual(len(memory), 1)
        self.assertEqual(memory[0].authority_class, "derived")
        self.assertIn("private interpretation summary", memory[0].content.lower())
        private = [c for c in manifest.contributions if c.source_kind == "character_private"]
        joined_private = private[0].content if private else ""
        self.assertNotIn("private interpretation summary", joined_private.lower())

    def test_character_memory_isolation_in_prepare_context(self) -> None:
        session_id = self._create_two_character_session()
        round_id = self._start_round(session_id)
        self._commit_alice(hg_scene_id=session_id, hg_round_id=round_id)

        alice_manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-alice",
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        bob_manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-bob",
                character_id="Bob",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        alice_memory = next(
            c for c in alice_manifest.contributions if c.source_kind == "character_memory"
        )
        bob_memory = next(
            c for c in bob_manifest.contributions if c.source_kind == "character_memory"
        )
        self.assertIn("has not spoken yet", alice_memory.content)
        self.assertNotIn("I did: nods thoughtfully", bob_memory.content)
        self.assertIn("Observed:", bob_memory.content)

    def test_rejected_validation_does_not_write_memory(self) -> None:
        session_id = self._create_two_character_session()
        round_id = self._start_round(session_id)
        fixture = self.repo.require(session_id)
        before_summary = list(fixture.character_states["Alice"].character_memory_summary)

        result = self.kernel.validate_move(
            ValidationRequest(
                inference_id="inf-reject",
                hg_scene_id=session_id,
                hg_round_id=round_id,
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
                proposed_move={
                    "move_schema_version": 2,
                    "beats": [],
                    "motivation": {
                        "goal": "x",
                        "tactic": "x",
                        "emotional_driver": "x",
                        "risk_level": "x",
                    },
                },
            )
        )
        self.assertFalse(result.accepted)
        after = self.repo.require(session_id).character_states["Alice"].character_memory_summary
        self.assertEqual(before_summary, after)

    def test_presentation_does_not_create_character_memory(self) -> None:
        session_id = self._create_two_character_session()
        round_id = self._start_round(session_id)
        self._commit_alice(hg_scene_id=session_id, hg_round_id=round_id)
        commit_id = self.repo.require(session_id).commit_ids[-1]

        before = list(self.repo.require(session_id).character_states["Alice"].private_memories)
        self.kernel.record_presentation(
            PresentationRecordRequest(
                hg_session_id=session_id,
                domain_commit_id=commit_id,
                hg_round_id=round_id,
                character_id="Alice",
                presentation_text="Alice nodded with narrator flourish.",
            )
        )
        after = self.repo.require(session_id).character_states["Alice"].private_memories
        self.assertEqual(before, after)

    def test_no_cross_session_memory_between_sessions(self) -> None:
        session_a = self.kernel.create_session(cast=["Alice", "Bob"]).hg_session_id
        round_a = self._start_round(session_a)
        self._commit_alice(hg_scene_id=session_a, hg_round_id=round_a)

        session_b = self.kernel.create_session(cast=["Alice", "Bob"]).hg_session_id
        alice_b = self.repo.require(session_b).character_states["Alice"]
        self.assertFalse(alice_b.character_memory_summary)
        self.assertFalse(alice_b.recent_observations)


if __name__ == "__main__":
    unittest.main()

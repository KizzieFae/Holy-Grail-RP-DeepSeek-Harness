"""M10.2 MemoryService and explicit memory_scope_id tests."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    ContextPrepareRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.memory_scope import new_memory_scope_id  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


class MemoryScopeM102Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(repository=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _create_kizzie_session(self, *, memory_scope_id: str | None = None) -> str:
        info = self.kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "minimal"},
            memory_scope_id=memory_scope_id,
        )
        self.assertTrue(info.memory_scope_id)
        return info.hg_session_id

    def _create_kizzie_willow_session(self, *, memory_scope_id: str | None = None) -> str:
        info = self.kernel.create_session(
            characters=["kizzie", "willow"],
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
            opening={"mode": "minimal"},
            memory_scope_id=memory_scope_id,
        )
        self.assertTrue(info.memory_scope_id)
        return info.hg_session_id

    def _record_user_message(self, session_id: str, content: str) -> None:
        self.kernel.record_user_turn(
            UserTurnRecordRequest(
                hg_session_id=session_id,
                content=content,
                speaker="Traveler",
            )
        )

    def _cross_scope_text(self, session_id: str, character_id: str = "Kizzie") -> str:
        round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=session_id)
        ).hg_round_id
        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=session_id,
                hg_round_id=round_id,
                inference_id="inf-kizzie",
                character_id=character_id,
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        cross = [
            c.content
            for c in manifest.contributions
            if c.source_kind == "character_memory"
            and c.provenance.get("memory_lane") == "cross_scope_relationship"
        ]
        return "\n".join(cross)

    def test_new_session_gets_unique_memory_scope_id(self) -> None:
        a = self.kernel.create_session(characters=["kizzie"]).memory_scope_id
        b = self.kernel.create_session(characters=["kizzie"]).memory_scope_id
        self.assertTrue(a)
        self.assertTrue(b)
        self.assertNotEqual(a, b)

    def test_explicit_memory_scope_is_preserved(self) -> None:
        scope = new_memory_scope_id()
        info = self.kernel.create_session(characters=["kizzie"], memory_scope_id=scope)
        self.assertEqual(info.memory_scope_id, scope)
        reopened = self.kernel.open_session(info.hg_session_id)
        self.assertEqual(reopened.memory_scope_id, scope)

    def test_default_isolation_between_sessions(self) -> None:
        session_a = self._create_kizzie_session()
        self._record_user_message(session_a, "Kizzie, remember our pact under the moon.")

        session_b = self._create_kizzie_session()
        cross = self._cross_scope_text(session_b)
        self.assertNotIn("pact under the moon", cross)

    def test_explicit_shared_scope_recall(self) -> None:
        scope = new_memory_scope_id()
        session_a = self._create_kizzie_session(memory_scope_id=scope)
        self._record_user_message(session_a, "Kizzie, remember our pact under the moon.")

        session_b = self._create_kizzie_session(memory_scope_id=scope)
        cross = self._cross_scope_text(session_b)
        self.assertIn("pact under the moon", cross)

    def test_same_cast_different_scopes_do_not_bleed(self) -> None:
        scope_a = new_memory_scope_id()
        scope_b = new_memory_scope_id()
        session_a = self._create_kizzie_willow_session(memory_scope_id=scope_a)
        self._record_user_message(session_a, "Hello both of you from the old timeline.")

        session_b = self._create_kizzie_willow_session(memory_scope_id=scope_b)
        cross_kizzie = self._cross_scope_text(session_b, "Kizzie")
        cross_willow = self._cross_scope_text(session_b, "Willow Reeves")
        self.assertNotIn("old timeline", cross_kizzie)
        self.assertNotIn("old timeline", cross_willow)

    def test_character_isolation_within_shared_scope(self) -> None:
        scope = new_memory_scope_id()
        session_a = self._create_kizzie_session(memory_scope_id=scope)
        fixture = self.repo.require(session_a)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.present_characters = ["Kizzie"]
        self.repo.persist(fixture)
        self._record_user_message(session_a, "Kizzie, this is only for you.")

        session_b = self._create_kizzie_willow_session(memory_scope_id=scope)
        kizzie_cross = self._cross_scope_text(session_b, "Kizzie")
        willow_cross = self._cross_scope_text(session_b, "Willow Reeves")
        self.assertIn("only for you", kizzie_cross)
        self.assertNotIn("only for you", willow_cross)

    def test_cross_scope_projection_is_idempotent(self) -> None:
        scope = new_memory_scope_id()
        session_id = self._create_kizzie_session(memory_scope_id=scope)
        self._record_user_message(session_id, "Kizzie, idempotency check message.")
        records_after_first = self.repo.memory_service.cross_scope_repo.list_records(
            scope,
            subject_character_file_id="kizzie",
        )
        self._record_user_message(session_id, "Kizzie, idempotency check message.")
        records_after_second = self.repo.memory_service.cross_scope_repo.list_records(
            scope,
            subject_character_file_id="kizzie",
        )
        self.assertEqual(len(records_after_first), len(records_after_second))

    def test_different_character_file_ids_remain_distinct(self) -> None:
        scope = new_memory_scope_id()
        session_a = self._create_kizzie_willow_session(memory_scope_id=scope)
        fixture = self.repo.require(session_a)
        assert fixture.manager.scene_state is not None
        fixture.manager.scene_state.present_characters = ["Kizzie", "Willow Reeves"]
        self.repo.persist(fixture)
        self._record_user_message(session_a, "Kizzie and Willow, shared greeting.")

        records_kizzie = self.repo.memory_service.cross_scope_repo.list_records(
            scope, subject_character_file_id="kizzie"
        )
        records_willow = self.repo.memory_service.cross_scope_repo.list_records(
            scope, subject_character_file_id="willow"
        )
        self.assertEqual(len(records_kizzie), 1)
        self.assertEqual(len(records_willow), 1)
        self.assertNotEqual(records_kizzie[0].memory_id, records_willow[0].memory_id)


if __name__ == "__main__":
    unittest.main()

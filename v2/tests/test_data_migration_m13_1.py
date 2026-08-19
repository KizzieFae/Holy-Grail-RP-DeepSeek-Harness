"""M13.1 HG_DATA_DIR migration and existing-session preservation tests."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.paths import (  # noqa: E402
    MIGRATION_MARKER_NAME,
    characters_data_dir,
    holy_grail_data_dir,
    sessions_data_dir,
)
from domain_api.contract import UserTurnRecordRequest  # noqa: E402
from domain_api.cross_scope_memory_repository import (  # noqa: E402
    CrossScopeMemoryRecord,
    CrossScopeMemoryRepository,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.memory_scope import new_memory_scope_id  # noqa: E402
from domain_api.scope_knowledge_repository import (  # noqa: E402
    LEARNED_WORLD_KNOWLEDGE,
    ScopeKnowledgeRecord,
    ScopeKnowledgeRepository,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


class DataMigrationM131Tests(unittest.TestCase):
    def setUp(self) -> None:
        self._root = tempfile.mkdtemp()
        self.legacy = Path(self._root) / "legacy"
        self.canonical = Path(self._root) / "canonical"
        self.legacy.mkdir(parents=True)
        self.canonical.mkdir(parents=True)
        self._legacy_patch = patch(
            "domain.data_migration.legacy_data_dir",
            return_value=self.legacy,
        )
        self._legacy_patch.start()

    def tearDown(self) -> None:
        self._legacy_patch.stop()
        shutil.rmtree(self._root, ignore_errors=True)
        for key in ("HG_DATA_DIR", "HG_SESSIONS_DIR"):
            os.environ.pop(key, None)

    def _with_canonical_env(self):
        return patch.dict(os.environ, {"HG_DATA_DIR": str(self.canonical)}, clear=False)

    def _run_migration(self):
        from domain.data_migration import run_data_migration

        with self._with_canonical_env():
            return run_data_migration()

    def _legacy_sessions_dir(self) -> Path:
        path = self.legacy / "sessions"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _seed_legacy_character(self, *, file_id: str = "kizzie", name: str = "Kizzie") -> None:
        cards = self.legacy / "autogen_characters"
        cards.mkdir(parents=True, exist_ok=True)
        card = {
            "name": name,
            "description": "Test card",
            "personality": "curious",
            "scenario": "workshop",
            "first_mes": "Hello.",
            "mes_example": "",
        }
        (cards / f"{file_id}.json").write_text(
            json.dumps(card), encoding="utf-8"
        )

    def _create_legacy_session(
        self,
        *,
        memory_scope_id: str | None = None,
        with_history: bool = True,
        card_name: str = "Kizzie",
    ) -> tuple[str, str]:
        self._seed_legacy_character(name=card_name)
        legacy_sessions = self._legacy_sessions_dir()
        repo = SessionRepository(legacy_sessions)
        kernel = DomainKernel(repository=repo)
        scope = memory_scope_id or new_memory_scope_id()
        info = kernel.create_session(
            characters=["kizzie"],
            opening={"mode": "minimal"},
            memory_scope_id=scope,
            characters_dir=self.legacy / "autogen_characters",
        )
        if with_history:
            kernel.record_user_turn(
                UserTurnRecordRequest(
                    hg_session_id=info.hg_session_id,
                    content="Legacy transcript line",
                    speaker="Traveler",
                )
            )
            session = repo.require(info.hg_session_id)
            append_history_entry(
                session.rp_history,
                kind="opening",
                content="Authored opening prose",
            )
            repo.persist(session)
        return info.hg_session_id, scope

    def _seed_cross_scope(self, sessions_dir: Path, scope_id: str) -> None:
        repo = CrossScopeMemoryRepository(sessions_dir / "_cross_scope_memory")
        repo.append_records(
            [
                CrossScopeMemoryRecord(
                    memory_id="mem-legacy-1",
                    memory_scope_id=scope_id,
                    subject_character_file_id="kizzie",
                    subject_display_name="Kizzie",
                    memory_kind="cross_scope_user_relationship",
                    content="Shared bond from legacy store",
                    source_session_id="legacy-session",
                )
            ]
        )

    def _seed_scope_knowledge(self, sessions_dir: Path, scope_id: str) -> None:
        repo = ScopeKnowledgeRepository(sessions_dir / "_scope_knowledge")
        repo.append_records(
            [
                ScopeKnowledgeRecord(
                    knowledge_id="know-legacy-1",
                    scope_id=scope_id,
                    knowledge_kind=LEARNED_WORLD_KNOWLEDGE,
                    content="Legacy learned fact",
                    source_session_id="legacy-session",
                )
            ]
        )

    def test_legacy_session_migrates_and_reopens(self) -> None:
        session_id, _scope = self._create_legacy_session()
        payload = self._run_migration()
        self.assertIn("sessions", payload["migrated_categories"])

        with self._with_canonical_env():
            repo = SessionRepository()
            reopened = repo.require(session_id)
        self.assertEqual(reopened.hg_session_id, session_id)

    def test_transcript_survives_migration(self) -> None:
        session_id, _scope = self._create_legacy_session(with_history=False)
        legacy_sessions = self._legacy_sessions_dir()
        repo = SessionRepository(legacy_sessions)
        kernel = DomainKernel(repository=repo)
        kernel.record_user_turn(
            UserTurnRecordRequest(
                hg_session_id=session_id,
                content="Legacy transcript line",
                speaker="Traveler",
            )
        )
        self._run_migration()
        with self._with_canonical_env():
            repo = SessionRepository()
            session = repo.require(session_id)
        user_entries = [item for item in session.rp_history if item.get("kind") == "user"]
        self.assertEqual(len(user_entries), 1)
        self.assertEqual(user_entries[0]["content"], "Legacy transcript line")

    def test_setup_snapshot_survives_migration(self) -> None:
        session_id, _scope = self._create_legacy_session()
        self._run_migration()
        with self._with_canonical_env():
            repo = SessionRepository()
            session = repo.require(session_id)
        self.assertIn("kizzie", session.setup_snapshot["character_cards"])
        self.assertEqual(
            session.setup_snapshot["character_cards"]["kizzie"]["name"],
            "Kizzie",
        )

    def test_cross_scope_memory_survives_migration(self) -> None:
        session_id, scope = self._create_legacy_session(with_history=False)
        self._seed_cross_scope(self._legacy_sessions_dir(), scope)
        self._run_migration()
        with self._with_canonical_env():
            repo = SessionRepository()
            records = repo.memory_service.cross_scope_repo.list_records(
                memory_scope_id=scope,
                subject_character_file_id="kizzie",
            )
        self.assertEqual(len(records), 1)
        self.assertIn("Shared bond", records[0].content)

    def test_scope_knowledge_survives_migration(self) -> None:
        session_id, scope = self._create_legacy_session(with_history=False)
        self._seed_scope_knowledge(self._legacy_sessions_dir(), scope)
        self._run_migration()
        with self._with_canonical_env():
            repo = SessionRepository()
            records = repo.scope_knowledge_repo.list_records(
                scope,
                knowledge_kinds={LEARNED_WORLD_KNOWLEDGE},
            )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].content, "Legacy learned fact")

    def test_opening_history_survives_migration(self) -> None:
        session_id, _scope = self._create_legacy_session()
        self._run_migration()
        with self._with_canonical_env():
            repo = SessionRepository()
            session = repo.require(session_id)
        opening_entries = [
            entry for entry in session.rp_history if entry.get("kind") == "opening"
        ]
        self.assertEqual(len(opening_entries), 1)
        self.assertEqual(opening_entries[0]["content"], "Authored opening prose")

    def test_migration_is_idempotent(self) -> None:
        self._create_legacy_session()
        first = self._run_migration()
        second = self._run_migration()
        self.assertEqual(first["migrated_categories"], second["migrated_categories"])
        marker = self.canonical / MIGRATION_MARKER_NAME
        self.assertTrue(marker.exists())

    def test_rerun_does_not_duplicate_sessions(self) -> None:
        session_id, _scope = self._create_legacy_session()
        self._run_migration()
        self._run_migration()
        with self._with_canonical_env():
            migrated_sessions = list((self.canonical / "sessions").glob("*.json"))
        session_files = [
            path for path in migrated_sessions if path.name != "_session_index.json"
        ]
        self.assertEqual(len(session_files), 1)
        self.assertEqual(session_files[0].stem, session_id)

    def test_new_sessions_write_to_canonical_only(self) -> None:
        self._seed_legacy_character()
        self._run_migration()
        with self._with_canonical_env():
            repo = SessionRepository()
            kernel = DomainKernel(repository=repo)
            info = kernel.create_session(
                characters=["kizzie"],
                opening={"mode": "minimal"},
            )
            canonical_file = self.canonical / "sessions" / f"{info.hg_session_id}.json"
            legacy_file = self.legacy / "sessions" / f"{info.hg_session_id}.json"
        self.assertTrue(canonical_file.exists())
        self.assertFalse(legacy_file.exists())

    def test_explicit_hg_data_dir(self) -> None:
        alt_root = Path(self._root) / "alt_data"
        alt_root.mkdir()
        (self.legacy / "autogen_characters").mkdir(parents=True, exist_ok=True)
        self._seed_legacy_character()
        with patch.dict(os.environ, {"HG_DATA_DIR": str(alt_root)}, clear=False):
            from domain.data_migration import run_data_migration

            payload = run_data_migration()
        self.assertEqual(payload["canonical_root"], str(alt_root))
        self.assertTrue((alt_root / "characters" / "kizzie.json").exists())

    def test_explicit_hg_sessions_dir_precedence(self) -> None:
        explicit_sessions = Path(self._root) / "explicit_sessions"
        explicit_sessions.mkdir()
        with patch.dict(
            os.environ,
            {
                "HG_DATA_DIR": str(self.canonical),
                "HG_SESSIONS_DIR": str(explicit_sessions),
            },
            clear=False,
        ):
            resolved = sessions_data_dir()
            repo = SessionRepository()
            kernel = DomainKernel(repository=repo)
            info = kernel.create_session(cast=["Alice", "Bob"])
        self.assertEqual(resolved, explicit_sessions)
        self.assertTrue((explicit_sessions / f"{info.hg_session_id}.json").exists())
        self.assertFalse((self.canonical / "sessions").exists())

    def test_live_card_changes_do_not_reinterpret_snapshot(self) -> None:
        session_id, _scope = self._create_legacy_session(
            with_history=False,
            card_name="Kizzie Legacy Name",
        )
        self._run_migration()
        with self._with_canonical_env():
            card_path = characters_data_dir() / "kizzie.json"
            card = json.loads(card_path.read_text(encoding="utf-8"))
            card["name"] = "Kizzie Live Override"
            card_path.write_text(json.dumps(card), encoding="utf-8")
            repo = SessionRepository()
            session = repo.require(session_id)
        self.assertEqual(
            session.setup_snapshot["character_cards"]["kizzie"]["name"],
            "Kizzie Legacy Name",
        )

    def test_clean_install_without_legacy(self) -> None:
        empty_legacy = Path(self._root) / "empty_legacy"
        empty_legacy.mkdir()
        with patch("domain.data_migration.legacy_data_dir", return_value=empty_legacy):
            payload = self._run_migration()
        self.assertNotIn("sessions", payload["migrated_categories"])
        marker = self.canonical / MIGRATION_MARKER_NAME
        self.assertTrue(marker.exists())
        with self._with_canonical_env():
            self.assertEqual(holy_grail_data_dir(), self.canonical)


if __name__ == "__main__":
    unittest.main()

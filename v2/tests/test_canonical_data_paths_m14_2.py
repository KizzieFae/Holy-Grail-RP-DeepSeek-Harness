"""M14.2 canonical data-path invariants (post migration-compatibility sunset)."""

from __future__ import annotations

import os
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

from domain import paths  # noqa: E402
from domain.paths import (  # noqa: E402
    characters_data_dir,
    holy_grail_data_dir,
    sessions_data_dir,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402


class CanonicalDataPathsM142Tests(unittest.TestCase):
    def tearDown(self) -> None:
        for key in ("HG_DATA_DIR", "HG_SESSIONS_DIR"):
            os.environ.pop(key, None)

    def test_default_data_root_is_repo_data(self) -> None:
        self.assertEqual(holy_grail_data_dir(), _ROOT / "data")

    def test_hg_data_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"HG_DATA_DIR": tmp}, clear=False):
                self.assertEqual(holy_grail_data_dir(), Path(tmp))
                self.assertEqual(characters_data_dir(), Path(tmp) / "characters")

    def test_hg_sessions_dir_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_data, tempfile.TemporaryDirectory() as tmp_sessions:
            with patch.dict(
                os.environ,
                {"HG_DATA_DIR": tmp_data, "HG_SESSIONS_DIR": tmp_sessions},
                clear=False,
            ):
                self.assertEqual(sessions_data_dir(), Path(tmp_sessions))
                repo = SessionRepository()
                kernel = DomainKernel(repository=repo)
                info = kernel.create_session(cast=["Alice", "Bob"])
            session_file = Path(tmp_sessions) / f"{info.hg_session_id}.json"
            self.assertTrue(session_file.is_file())
            self.assertFalse((Path(tmp_data) / "sessions").exists())

    def test_paths_module_has_no_autogen_rp_migration_hooks(self) -> None:
        source = Path(paths.__file__).read_text(encoding="utf-8")
        self.assertNotIn("autogen_rp", source)
        self.assertNotIn("legacy_data_dir", source)
        self.assertNotIn("ensure_data_migrated", source)
        self.assertNotIn("data_migration", source)

    def test_data_migration_module_removed(self) -> None:
        migration = _V2 / "domain" / "data_migration.py"
        self.assertFalse(migration.exists())

    def test_no_autogen_rp_in_production_path_resolution(self) -> None:
        proc_paths = [
            _V2 / "domain" / "paths.py",
            _V2 / "domain_api" / "session_repository.py",
        ]
        for path in proc_paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("autogen_rp", text, msg=str(path))


if __name__ == "__main__":
    unittest.main()

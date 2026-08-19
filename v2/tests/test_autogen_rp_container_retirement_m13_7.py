"""M13.7 final autogen_rp container retirement integrity tests."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))


class AutogenRpContainerRetirementM137Tests(unittest.TestCase):
    def test_no_tracked_autogen_rp_files(self) -> None:
        proc = subprocess.run(
            ["git", "ls-files", "autogen_rp"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(proc.stdout.strip(), "")

    def test_paths_module_has_no_legacy_migration_hooks(self) -> None:
        from domain.bootstrap import ensure_domain_paths

        ensure_domain_paths()
        from domain import paths as domain_paths

        source = Path(domain_paths.__file__).read_text(encoding="utf-8")
        self.assertNotIn("legacy_data_dir", source)
        self.assertNotIn("ensure_data_migrated", source)
        self.assertNotIn("data_migration", source)
        self.assertNotIn("autogen_rp", source)

    def test_root_gitignore_covers_local_legacy_tree(self) -> None:
        text = (_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("autogen_rp/", text)


if __name__ == "__main__":
    unittest.main()

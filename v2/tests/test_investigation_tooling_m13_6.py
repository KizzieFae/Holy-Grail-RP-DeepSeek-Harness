"""M13.6 investigation tooling rehome integrity tests."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_INV = _ROOT / "tools" / "investigation"
_LEGACY_SCRIPTS = _ROOT / "autogen_rp" / "python" / "scripts"


class InvestigationToolingM136Tests(unittest.TestCase):
    def test_investigation_dir_exists(self) -> None:
        self.assertTrue(_INV.is_dir())
        py_files = list(_INV.glob("*.py"))
        self.assertGreaterEqual(len(py_files), 35)

    def test_legacy_scripts_path_removed(self) -> None:
        self.assertFalse(_LEGACY_SCRIPTS.exists())

    def test_shared_repo_paths_module(self) -> None:
        helper = _ROOT / "tools" / "_repo_paths.py"
        self.assertTrue(helper.is_file())
        text = helper.read_text(encoding="utf-8")
        self.assertIn("FIXTURES_DIR", text)
        self.assertIn("VALIDATION_RUNS_ARCHIVE", text)

    def test_active_docs_moved_to_docs(self) -> None:
        for name in (
            "architecture.md",
            "audit-workflows.md",
            "rp-data-layout.md",
            "scene-grounding-layer.md",
        ):
            self.assertTrue((_ROOT / "docs" / name).is_file(), name)

    def test_compare_script_help(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(_INV / "compare_participation_calibration_ab.py"),
                "--help",
            ],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("baseline-summary", proc.stdout)


if __name__ == "__main__":
    unittest.main()

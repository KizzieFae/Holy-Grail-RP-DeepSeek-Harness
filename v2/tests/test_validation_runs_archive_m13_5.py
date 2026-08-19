"""M13.5 validation evidence archive integrity tests."""

from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_ARCHIVE = _ROOT / "governance" / "archive" / "validation-runs"
_LEGACY = _ROOT / "autogen_rp" / "python" / "validation_runs"
_FIXTURE = (
    _ROOT
    / "v2"
    / "domain"
    / "tests"
    / "fixtures"
    / "issue251"
    / "i251_doctrine_alignment.py"
)


class ValidationRunsArchiveM135Tests(unittest.TestCase):
    def test_archive_readme_exists(self) -> None:
        readme = _ARCHIVE / "README.md"
        self.assertTrue(readme.is_file())
        text = readme.read_text(encoding="utf-8")
        self.assertIn("autogen_rp/python/validation_runs", text)

    def test_legacy_validation_runs_path_removed(self) -> None:
        self.assertFalse(_LEGACY.exists())

    def test_archived_evidence_count(self) -> None:
        tracked = list(_ARCHIVE.rglob("*"))
        files = [p for p in tracked if p.is_file() and p.name != "README.md"]
        self.assertGreaterEqual(len(files), 75)

    def test_issue251_fixture_extracted_for_domain_tests(self) -> None:
        self.assertTrue(_FIXTURE.is_file())
        text = _FIXTURE.read_text(encoding="utf-8")
        self.assertIn("evaluate_doctrine_alignment", text)

    def test_archive_contains_plan_execution_snapshots(self) -> None:
        plan = _ARCHIVE / "plan_execution"
        self.assertTrue(plan.is_dir())
        json_files = list(plan.glob("*.json"))
        self.assertGreaterEqual(len(json_files), 5)

    def test_active_scripts_point_to_archive_helper(self) -> None:
        helper = _ROOT / "tools" / "_repo_paths.py"
        self.assertTrue(helper.is_file())
        text = helper.read_text(encoding="utf-8")
        self.assertIn("validation-runs", text)
        self.assertIn("VALIDATION_RUNS_ARCHIVE", text)


if __name__ == "__main__":
    unittest.main()

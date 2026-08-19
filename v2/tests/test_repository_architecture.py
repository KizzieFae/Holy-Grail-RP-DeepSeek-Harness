"""Permanent repository architecture invariants (fresh-start)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
_TOOLS = _ROOT / "tools"
_INV = _TOOLS / "investigation"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain import paths as domain_paths  # noqa: E402
from domain.paths import characters_data_dir, holy_grail_data_dir, sessions_data_dir  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402

_AUTOGEN_IMPORT_ROOTS = frozenset(
    {"autogen", "autogen_agentchat", "autogen_core", "autogen_ext", "autogenstudio", "pyautogen"}
)
_PRODUCTION_FORBIDDEN_TOKENS = (
    "legacy.v1_orchestration",
    "v1_orchestration",
    "turn_runner",
    "model_client",
    "python.rp_app",
    "rp_app",
)


def _iter_python_files(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in {".venv", ".pytest_cache", "governance"} for part in path.parts):
                continue
            out.append(path)
    return out


def _autogen_import_offenders(paths: list[Path]) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in _AUTOGEN_IMPORT_ROOTS:
                        offenders.append(f"{path.relative_to(_ROOT)}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in _AUTOGEN_IMPORT_ROOTS:
                    offenders.append(f"{path.relative_to(_ROOT)}: from {node.module}")
    return offenders


class RepositoryArchitectureTests(unittest.TestCase):
    def test_no_tracked_autogen_rp_files(self) -> None:
        proc = subprocess.run(
            ["git", "ls-files", "autogen_rp"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(proc.stdout.strip(), "")

    def test_local_autogen_rp_tree_absent(self) -> None:
        self.assertFalse((_ROOT / "autogen_rp").exists())

    def test_gitignore_does_not_hide_legacy_autogen_rp(self) -> None:
        text = (_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("autogen_rp/", text)

    def test_canonical_data_paths_module(self) -> None:
        source = Path(domain_paths.__file__).read_text(encoding="utf-8")
        self.assertNotIn("autogen_rp", source)
        self.assertNotIn("legacy_data_dir", source)
        self.assertNotIn("ensure_data_migrated", source)
        self.assertNotIn("data_migration", source)
        self.assertEqual(holy_grail_data_dir(), _ROOT / "data")

    def test_hg_data_dir_and_sessions_dir_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_data, tempfile.TemporaryDirectory() as tmp_sessions:
            with patch.dict(
                os.environ,
                {"HG_DATA_DIR": tmp_data, "HG_SESSIONS_DIR": tmp_sessions},
                clear=False,
            ):
                self.assertEqual(holy_grail_data_dir(), Path(tmp_data))
                self.assertEqual(characters_data_dir(), Path(tmp_data) / "characters")
                self.assertEqual(sessions_data_dir(), Path(tmp_sessions))
                repo = SessionRepository()
                kernel = DomainKernel(repository=repo)
                info = kernel.create_session(cast=["Alice", "Bob"])
            self.assertTrue((Path(tmp_sessions) / f"{info.hg_session_id}.json").is_file())

    def test_v2_production_has_no_autogen_imports(self) -> None:
        paths = _iter_python_files(_V2 / "domain_api", _V2 / "domain")
        self.assertEqual(_autogen_import_offenders(paths), [])

    def test_v2_production_has_no_legacy_orchestration_tokens(self) -> None:
        offenders: list[str] = []
        for tree_root in (_V2 / "domain_api", _V2 / "domain"):
            for path in tree_root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                for token in _PRODUCTION_FORBIDDEN_TOKENS:
                    if token in text:
                        offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_domain_modules_remain_framework_neutral(self) -> None:
        modules_dir = _V2 / "domain" / "modules"
        banned = ("autogen", "streamlit", "model_client", "turn_runner")
        offenders: list[str] = []
        for path in modules_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    if root in banned:
                        offenders.append(f"{path.relative_to(_ROOT)}: from {node.module}")
        self.assertEqual(offenders, [])

    def test_active_tooling_has_no_rp_app_or_legacy_path_constants(self) -> None:
        offenders: list[str] = []
        for path in _iter_python_files(_TOOLS / "investigation", _TOOLS / "maintenance", _TOOLS):
            if path.name == "_repo_paths.py" and path.parent == _TOOLS:
                text = path.read_text(encoding="utf-8")
            else:
                text = path.read_text(encoding="utf-8")
            for token in ("LEGACY_RP_APP", "autogen_rp/python/rp_app", "sys.path.insert(0, str(LEGACY"):
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_investigation_tooling_present(self) -> None:
        self.assertTrue(_INV.is_dir())
        py_files = [p for p in _INV.glob("*.py") if p.name != "_repo_paths.py"]
        self.assertGreaterEqual(len(py_files), 8)
        helper = _TOOLS / "_repo_paths.py"
        text = helper.read_text(encoding="utf-8")
        self.assertIn("FIXTURES_DIR", text)
        self.assertIn("resolve_rp_audits_dir", text)
        self.assertNotIn("LEGACY_RP_APP", text)

    def test_compare_script_help(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(_INV / "compare_participation_calibration_ab.py"), "--help"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("baseline-summary", proc.stdout)

    def test_current_bootstrap_docs_avoid_retired_runtime_paths(self) -> None:
        """Current-facing docs must not instruct readers to use deleted V1 runtime trees."""
        doc_paths = [
            _ROOT / "README.md",
            _ROOT / "AGENTS.md",
            _ROOT / "ARCHITECTURE_OVERVIEW.md",
            _ROOT / "MODULE_INDEX.md",
            _ROOT / "SCENARIO_VALIDATION_FRAMEWORK.md",
            _ROOT / "docs" / "architecture.md",
            _ROOT / "docs" / "repo-map.md",
            _ROOT / "docs" / "rp-data-layout.md",
            _ROOT / "docs" / "testing.md",
            _ROOT / "docs" / "core-operating-invariants.md",
            _ROOT / "v2" / "README.md",
        ]
        banned_substrings = (
            "autogen_rp/python/rp_app",
            "python/rp_app/",
            "scripts/run_scene_simulation_llm",
            "run_scene_simulation_llm.py",
            "LEGACY_RP_APP",
        )
        offenders: list[str] = []
        for path in doc_paths:
            text = path.read_text(encoding="utf-8")
            for token in banned_substrings:
                if token in text:
                    offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_no_legacy_migration_check_tool(self) -> None:
        self.assertFalse((_TOOLS / "maintenance" / "hg_data_migration_check.py").exists())


if __name__ == "__main__":
    unittest.main()

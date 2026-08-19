"""M12.5 — vendored AutoGen package removal proof tests."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
_PY = _ROOT / "autogen_rp" / "python"
_AUTOGEN_IMPORT_ROOTS = frozenset(
    {"autogen", "autogen_agentchat", "autogen_core", "autogen_ext", "autogenstudio", "pyautogen"}
)


def _iter_python_files(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in {"governance", ".venv", ".pytest_cache"} for part in path.parts):
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


class AutogenRemovalM125Tests(unittest.TestCase):
    def test_vendored_packages_directory_removed(self) -> None:
        self.assertFalse((_PY / "packages").exists())

    def test_v2_production_has_no_autogen_imports(self) -> None:
        paths = _iter_python_files(_V2 / "domain_api", _V2 / "domain", _V2 / "rp_runtime")
        self.assertEqual(_autogen_import_offenders(paths), [])

    def test_domain_tests_have_no_autogen_imports(self) -> None:
        paths = _iter_python_files(_V2 / "domain" / "tests")
        self.assertEqual(_autogen_import_offenders(paths), [])

    def test_domain_imports_in_isolated_subprocess_without_packages(self) -> None:
        root = str(_V2).replace("\\", "/")
        script = f"""
import sys
sys.path.insert(0, {root!r})
from domain.bootstrap import ensure_domain_paths
ensure_domain_paths()
from continuity_manager import ContinuityManager
from memory_layer.retrieval import build_episodic_prompt_snapshot
ContinuityManager()
print("ok")
"""
        env = os.environ.copy()
        env["PYTHONNOUSERSITE"] = "1"
        result = subprocess.run(
            [sys.executable, "-I", "-c", script],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        combined = (result.stdout or "") + (result.stderr or "")
        self.assertNotIn("autogen", combined.lower())


if __name__ == "__main__":
    unittest.main()

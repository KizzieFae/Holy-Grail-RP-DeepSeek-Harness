"""M12.4 — superseded V1 orchestration deletion proof tests."""

from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))


class OrchestrationDeletionM124Tests(unittest.TestCase):
    def test_v2_production_has_no_legacy_orchestration_imports(self) -> None:
        offenders: list[str] = []
        for tree_root in (_V2 / "domain_api", _V2 / "domain"):
            for path in tree_root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                for token in (
                    "legacy.v1_orchestration",
                    "v1_orchestration",
                    "turn_runner",
                    "model_client",
                    "python.rp_app",
                ):
                    if token in text and "test_" not in path.name:
                        offenders.append(f"{path.relative_to(_ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_v2_domain_has_no_legacy_imports(self) -> None:
        modules = _V2 / "domain"
        offenders: list[str] = []
        for path in modules.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("legacy"):
                        offenders.append(f"{path.relative_to(_ROOT)}: from {node.module}")
        self.assertEqual(offenders, [])

    def test_legacy_orchestration_tree_removed(self) -> None:
        self.assertFalse((_ROOT / "legacy" / "v1_orchestration").exists())

    def test_rp_app_namespace_removed(self) -> None:
        self.assertFalse((_ROOT / "autogen_rp" / "python" / "rp_app").exists())

    def test_no_turn_runner_in_production_tree(self) -> None:
        offenders: list[str] = []
        for tree in (_V2, _ROOT / "Launch-Holy-Grail-V2.bat"):
            if tree.is_file():
                text = tree.read_text(encoding="utf-8")
                if "turn_runner" in text:
                    offenders.append(str(tree.relative_to(_ROOT)))
                continue
            for path in tree.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix not in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".bat"}:
                    continue
                if "tests" in path.parts or "governance" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if "turn_runner" in text:
                    offenders.append(str(path.relative_to(_ROOT)))
        self.assertEqual(offenders, [])

    def test_domain_bootstrap_imports_continuity_manager(self) -> None:
        root = str(_ROOT).replace("\\", "/")
        script = f"""
import sys
sys.path.insert(0, {root!r})
sys.path.insert(0, {str(_V2).replace(chr(92), "/")!r})
from domain.bootstrap import ensure_domain_paths
ensure_domain_paths()
import continuity_manager
print("ok")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()

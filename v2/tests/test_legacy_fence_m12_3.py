"""M12.3 legacy V1 orchestration fence tests."""

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


class LegacyFenceM123Tests(unittest.TestCase):
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

    def test_rp_app_has_no_substantive_orchestration_modules(self) -> None:
        rp_app = _ROOT / "autogen_rp" / "python" / "rp_app"
        blocked = {
            "app.py",
            "turn_runner.py",
            "model_client.py",
            "character_loader.py",
        }
        present = [name for name in blocked if (rp_app / name).is_file()]
        self.assertEqual(present, [])

    def test_legacy_import_smoke_subprocess(self) -> None:
        root = str(_ROOT).replace("\\", "/")
        script = f"""
import sys
sys.path.insert(0, {root!r})
from legacy.v1_orchestration.bootstrap import ensure_v1_orchestration_paths
ensure_v1_orchestration_paths()
import turn_runner
import model_client
from character_loader import CharacterLoader
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

"""M12.2 framework-neutral domain library extraction tests."""

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

from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_manager import ContinuityManager  # noqa: E402
from scene_grounding import rebuild_scene_grounding_from_continuity  # noqa: E402
from memory_layer.retrieval import build_episodic_prompt_snapshot  # noqa: E402
from canonical_compile_adapters import resolve_adapter_row  # noqa: E402
from perception_audibility_structured import redact_structured_move_for_orchestration  # noqa: E402


class DomainLibraryM122Tests(unittest.TestCase):
    def test_representative_domain_imports(self) -> None:
        manager = ContinuityManager()
        self.assertIsNotNone(manager)
        self.assertIsNotNone(resolve_adapter_row)
        self.assertIsNotNone(redact_structured_move_for_orchestration)
        self.assertIsNotNone(rebuild_scene_grounding_from_continuity)

    def test_v2_production_does_not_reference_rp_app(self) -> None:
        domain_api = _V2 / "domain_api"
        offenders: list[str] = []
        for path in domain_api.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "rp_app" in text or "_RP_APP" in text:
                offenders.append(str(path.relative_to(_ROOT)))
        self.assertEqual(offenders, [])

    def test_domain_modules_no_autogen_streamlit_imports(self) -> None:
        modules_dir = _V2 / "domain" / "modules"
        banned = ("autogen", "streamlit", "model_client", "turn_runner")
        offenders: list[str] = []
        for path in modules_dir.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in banned:
                            offenders.append(f"{path.relative_to(_ROOT)}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    root = node.module.split(".")[0]
                    if root in banned:
                        offenders.append(
                            f"{path.relative_to(_ROOT)}: from {node.module} import ..."
                        )
        self.assertEqual(offenders, [])

    def test_import_domain_without_autogen_in_subprocess(self) -> None:
        root = str(_ROOT).replace("\\", "/")
        script = f"""
import sys
sys.path.insert(0, {root!r} + "/v2")
from domain.bootstrap import ensure_domain_paths
ensure_domain_paths()
from continuity_manager import ContinuityManager
from response_validation_parsing import parse_character_move
from memory_layer.retrieval import build_episodic_prompt_snapshot
from scene_grounding import rebuild_scene_grounding_from_continuity
m = ContinuityManager()
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

"""Cross-runtime parity for manifest projection policy (#134)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.manifest_projection_policy import (  # noqa: E402
    ALLOWED_SOURCE_KINDS,
    INFERENCE_KINDS,
)


def _export_python_policy() -> dict:
    return {
        "inference_kinds": sorted(ALLOWED_SOURCE_KINDS.keys()),
        "allowed_source_kinds": {
            kind: sorted(allowed) for kind, allowed in ALLOWED_SOURCE_KINDS.items()
        },
        "aliases": {
            "director_decision": "director_turn",
            "character_move": "character_turn",
        },
    }


def _export_javascript_policy() -> dict:
    script = _V2 / "rp_runtime" / "scripts" / "export-manifest-policy.mjs"
    result = subprocess.run(
        ["node", str(script)],
        check=True,
        capture_output=True,
        text=True,
        cwd=_V2 / "rp_runtime",
    )
    return json.loads(result.stdout)


class ManifestPolicyParityTests(unittest.TestCase):
    def test_inference_kind_vocabulary_matches(self) -> None:
        js_policy = _export_javascript_policy()
        self.assertEqual(sorted(INFERENCE_KINDS), js_policy["inference_kinds"])

    def test_allowed_source_kind_sets_match(self) -> None:
        py_policy = _export_python_policy()
        js_policy = _export_javascript_policy()
        self.assertEqual(py_policy, js_policy)


if __name__ == "__main__":
    unittest.main()

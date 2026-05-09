"""Shadow compare / parity helpers for character prompt bundles (Issue #166)."""

from __future__ import annotations

import difflib
import json
from typing import Any


def _deep_equal(
    a: Any,
    b: Any,
    path: str,
) -> tuple[bool, str]:
    if a is b:
        return True, ""
    if type(a) is not type(b):
        # Allow int/float interchange if numerically equal
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a == b:
                return True, ""
        return False, f"{path}: type mismatch {type(a)!r} vs {type(b)!r}"
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            missing = set(a.keys()) ^ set(b.keys())
            return False, f"{path}: dict key mismatch {missing!r}"
        for key in sorted(a.keys()):
            ok, msg = _deep_equal(a[key], b[key], f"{path}.{key}")
            if not ok:
                return False, msg
        return True, ""
    if isinstance(a, list):
        if len(a) != len(b):
            return False, f"{path}: list len {len(a)} vs {len(b)}"
        for i, (ai, bi) in enumerate(zip(a, b)):
            ok, msg = _deep_equal(ai, bi, f"{path}[{i}]")
            if not ok:
                return False, msg
        return True, ""
    if isinstance(a, str):
        if a != b:
            return False, f"{path}: string mismatch"
        return True, ""
    if a != b:
        return False, f"{path}: value mismatch {a!r} vs {b!r}"
    return True, ""


def compare_character_prompt_bundles(
    live: dict[str, Any],
    reconstructed: dict[str, Any],
) -> tuple[bool, str]:
    ok, msg = _deep_equal(live, reconstructed, "bundle")
    return ok, msg


def debug_bundle_mismatch_strings(
    live: dict[str, Any],
    reconstructed: dict[str, Any],
) -> str:
    """JSON-oriented diff aid after structured mismatch (order-stable for dicts)."""

    def _dump(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str)

    la = _dump(live)
    rb = _dump(reconstructed)
    diff = difflib.unified_diff(
        la.splitlines(),
        rb.splitlines(),
        fromfile="live",
        tofile="reconstructed",
        lineterm="",
    )
    return "\n".join(diff)

"""MODULE_INDEX.md: backticked *.py filenames under rp_app must exist on disk."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MODULE_INDEX = _ROOT / "MODULE_INDEX.md"
_SEARCH_PATHS = (
    _ROOT / "autogen_rp" / "python" / "rp_app",
    _ROOT / "legacy" / "v1_orchestration",
    _ROOT / "autogen_rp" / "python" / "scripts",
)


def test_module_index_python_references_exist() -> None:
    text = _MODULE_INDEX.read_text(encoding="utf-8")
    refs = set(re.findall(r"`([^`]+\.py)`", text))
    missing: list[str] = []
    for ref in sorted(refs):
        if "/" in ref or "\\" in ref:
            continue
        if ref.startswith(("tests/", "scripts/")):
            continue
        if any((p / ref).is_file() for p in _SEARCH_PATHS):
            continue
        missing.append(ref)
    assert not missing, "MODULE_INDEX.md references missing rp_app files: " + ", ".join(
        missing
    )

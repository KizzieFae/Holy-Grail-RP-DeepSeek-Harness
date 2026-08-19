"""Shared archive paths for investigation scripts (post-M13.5)."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Historical validation evidence (immutable archive; do not write new runs here).
VALIDATION_RUNS_ARCHIVE = _REPO_ROOT / "governance" / "archive" / "validation-runs"

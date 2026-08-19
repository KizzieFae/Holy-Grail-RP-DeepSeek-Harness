"""Neutral repository path helpers for Holy Grail tooling (post-M13.6)."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INVESTIGATION_DIR = REPO_ROOT / "tools" / "investigation"
MAINTENANCE_DIR = REPO_ROOT / "tools" / "maintenance"

_HG_DATA = os.environ.get("HG_DATA_DIR", "").strip()
DATA_DIR = Path(_HG_DATA) if _HG_DATA else REPO_ROOT / "data"
FIXTURES_DIR = DATA_DIR / "fixtures"

# Immutable historical validation evidence (M13.5 archive; read-only).
VALIDATION_RUNS_ARCHIVE = REPO_ROOT / "governance" / "archive" / "validation-runs"

# Local headless audit trees (gitignored; canonical under HG_DATA_DIR).
RP_AUDITS_DIR = DATA_DIR / "rp_audits"

# Historical V1 module root (deleted in M12; retained for transitional import attempts).
LEGACY_RP_APP = REPO_ROOT / "autogen_rp" / "python" / "rp_app"


def resolve_rp_audits_dir() -> Path:
    """Return the best available rp_audits directory for offline investigation."""
    if RP_AUDITS_DIR.is_dir():
        return RP_AUDITS_DIR
    legacy = LEGACY_RP_APP / "data" / "rp_audits"
    if legacy.is_dir():
        return legacy
    return RP_AUDITS_DIR


def fixture_path(*parts: str) -> Path:
    """Resolve tracked investigation fixtures under ``data/fixtures/``."""
    return FIXTURES_DIR.joinpath(*parts)


def resolve_data_path(relative: str) -> Path:
    """Resolve legacy repo-relative data paths to the canonical HG data root."""
    rel = relative.replace("\\", "/").lstrip("/")
    if rel.startswith("data/fixtures/"):
        return REPO_ROOT / rel
    if rel.startswith("data/"):
        tail = rel[5:]
        if tail.startswith("fixtures/"):
            return DATA_DIR / tail
        if tail.split("/", 1)[0].startswith("issue") and not (DATA_DIR / tail).exists():
            return FIXTURES_DIR / tail
        return DATA_DIR / tail
    if rel.startswith("fixtures/"):
        return DATA_DIR / rel
    if rel.split("/", 1)[0].startswith("issue"):
        return FIXTURES_DIR / rel
    return DATA_DIR / rel

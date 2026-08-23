"""Neutral repository path helpers for Holy Grail tooling."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INVESTIGATION_DIR = REPO_ROOT / "tools" / "investigation"
MAINTENANCE_DIR = REPO_ROOT / "tools" / "maintenance"

_HG_DATA = os.environ.get("HG_DATA_DIR", "").strip()
DATA_DIR = Path(_HG_DATA) if _HG_DATA else REPO_ROOT / "data"
FIXTURES_DIR = DATA_DIR / "fixtures"

# Local investigation output (gitignored under data/).
INVESTIGATION_RUNS_DIR = DATA_DIR / "investigation_runs"
VALIDATION_RUNS_ARCHIVE = INVESTIGATION_RUNS_DIR

# Local headless audit trees (gitignored; canonical under HG_DATA_DIR).
RP_AUDITS_DIR = DATA_DIR / "rp_audits"
EXECUTION_EVIDENCE_DIR = DATA_DIR / "execution_evidence"


def resolve_rp_audits_dir() -> Path:
    """Return the canonical rp_audits directory for offline investigation."""
    return RP_AUDITS_DIR


def fixture_path(*parts: str) -> Path:
    """Resolve tracked investigation fixtures under ``data/fixtures/``."""
    return FIXTURES_DIR.joinpath(*parts)


def resolve_data_path(relative: str) -> Path:
    """Resolve repo-relative data paths to the canonical HG data root."""
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

"""Repository data-path helpers for framework-neutral domain modules."""

from __future__ import annotations

import os
from pathlib import Path

MIGRATION_MARKER_NAME = ".hg_data_migration_v1.json"


def repo_root() -> Path:
    """Holy Grail repository root (parent of ``v2/``)."""
    return Path(__file__).resolve().parents[2]


def legacy_data_dir() -> Path:
    """Historical AutoGen-era data root (migration source only)."""
    return repo_root() / "autogen_rp" / "python" / "data"


def holy_grail_data_dir() -> Path:
    """Canonical Holy Grail product data root."""
    override = os.environ.get("HG_DATA_DIR", "").strip()
    if override:
        return Path(override)
    return repo_root() / "data"


def ensure_data_migrated() -> None:
    """One-time legacy → canonical data migration when required."""
    from domain.data_migration import run_data_migration

    run_data_migration()


def characters_data_dir() -> Path:
    ensure_data_migrated()
    return holy_grail_data_dir() / "characters"


def scene_templates_data_dir() -> Path:
    ensure_data_migrated()
    return holy_grail_data_dir() / "scene_templates"


def fixtures_data_dir() -> Path:
    ensure_data_migrated()
    return holy_grail_data_dir() / "fixtures"


def sessions_data_dir() -> Path:
    explicit = os.environ.get("HG_SESSIONS_DIR", "").strip()
    if explicit:
        return Path(explicit)
    ensure_data_migrated()
    return holy_grail_data_dir() / "sessions"


def autogen_python_data_dir() -> Path:
    """Deprecated alias for legacy migration source path."""
    return legacy_data_dir()

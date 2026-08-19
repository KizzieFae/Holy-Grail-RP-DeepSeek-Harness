"""Repository data-path helpers for framework-neutral domain modules."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Holy Grail repository root (parent of ``v2/``)."""
    return Path(__file__).resolve().parents[2]


def holy_grail_data_dir() -> Path:
    """Canonical Holy Grail product data root."""
    override = os.environ.get("HG_DATA_DIR", "").strip()
    if override:
        return Path(override)
    return repo_root() / "data"


def characters_data_dir() -> Path:
    return holy_grail_data_dir() / "characters"


def scene_templates_data_dir() -> Path:
    return holy_grail_data_dir() / "scene_templates"


def fixtures_data_dir() -> Path:
    return holy_grail_data_dir() / "fixtures"


def sessions_data_dir() -> Path:
    explicit = os.environ.get("HG_SESSIONS_DIR", "").strip()
    if explicit:
        return Path(explicit)
    return holy_grail_data_dir() / "sessions"

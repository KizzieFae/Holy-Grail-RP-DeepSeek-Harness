"""Repository data-path helpers for framework-neutral domain modules."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Holy Grail repository root (parent of ``v2/``)."""
    return Path(__file__).resolve().parents[2]


def autogen_python_data_dir() -> Path:
    return repo_root() / "autogen_rp" / "python" / "data"


def characters_data_dir() -> Path:
    return autogen_python_data_dir() / "autogen_characters"


def scene_templates_data_dir() -> Path:
    return autogen_python_data_dir() / "scene_templates"


def sessions_data_dir() -> Path:
    return autogen_python_data_dir() / "sessions"

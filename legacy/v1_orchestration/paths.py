"""Path helpers for fenced V1 orchestration (repo-stable anchors)."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def autogen_python_dir() -> Path:
    """``autogen_rp/python`` — historical path anchor for audits and callouts."""
    return repo_root() / "autogen_rp" / "python"


def orchestration_data_dir() -> Path:
    """Runtime-local data shipped with fenced orchestration (e.g. rp_audits)."""
    return Path(__file__).resolve().parent / "data"

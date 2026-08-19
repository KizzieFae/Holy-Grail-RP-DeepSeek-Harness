"""Re-export shared tooling paths for investigation scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PARENT_MODULE = Path(__file__).resolve().parents[1] / "_repo_paths.py"
_spec = importlib.util.spec_from_file_location("hg_tools_repo_paths", _PARENT_MODULE)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

REPO_ROOT = _mod.REPO_ROOT
INVESTIGATION_DIR = _mod.INVESTIGATION_DIR
MAINTENANCE_DIR = _mod.MAINTENANCE_DIR
DATA_DIR = _mod.DATA_DIR
FIXTURES_DIR = _mod.FIXTURES_DIR
VALIDATION_RUNS_ARCHIVE = _mod.VALIDATION_RUNS_ARCHIVE
RP_AUDITS_DIR = _mod.RP_AUDITS_DIR
LEGACY_RP_APP = _mod.LEGACY_RP_APP
resolve_rp_audits_dir = _mod.resolve_rp_audits_dir
fixture_path = _mod.fixture_path
resolve_data_path = _mod.resolve_data_path

__all__ = [
    "DATA_DIR",
    "FIXTURES_DIR",
    "INVESTIGATION_DIR",
    "LEGACY_RP_APP",
    "MAINTENANCE_DIR",
    "REPO_ROOT",
    "RP_AUDITS_DIR",
    "VALIDATION_RUNS_ARCHIVE",
    "fixture_path",
    "resolve_data_path",
    "resolve_rp_audits_dir",
]

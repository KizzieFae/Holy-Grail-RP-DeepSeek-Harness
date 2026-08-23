"""Re-export shared path helpers from ``tools/_repo_paths.py``."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_parent = Path(__file__).resolve().parents[1] / "_repo_paths.py"
_spec = importlib.util.spec_from_file_location("tools__repo_paths", _parent)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

DATA_DIR = _mod.DATA_DIR
FIXTURES_DIR = _mod.FIXTURES_DIR
INVESTIGATION_DIR = _mod.INVESTIGATION_DIR
INVESTIGATION_RUNS_DIR = _mod.INVESTIGATION_RUNS_DIR
MAINTENANCE_DIR = _mod.MAINTENANCE_DIR
REPO_ROOT = _mod.REPO_ROOT
RP_AUDITS_DIR = _mod.RP_AUDITS_DIR
VALIDATION_RUNS_ARCHIVE = _mod.VALIDATION_RUNS_ARCHIVE
fixture_path = _mod.fixture_path
resolve_data_path = _mod.resolve_data_path
resolve_rp_audits_dir = _mod.resolve_rp_audits_dir
EXECUTION_EVIDENCE_DIR = _mod.EXECUTION_EVIDENCE_DIR

__all__ = [
    "DATA_DIR",
    "FIXTURES_DIR",
    "INVESTIGATION_DIR",
    "INVESTIGATION_RUNS_DIR",
    "MAINTENANCE_DIR",
    "REPO_ROOT",
    "RP_AUDITS_DIR",
    "VALIDATION_RUNS_ARCHIVE",
    "fixture_path",
    "resolve_data_path",
    "resolve_rp_audits_dir",
]

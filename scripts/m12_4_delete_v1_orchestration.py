#!/usr/bin/env python3
"""M12.4 — delete superseded V1 orchestration runtime (legacy fence + rp_app shims)."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_ORCH = ROOT / "legacy" / "v1_orchestration"
RP_APP = ROOT / "autogen_rp" / "python" / "rp_app"
ARCHIVE = ROOT / "governance" / "archive" / "v1-runtime"
AUDIT_DEST = ROOT / "autogen_rp" / "python" / "data" / "rp_audits"
TESTS = ROOT / "autogen_rp" / "python" / "tests"

ORCH_TEST_PATTERNS = [
    r"\bturn_runner",
    r"\bfrom app import",
    r"\bimport app\b",
    r"model_client",
    r"headless_scene_simulation",
    r"headless_session_prepare",
    r"headless_turn_runner",
    r"app_turn_director",
    r"app_turn_rendering",
    r"app_turn_prompting",
    r"semantic_validation",
    r"create_director_agent",
    r"CharacterLoader",
    r"run_character_turns",
    r"bootstrap_composition",
    r"scene_start_bootstrap",
    r"prepare_headless",
    r"turn_runner_character_attempt",
    r"user_callout_review",
]


def _archive_evidence() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for name in ("ARCHITECTURE.md", "AUDIT_DOCUMENTATION.md", "README.md"):
        src = LEGACY_ORCH / name
        if src.is_file():
            shutil.copy2(src, ARCHIVE / name)
    audit_src = LEGACY_ORCH / "data" / "rp_audits"
    if audit_src.is_dir():
        if AUDIT_DEST.exists():
            shutil.rmtree(AUDIT_DEST)
        shutil.copytree(audit_src, AUDIT_DEST)
    prog_src = LEGACY_ORCH / "data" / "progression_simulation_scenarios"
    prog_dest = ROOT / "autogen_rp" / "python" / "data" / "progression_simulation_scenarios"
    if prog_src.is_dir() and not prog_dest.exists():
        shutil.copytree(prog_src, prog_dest)


def _delete_legacy_orchestration() -> int:
    if not LEGACY_ORCH.is_dir():
        return 0
    count = sum(1 for _ in LEGACY_ORCH.rglob("*") if _.is_file())
    shutil.rmtree(LEGACY_ORCH)
    return count


def _delete_rp_app_shims() -> int:
    removed = 0
    if not RP_APP.is_dir():
        return 0
    for path in sorted(RP_APP.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        path.unlink()
        removed += 1
    # Remove empty nested dirs (e.g. memory_layer) after shim removal
    for path in sorted(RP_APP.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return removed


def _orchestration_test_files() -> list[Path]:
    delete: list[Path] = []
    for path in sorted(TESTS.glob("test_*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(re.search(pat, text) for pat in ORCH_TEST_PATTERNS):
            delete.append(path)
    # Explicit orchestration-only tests by name
    for name in (
        "test_turn_runner_updates.py",
        "test_turn_runner_character_attempt_parity.py",
        "test_turn_runner_continuation_override.py",
        "test_turn_runner_ignore_director_end_round.py",
        "test_turn_runner_issue213_pre_turn_ordering.py",
        "test_orchestration_helpers.py",
        "test_rp_app_smoke_flows.py",
        "test_module_index_references.py",
        "test_issue174_app_glue_and_import_parity.py",
    ):
        p = TESTS / name
        if p.is_file() and p not in delete:
            delete.append(p)
    return delete


def _delete_orchestration_tests() -> int:
    removed = 0
    for path in _orchestration_test_files():
        path.unlink()
        removed += 1
    return removed


def main() -> int:
    print("M12.4: archiving evidence...")
    _archive_evidence()
    print("M12.4: deleting legacy/v1_orchestration...")
    legacy_files = _delete_legacy_orchestration()
    print(f"  removed {legacy_files} files from legacy tree")
    print("M12.4: deleting rp_app domain shims...")
    shim_files = _delete_rp_app_shims()
    print(f"  removed {shim_files} shim modules")
    print("M12.4: deleting orchestration tests...")
    test_files = _delete_orchestration_tests()
    print(f"  removed {test_files} test modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

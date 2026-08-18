#!/usr/bin/env python3
"""M12.5 — remove vendored AutoGen packages and obsolete framework dependencies."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "autogen_rp" / "python"

DELETE_DIRS = [
    PY / "packages",
    PY / "samples",
    PY / "docs",
    PY / "templates",
    PY / "rp_app",
]

DELETE_FILES = [
    PY / "deepseek_example.py",
    PY / "test_deepseek.py",
    PY / "fixup_generated_files.py",
    PY / "run_task_in_pkgs_if_exist.py",
    PY / "check_md_code_blocks.py",
    PY / "shared_tasks.toml",
    PY / "uv.lock",
]

AUTOGEN_EXPERIMENT_SCRIPTS = [
    PY / "validation_runs/issue249/run_i249_proposal_schema_experiment.py",
    PY / "validation_runs/issue249/run_i249_participation_boundary_b_experiment.py",
    PY / "validation_runs/issue249/run_i249_participation_boundary_b_clean_experiment.py",
    PY / "validation_runs/issue249/run_i249_proposal_schema_generalization.py",
    PY / "validation_runs/issue251/run_gm3_exact_replay.py",
    PY / "validation_runs/issue251/run_i251_anchor_guard_experiment.py",
]


def _rm_tree(path: Path) -> int:
    if not path.exists():
        return 0
    count = sum(1 for _ in path.rglob("*") if _.is_file())
    shutil.rmtree(path)
    return count


def main() -> int:
    removed_files = 0
    for d in DELETE_DIRS:
        n = _rm_tree(d)
        print(f"removed dir {d.relative_to(ROOT)} ({n} files)")
        removed_files += n
    for f in DELETE_FILES:
        if f.is_file():
            f.unlink()
            removed_files += 1
            print(f"removed file {f.relative_to(ROOT)}")
    for f in AUTOGEN_EXPERIMENT_SCRIPTS:
        if f.is_file():
            f.unlink()
            removed_files += 1
            print(f"removed experiment {f.relative_to(ROOT)}")
    print(f"total files removed: {removed_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

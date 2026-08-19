#!/usr/bin/env python3
"""Run all #227 cohesion slate audited sessions sequentially."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE

PY_ROOT = REPO_ROOT
RUNS = [
    (
        "household_baseline",
        "investigate_i227_cohesion_household_baseline",
        12,
        str(DATA_DIR / "issue227/cohesion_slate/household_probe_schedule_v1.json"),
    ),
    (
        "household_flex",
        "investigate_i227_cohesion_household_selective_flex",
        12,
        str(DATA_DIR / "issue227/cohesion_slate/household_probe_schedule_v1.json"),
    ),
    (
        "arkham_baseline",
        "investigate_i227_cohesion_arkham_baseline",
        14,
        str(DATA_DIR / "issue227/cohesion_slate/arkham_probe_schedule_v1.json"),
    ),
    (
        "arkham_flex",
        "investigate_i227_cohesion_arkham_selective_flex",
        14,
        str(DATA_DIR / "issue227/cohesion_slate/arkham_probe_schedule_v1.json"),
    ),
    (
        "apartment_baseline",
        "investigate_i227_cohesion_apartment_baseline",
        16,
        str(DATA_DIR / "issue227/cohesion_slate/apartment_probe_schedule_v1.json"),
    ),
    (
        "apartment_flex",
        "investigate_i227_cohesion_apartment_selective_flex",
        16,
        str(DATA_DIR / "issue227/cohesion_slate/apartment_probe_schedule_v1.json"),
    ),
]


def main() -> None:
    log_dir = VALIDATION_RUNS_ARCHIVE / "cohesion_slate"
    log_dir.mkdir(parents=True, exist_ok=True)
    for label, scenario, turns, schedule in RUNS:
        log_path = log_dir / f"run_{label}.log"
        cmd = [
            sys.executable,
            "scripts/run_scene_simulation_llm.py",
            "--scenario",
            scenario,
            "--audit",
            "--turns",
            str(turns),
            "--ignore-end-round",
            "--user-trigger-schedule",
            schedule,
        ]
        print(f"=== {label} ===", flush=True)
        with log_path.open("w", encoding="utf-8") as log:
            proc = subprocess.run(
                cmd,
                cwd=PY_ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        print(f"{label} exit={proc.returncode} log={log_path}", flush=True)
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()

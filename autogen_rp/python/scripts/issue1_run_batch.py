#!/usr/bin/env python3
"""Run N audited Issue #1 simulations; print session numbers (stochastic N on priming+probe)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--turns", type=int, default=20)
    args = p.parse_args()

    sched = _PY_ROOT / "rp_app/data/issue1_user_trigger_schedule.json"
    for i in range(args.runs):
        cmd = [
            sys.executable,
            str(_PY_ROOT / "scripts/run_scene_simulation_llm.py"),
            "--scenario",
            "issue1_identity_bleed_3char_cafeteria",
            "--audit",
            "--turns",
            str(args.turns),
            "--user-trigger-schedule",
            str(sched),
        ]
        print(f"--- run {i + 1}/{args.runs} ---", flush=True)
        r = subprocess.run(cmd, cwd=str(_PY_ROOT), check=False)
        if r.returncode != 0:
            print(f"run {i + 1} failed exit {r.returncode}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()

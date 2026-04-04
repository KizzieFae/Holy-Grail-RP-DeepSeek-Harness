#!/usr/bin/env python3
"""Second-pass arch-quality batch: baseline vs A1/B/C × scenarios × reps (metrics JSON only).

Run from autogen_rp/python. Requires DEEPSEEK_API_KEY. Does not change runtime code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_PY = Path(__file__).resolve().parents[1]
_OUT = _PY / "runs" / "arch_quality_r2"

SCENARIOS: list[tuple[str, int]] = [
    ("conflict_3char", 4),
    ("arrival_setup", 3),
    ("long_session", 8),
]
COMPARISONS: list[tuple[str, str, str]] = [
    ("A1", "baseline", "a1"),
    ("B", "baseline", "b"),
    ("C", "baseline", "c"),
]
REPS = (1, 2, 3)


def main() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    _OUT.mkdir(parents=True, exist_ok=True)
    sim = _PY / "scripts" / "run_scene_simulation_llm.py"
    total = len(COMPARISONS) * len(SCENARIOS) * len(REPS) * 2
    n = 0
    for comp, vb, vt in COMPARISONS:
        d = _OUT / comp
        d.mkdir(parents=True, exist_ok=True)
        for scen, turns in SCENARIOS:
            for rep in REPS:
                for var in (vb, vt):
                    n += 1
                    out = d / f"{scen}_{var}_rep{rep}.json"
                    print(f"[{n}/{total}] {comp} {scen} {var} rep{rep} -> {out.name}")
                    r = subprocess.run(
                        [
                            sys.executable,
                            str(sim),
                            "--scenario",
                            scen,
                            "--turns",
                            str(turns),
                            "--arch-quality-variant",
                            var,
                            "--metrics-out",
                            str(out),
                        ],
                        cwd=str(_PY),
                    )
                    if r.returncode != 0:
                        print(f"FAILED {out}", file=sys.stderr)
                        sys.exit(r.returncode)
    print("Done. Aggregate with scripts/aggregate_arch_quality_r2.py or inspect JSON under", _OUT)


if __name__ == "__main__":
    main()

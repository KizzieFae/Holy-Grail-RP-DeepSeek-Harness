"""Baseline vs arch-quality C only: paired runs for override quality phase."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PY = Path(__file__).resolve().parents[1]
_OUT = _PY / "runs" / "arch_quality_override_c"
_SIM = _PY / "scripts" / "run_scene_simulation_llm.py"

# (scenario_id, turns, pairs) — pairs = baseline+C per index 1..pairs
RUNS: list[tuple[str, int, int]] = [
    ("conflict_3char", 4, 4),
    ("arkham_multi_character_stress", 3, 4),
    ("long_session", 8, 3),
]


def main() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    _OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    total = sum(p * 2 for _, _, p in RUNS)
    for scen, turns, pairs in RUNS:
        d = _OUT / scen
        d.mkdir(parents=True, exist_ok=True)
        for rep in range(1, pairs + 1):
            for var in ("baseline", "c"):
                n += 1
                out = d / f"{var}_rep{rep}.json"
                log = d / f"{var}_rep{rep}.md"
                print(f"[{n}/{total}] {scen} {var} rep{rep} turns={turns}")
                r = subprocess.run(
                    [
                        sys.executable,
                        str(_SIM),
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
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                log.write_text(r.stdout or "", encoding="utf-8")
                if r.returncode != 0:
                    print(r.stderr, file=sys.stderr)
                    sys.exit(r.returncode)
    print("Done ->", _OUT)


if __name__ == "__main__":
    main()

"""One-off batch runner for Progression Stress Audit (writes under this directory)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT.parent.parent  # autogen_rp/python
SIM = PY / "scripts" / "run_scene_simulation_llm.py"
REPLAY = PY / "scripts" / "run_progression_stress_audit_replay.py"
AUDIT_BASE = PY / "rp_app" / "data" / "rp_audits"

RUNS: list[tuple[str, bool, int | None]] = [
    ("arrival_setup", True, None),
    ("emotional_loop_2char", True, None),
    ("emotional_loop_2char", False, None),
    ("conflict_3char", True, None),
    ("strong_user_steer", True, None),
    ("strong_user_steer", False, None),
    ("recovery_derail", True, None),
    ("recovery_derail", False, None),
    ("long_session", True, 10),
    ("willow_dorm_binding_stress", True, 8),
    ("arkham_multi_character_stress", True, 8),
    ("arkham_multi_character_stress_long", True, 8),
    ("passive_observer", True, None),
]


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    for scenario, enf_on, turns in RUNS:
        tag = f"{scenario}_enf{'on' if enf_on else 'off'}"
        if turns is not None:
            tag += f"_t{turns}"
        out = ROOT / tag
        out.mkdir(parents=True, exist_ok=True)
        metrics = out / "metrics.json"
        logf = out / "run.log"
        cmd = [
            sys.executable,
            str(SIM),
            "--scenario",
            scenario,
            "--audit",
            "--metrics-out",
            str(metrics),
        ]
        if not enf_on:
            cmd.append("--no-progression-enforcement")
        if turns is not None:
            cmd.extend(["--turns", str(turns)])

        print("RUN", " ".join(cmd), flush=True)
        with open(logf, "w", encoding="utf-8") as lf:
            r = subprocess.run(
                cmd,
                cwd=str(PY),
                stdout=lf,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if r.returncode != 0:
            print(f"FAIL exit={r.returncode} {tag}", flush=True)
            index.append({"tag": tag, "error": f"exit {r.returncode}"})
            continue

        text = logf.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"\* \*\*Audit session:\*\* (\d+)", text)
        session_num = int(m.group(1)) if m else None
        session_dir = AUDIT_BASE / f"session_{session_num:03d}" if session_num else None

        replay_out = out / "replay_out"
        if session_dir and session_dir.is_dir():
            rr = subprocess.run(
                [
                    sys.executable,
                    str(REPLAY),
                    "--session-dir",
                    str(session_dir),
                    "--structured-eval",
                    str(metrics),
                    "--log",
                    str(logf),
                    "--out-dir",
                    str(replay_out),
                ],
                cwd=str(PY),
                capture_output=True,
                text=True,
            )
            if rr.returncode != 0:
                print(f"REPLAY FAIL {tag}", rr.stderr, flush=True)
        index.append(
            {
                "tag": tag,
                "scenario": scenario,
                "enforcement_on": enf_on,
                "turns_cap": turns,
                "session_number": session_num,
                "session_dir": str(session_dir) if session_dir else None,
            }
        )

    (ROOT / "batch_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Wrote batch_index.json", flush=True)


if __name__ == "__main__":
    main()

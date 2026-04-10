#!/usr/bin/env python3
"""Run Issue #29 scenario suite (audit + deep sim) and write machine-lane JSON summary.

Requires DEEPSEEK_API_KEY. Does not interpret results.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from issue29_investigation import (  # noqa: E402
    analyze_issue29_session,
    parse_audit_session_from_stdout,
)

SCENARIOS: list[tuple[str, str, int]] = [
    (
        "investigate_i29_negotiation_harley_kizzie_ayame",
        "data/issue29_investigation_schedules/negotiation_harley_kizzie_ayame.json",
        25,
    ),
    (
        "investigate_i29_transformation_persistence",
        "data/issue29_investigation_schedules/transformation_persistence.json",
        25,
    ),
    (
        "investigate_i29_object_continuity",
        "data/issue29_investigation_schedules/object_continuity.json",
        25,
    ),
    (
        "investigate_i29_instruction_retention",
        "data/issue29_investigation_schedules/instruction_retention.json",
        25,
    ),
    (
        "investigate_i29_cross_scene_carry",
        "data/issue29_investigation_schedules/cross_scene_50.json",
        50,
    ),
    (
        "investigate_i29_multi_thread_dialogue",
        "data/issue29_investigation_schedules/multi_thread.json",
        25,
    ),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        type=Path,
        default=_PY_ROOT / "runs" / "issue29_suite_results.json",
        help="Write combined results JSON here",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Run only first N scenarios (0 = all)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only",
    )
    args = ap.parse_args()

    if not args.dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    os.chdir(_PY_ROOT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    to_run = SCENARIOS[: args.limit] if args.limit > 0 else SCENARIOS

    for sid, sched, turns in to_run:
        cmd = [
            sys.executable,
            "scripts/run_scene_simulation_llm.py",
            "--scenario",
            sid,
            "--audit",
            "--issue29-long-run-harness",
            "--turns",
            str(turns),
            "--user-trigger-schedule",
            sched,
        ]
        if args.dry_run:
            print(" ".join(cmd))
            continue
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
        session_num = parse_audit_session_from_stdout(blob)
        audit_base = _RP_APP / "data" / "rp_audits"
        session_dir = (
            audit_base / f"session_{session_num}" if session_num is not None else None
        )
        analysis: dict | None = None
        if session_dir and session_dir.is_dir():
            analysis = analyze_issue29_session(session_dir, sid)
        results.append(
            {
                "scenario_id": sid,
                "exit_code": proc.returncode,
                "audit_session_number": session_num,
                "session_dir": str(session_dir) if session_dir else None,
                "command": cmd,
                "issue29_long_run_harness": True,
                "analysis": analysis,
            }
        )

    if not args.dry_run:
        args.out.write_text(
            json.dumps(results, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

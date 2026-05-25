#!/usr/bin/env python3
"""Issue #251 — cohort D scenario matrix (baseline vs treatment)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
_PY = Path(__file__).resolve().parents[2]
PLAN = OUT_DIR / "i251_scenario_matrix_plan.json"
RUNNER = _PY / "scripts" / "run_scene_simulation_llm.py"


def load_plan() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def run_scenario(
    *,
    scenario_id: str,
    arm: str,
    max_turns: int,
    dry_run: bool,
) -> dict:
    topology = (
        "v1_next7"
        if arm == "baseline"
        else "v1_next7_issue251_awareness_clean"
    )
    run_dir = OUT_DIR / "runs" / arm / scenario_id
    metrics_out = run_dir / "structured_eval.json"
    if dry_run:
        return {
            "scenario_id": scenario_id,
            "arm": arm,
            "topology": topology,
            "max_turns": max_turns,
            "dry_run": True,
            "metrics_out": str(metrics_out),
        }
    run_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["RP_ISSUE240_PROMPT_TOPOLOGY"] = topology
    cmd = [
        sys.executable,
        str(RUNNER),
        "--scenario",
        scenario_id,
        "--turns",
        str(max_turns),
        "--audit",
        "--metrics-out",
        str(metrics_out),
    ]
    print(f"=== {arm} / {scenario_id} (topology={topology}) ===", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(_PY),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "scenario_id": scenario_id,
        "arm": arm,
        "topology": topology,
        "max_turns": max_turns,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:] if proc.stdout else "",
        "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
        "metrics_out": str(metrics_out),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--scenario",
        action="append",
        help="Run only these scenario ids (default: all cohort D)",
    )
    parser.add_argument("--arm", choices=("baseline", "treatment", "both"), default="both")
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY required for live scenario matrix")

    plan = load_plan()
    scenarios = plan.get("cohort_d_scenarios") or []
    if args.scenario:
        scenarios = [s for s in scenarios if s["scenario_id"] in args.scenario]

    arms = ["baseline", "treatment"] if args.arm == "both" else [args.arm]
    results: list[dict] = []
    for spec in scenarios:
        sid = spec["scenario_id"]
        turns = int(spec.get("max_turns") or 12)
        for arm in arms:
            results.append(
                run_scenario(
                    scenario_id=sid,
                    arm=arm,
                    max_turns=turns,
                    dry_run=args.dry_run,
                )
            )

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_id": plan.get("experiment_id"),
        "dry_run": args.dry_run,
        "runs": results,
    }
    out = OUT_DIR / "i251_scenario_matrix_results.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()

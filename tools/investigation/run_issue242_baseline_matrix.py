#!/usr/bin/env python3
"""Issue #242 — execute approved baseline matrix (observability / capture only)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE

_PY = REPO_ROOT
_REPO_SHA = (
    subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT)
    .decode()
    .strip()
)
_BASELINE_SHA = _REPO_SHA[:12]
_RUN_ROOT = VALIDATION_RUNS_ARCHIVE / "issue242_baseline" / _BASELINE_SHA
_PROMPT_OUT = DATA_DIR / "issue240_runs" / "issue242_baseline_prompts" / _BASELINE_SHA

MATRIX_V1_NEXT7 = [
    ("R1a", "cert_i234_proposal_accept_off_focal", 6, str(DATA_DIR / "issue240/cert_i234_reinforced_overlay.json")),
    ("R1b", "cert_i234_proposal_accept_off_focal", 6, str(DATA_DIR / "issue240/cert_i234_reinforced_overlay.json")),
    ("R2a", "emotional_loop_2char", 12, str(DATA_DIR / "issue240/emotional_loop_2char_actor_targeted_overlay.json")),
    ("R2b", "emotional_loop_2char", 12, str(DATA_DIR / "issue240/emotional_loop_2char_actor_targeted_overlay.json")),
    ("R2c", "emotional_loop_2char", 12, str(DATA_DIR / "issue240/emotional_loop_2char_actor_targeted_overlay.json")),
    ("E1", "conflict_3char", 12, None),
    ("E2", "audit_i225_willow_must_remain_v2_offstage_cycles", 12, str(DATA_DIR / "issue240/audit_i225_willow_actor_targeted_overlay.json")),
    ("E3", "long_session", 12, None),
]

MATRIX_PRODUCTION = [
    ("T3a", "cert_i234_proposal_accept_off_focal", 6, str(DATA_DIR / "issue240/cert_i234_reinforced_overlay.json")),
    ("T3b", "emotional_loop_2char", 12, str(DATA_DIR / "issue240/emotional_loop_2char_actor_targeted_overlay.json")),
]


def _run_one(
    run_id: str,
    scenario: str,
    turns: int,
    schedule: str | None,
    *,
    topology: str | None,
) -> dict:
    env = os.environ.copy()
    env.pop("RP_RETRIEVED_CONTEXT_INDEX", None)
    env.pop("RP_EPISODIC_MEMORY", None)
    if topology:
        env["RP_ISSUE240_PROMPT_TOPOLOGY"] = topology
    else:
        env.pop("RP_ISSUE240_PROMPT_TOPOLOGY", None)

    metrics_out = _RUN_ROOT / f"{run_id}_{scenario}_metrics.json"
    metrics_out.parent.mkdir(parents=True, exist_ok=True)
    if metrics_out.is_file():
        print(f"\n=== {run_id} {scenario} SKIP (existing metrics) ===", flush=True)
        metrics = json.loads(metrics_out.read_text(encoding="utf-8"))
        session_num = metrics.get("audit_session_number")
        session_id = f"session_{session_num}" if session_num is not None else None
        return {
            "run_id": run_id,
            "scenario_id": scenario,
            "turns": turns,
            "schedule": schedule,
            "topology_env": topology,
            "metrics_out": str(metrics_out.relative_to(_PY)).replace("\\", "/"),
            "audit_session_number": session_num,
            "session_id": session_id,
            "skipped_existing": True,
        }

    cmd = [
        sys.executable,
        str(INVESTIGATION_DIR / "run_scene_simulation_llm.py"),
        "--scenario",
        scenario,
        "--turns",
        str(turns),
        "--audit",
        "--metrics-out",
        str(metrics_out),
    ]
    if schedule:
        cmd.extend(["--user-trigger-schedule", str(_PY / schedule)])

    print(f"\n=== {run_id} {scenario} topology={topology or 'production'} ===", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(_PY),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)

    metrics = json.loads(metrics_out.read_text(encoding="utf-8"))
    session_num = metrics.get("audit_session_number")
    session_id = f"session_{session_num}" if session_num is not None else None
    return {
        "run_id": run_id,
        "scenario_id": scenario,
        "turns": turns,
        "schedule": schedule,
        "topology_env": topology,
        "metrics_out": str(metrics_out.relative_to(_PY)).replace("\\", "/"),
        "audit_session_number": session_num,
        "session_id": session_id,
    }


def _extract_sessions(session_ids: list[str], scenario_hint: str | None = None) -> None:
    if not session_ids:
        return
    _PROMPT_OUT.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(INVESTIGATION_DIR / "_issue240_extract_prompts.py"),
        *session_ids,
        "--out-dir",
        str(_PROMPT_OUT.relative_to(_PY)).replace("\\", "/"),
        "--topology-manifest",
    ]
    if scenario_hint:
        cmd.extend(["--scenario-id", scenario_hint])
    subprocess.run(cmd, cwd=str(_PY), check=True)


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is required for baseline live runs", file=sys.stderr)
        return 1

    results: list[dict] = []
    for run_id, scenario, turns, schedule in MATRIX_V1_NEXT7:
        results.append(
            _run_one(run_id, scenario, turns, schedule, topology="v1_next7")
        )
    for run_id, scenario, turns, schedule in MATRIX_PRODUCTION:
        results.append(_run_one(run_id, scenario, turns, schedule, topology=None))

    session_ids = sorted(
        {r["session_id"] for r in results if r.get("session_id")},
        key=lambda s: int(s.split("_", 1)[1]),
    )
    _extract_sessions(session_ids)

    rollup_cmd = [
        sys.executable,
        str(INVESTIGATION_DIR / "_issue242_topology_rollup.py"),
        "--manifest-dir",
        str(_PROMPT_OUT.relative_to(_PY)).replace("\\", "/"),
        "--out",
        str((_RUN_ROOT / "topology_rollup.json").relative_to(_PY)).replace("\\", "/"),
    ]
    subprocess.run(rollup_cmd, cwd=str(_PY), check=True)

    manifest = {
        "schema_version": "issue242_baseline_run_manifest_v1",
        "issue": 242,
        "commit_sha": _REPO_SHA,
        "topology_env_primary": "v1_next7",
        "retrieval": "off",
        "runs": results,
        "session_ids": session_ids,
        "prompt_extraction_dir": str(_PROMPT_OUT.relative_to(_PY)).replace("\\", "/"),
        "topology_rollup": str(
            (_RUN_ROOT / "topology_rollup.json").relative_to(_PY)
        ).replace("\\", "/"),
    }
    manifest_path = _RUN_ROOT / "baseline_run_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Synthesize Issue #242 baseline evidence from captured artifacts."""
from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, LEGACY_RP_APP, REPO_ROOT, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir
import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_PY = REPO_ROOT
sys.path.insert(0, str(INVESTIGATION_DIR))
from _issue240_audit_classifier import analyze_session  # noqa: E402


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _overlay_applied_turns(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        t
        for t in analysis.get("turns") or []
        if t.get("overlay_applied") is True and t.get("actor_aligned") is True
    ]


def _semantic_eval_presence(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    hits = sum(1 for r in rows if r.get("semantic_decision") in {"covered_change", "no_covered_change"})
    return round(hits / len(rows), 3)


def _omission_rate_overlay(rows: list[dict[str, Any]]) -> float:
    overlay_rows = [r for r in rows if r.get("overlay_targeted") and r.get("actor_aligned") is True]
    if not overlay_rows:
        return 0.0
    bad = sum(
        1
        for r in overlay_rows
        if r.get("semantic_decision") in {"omission", "empty_array"}
        or r.get("classification") in {"F2", "F3"}
    )
    return round(bad / len(overlay_rows), 3)


def _overlay_f0_rate(analysis: dict[str, Any]) -> float | None:
    applied = _overlay_applied_turns(analysis)
    if not applied:
        return None
    f0 = sum(1 for t in applied if t.get("primary") == "F0")
    return round(f0 / len(applied), 3)


def synthesize(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    sha = manifest.get("commit_sha")
    prompt_dir = _PY / manifest.get("prompt_extraction_dir", "")
    index_rows: list[dict[str, Any]] = []
    if (prompt_dir / "INDEX.json").is_file():
        index_rows = _load_json(prompt_dir / "INDEX.json")

    by_session: dict[str, list[dict[str, Any]]] = {}
    for row in index_rows:
        by_session.setdefault(str(row.get("session")), []).append(row)

    run_summaries: list[dict[str, Any]] = []
    audits = LEGACY_RP_APP / "data" / "rp_audits"

    for run in manifest.get("runs") or []:
        session_id = run.get("session_id")
        if not session_id:
            continue
        analysis = analyze_session(audits / session_id)
        rows = by_session.get(session_id, [])
        run_summaries.append(
            {
                "run_id": run.get("run_id"),
                "scenario_id": run.get("scenario_id"),
                "session_id": session_id,
                "topology_env": run.get("topology_env"),
                "character_turns": len(rows),
                "semantic_eval_presence_rate": _semantic_eval_presence(rows),
                "overlay_omission_rate": _omission_rate_overlay(rows),
                "overlay_aligned_f0_rate": _overlay_f0_rate(analysis),
                "classifier_primary_counts": dict(
                    Counter(t.get("primary") for t in analysis.get("turns") or [])
                ),
            }
        )

    topology_rollup = {}
    rollup_path = manifest.get("topology_rollup")
    if rollup_path and (_PY / rollup_path).is_file():
        topology_rollup = _load_json(_PY / rollup_path)

    token_rows = [r for r in index_rows if (r.get("topology_env") == "v1_next7")]
    prod_rows = [r for r in index_rows if not r.get("topology_env")]

    def _median(key: str, rows: list[dict[str, Any]]) -> int | None:
        vals = [r.get(key) for r in rows if isinstance(r.get(key), int)]
        if not vals:
            return None
        s = sorted(vals)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) // 2

    return {
        "schema_version": "issue242_baseline_synthesis_v1",
        "issue": 242,
        "commit_sha": sha,
        "run_summaries": run_summaries,
        "topology_rollup": topology_rollup,
        "token_summary": {
            "v1_next7_median_system_chars": _median("system_chars", token_rows),
            "v1_next7_median_output_rules_chars": _median("output_rules_chars", token_rows),
            "production_median_system_chars": _median("system_chars", prod_rows),
            "production_median_output_rules_chars": _median("output_rules_chars", prod_rows),
        },
        "gates": {
            "semantic_eval_presence_v1_next7_min": min(
                (s["semantic_eval_presence_rate"] for s in run_summaries if s["topology_env"] == "v1_next7"),
                default=None,
            ),
            "overlay_omission_v1_next7_max": max(
                (s["overlay_omission_rate"] for s in run_summaries if s["topology_env"] == "v1_next7"),
                default=None,
            ),
            "profile_match_rate": (topology_rollup.get("aggregate_all_sessions") or {}).get(
                "profile_match_rate"
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", help="baseline_run_manifest.json path")
    ap.add_argument("--out", required=True, help="synthesis output JSON")
    args = ap.parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        manifest_path = _PY / args.manifest
    synthesis = synthesize(manifest_path)
    out = Path(args.out)
    if not out.is_absolute():
        out = _PY / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(synthesis, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(synthesis, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

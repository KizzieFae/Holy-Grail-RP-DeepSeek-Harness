#!/usr/bin/env python3
"""Run Issue #243 frozen corpus regression (Phase 0 skeleton — offline only).

Loads frozen #240 corpora, resolves evaluation profiles declaratively, and diffs
calibration-label snapshots against committed baselines. Does **not** score audits or
touch runtime paths.
"""

from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE
import argparse
import json
import sys
from pathlib import Path

_PY = REPO_ROOT
sys.path.insert(0, str(LEGACY_RP_APP))

from issue243_corpus_regression import (  # noqa: E402
    DEFAULT_FROZEN_CORPORA,
    default_baselines_dir,
    run_corpus_regression,
    run_eval_regression,
    summarize_eval_report,
    summarize_legacy_replay,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Issue #243 frozen corpus regression")
    ap.add_argument(
        "--baseline-dir",
        default=str(default_baselines_dir()),
        help="Directory containing committed baseline JSON files",
    )
    ap.add_argument(
        "--corpus",
        choices=[name for name, _ in DEFAULT_FROZEN_CORPORA],
        action="append",
        help="Corpus to check (default: all known frozen corpora)",
    )
    ap.add_argument("--json-out", default="", help="Optional path to write combined report JSON")
    ap.add_argument(
        "--eval",
        action="store_true",
        help="Run #243-B eval baseline regression (semantic_proposal_eval_v1)",
    )
    ap.add_argument(
        "--summary",
        action="store_true",
        help="With --eval, print human-alignment / ontology summary (no baseline required)",
    )
    ap.add_argument(
        "--legacy",
        action="store_true",
        help="Print legacy F-code replay summary (investigation-era taxonomy lane)",
    )
    ap.add_argument(
        "--legacy-replay",
        action="store_true",
        help="Re-classify legacy F-codes from corpus fields instead of stored classifier_primary",
    )
    args = ap.parse_args()
    baseline_dir = Path(args.baseline_dir)
    selected = DEFAULT_FROZEN_CORPORA
    if args.corpus:
        wanted = set(args.corpus)
        selected = tuple((n, p) for n, p in DEFAULT_FROZEN_CORPORA if n in wanted)

    reports: list[dict] = []
    exit_code = 0
    for name, corpus_path in selected:
        if args.legacy:
            summary = summarize_legacy_replay(name, corpus_path, replay=args.legacy_replay)
            print(json.dumps(summary, indent=2))
            continue
        if args.summary and args.eval:
            summary = summarize_eval_report(
                name, corpus_path, legacy_replay=args.legacy_replay
            )
            print(json.dumps(summary, indent=2))
            continue
        suffix = "_eval" if args.eval else ""
        baseline_path = baseline_dir / f"{name}{suffix}.json"
        if not corpus_path.is_file():
            print(f"FAIL {name}: missing corpus {corpus_path}", file=sys.stderr)
            exit_code = 1
            continue
        if not baseline_path.is_file():
            print(f"FAIL {name}: missing baseline {baseline_path}", file=sys.stderr)
            exit_code = 1
            continue
        if args.eval:
            report = run_eval_regression(name, corpus_path, baseline_path)
        else:
            report = run_corpus_regression(name, corpus_path, baseline_path)
        reports.append(report)
        status = "PASS" if report.get("passed") else "FAIL"
        print(
            f"{status} {name}: mismatches={report.get('mismatch_count')} "
            f"corpus={corpus_path.name} baseline={baseline_path.name}"
        )
        if not report.get("passed"):
            exit_code = 1
            for mm in report.get("mismatches") or []:
                print(f"  - {mm}", file=sys.stderr)

    combined = {
        "schema_version": "issue243_regression_run_v1",
        "issue": 243,
        "phase": "243-C" if args.eval else "243-A",
        "observational_only": True,
        "runtime_allowlist": False,
        "passed": exit_code == 0,
        "reports": reports,
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

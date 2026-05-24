#!/usr/bin/env python3
"""Run Issue #246 frozen corpus regression (offline only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PY / "rp_app"))

from issue246_corpus_regression import (  # noqa: E402
    default_baselines_dir,
    default_corpus_path,
    evaluate_corpus,
    run_regression,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Issue #246 corpus regression")
    ap.add_argument("--corpus", type=Path, default=default_corpus_path())
    ap.add_argument("--baseline-dir", type=Path, default=default_baselines_dir())
    ap.add_argument("--eval", action="store_true", help="Compare against committed baseline")
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()
    if not args.corpus.is_file():
        print(f"FAIL: missing corpus {args.corpus}", file=sys.stderr)
        return 1
    if args.eval:
        baseline = args.baseline_dir / "cohesion_v1.json"
        if not baseline.is_file():
            print(f"FAIL: missing baseline {baseline}", file=sys.stderr)
            return 1
        report = run_regression(args.corpus, baseline)
    else:
        report = evaluate_corpus(args.corpus)
    status = "PASS" if report.get("passed") else "FAIL"
    print(f"{status}: mismatches={report.get('mismatch_count')}")
    print(json.dumps(report.get("summary") or {}, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())

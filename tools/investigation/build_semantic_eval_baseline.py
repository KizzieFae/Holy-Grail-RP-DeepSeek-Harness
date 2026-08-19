#!/usr/bin/env python3
"""Build Issue #243 regression baselines from frozen #240 corpora (offline only).

Writes calibration-label snapshots under ``data/evaluation/issue243_regression_baselines/``.
These are **regression anchors**, not canonical evaluator truth.
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
    build_baseline_from_corpus,
    build_eval_baseline_from_corpus,
    default_baselines_dir,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build #243 frozen corpus regression baselines")
    ap.add_argument(
        "--out-dir",
        default=str(default_baselines_dir()),
        help="Output directory for baseline JSON files",
    )
    ap.add_argument(
        "--corpus",
        choices=[name for name, _ in DEFAULT_FROZEN_CORPORA],
        action="append",
        help="Corpus to build (default: all known frozen corpora)",
    )
    ap.add_argument(
        "--eval",
        action="store_true",
        help="Build #243-B eval baselines (semantic_proposal_eval_v1) instead of #243-A calibration baselines",
    )
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.corpus:
        wanted = set(args.corpus)
        selected = tuple((n, p) for n, p in DEFAULT_FROZEN_CORPORA if n in wanted)
    else:
        selected = DEFAULT_FROZEN_CORPORA
    for name, path in selected:
        if not path.is_file():
            print(f"skip {name}: missing corpus {path}", file=sys.stderr)
            return 1
        if args.eval:
            baseline = build_eval_baseline_from_corpus(name, path)
            suffix = "_eval"
        else:
            baseline = build_baseline_from_corpus(name, path)
            suffix = ""
        out_path = out_dir / f"{name}{suffix}.json"
        out_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out_path} ({baseline.get('case_count')} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

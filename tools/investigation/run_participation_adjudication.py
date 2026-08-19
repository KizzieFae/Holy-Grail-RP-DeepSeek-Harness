#!/usr/bin/env python3
"""Run offline participation suspicion adjudication (#246)."""

from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE
import argparse
import json
import sys
from pathlib import Path

_PY = REPO_ROOT
sys.path.insert(0, str(LEGACY_RP_APP))

from participation_adjudication_v1 import (  # noqa: E402
    adjudicate_suspicions,
    load_corpus_outcomes,
    row_lookup_from_jsonl,
    summarize_adjudication_report,
    write_adjudication_jsonl,
)
from participation_adjudication_llm import llm_adjudicate_bundle  # noqa: E402
from participation_suspicion_extract import (  # noqa: E402
    ParticipationSuspicionRecord,
    extract_suspicions_from_jsonl,
    load_jsonl_rows,
)


def _load_suspicions(path: Path) -> list[ParticipationSuspicionRecord]:
    rows = load_jsonl_rows(path)
    if rows and rows[0].get("schema_version") == "participation_suspicion.v1":
        return [ParticipationSuspicionRecord(**r) for r in rows]
    return extract_suspicions_from_jsonl(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Adjudicate participation suspicion records")
    ap.add_argument("--suspicions", type=Path, required=True, help="Suspicion or source JSONL")
    ap.add_argument("--source-jsonl", type=Path, default=None, help="Original extract for bundles")
    ap.add_argument("--corpus", type=Path, default=None, help="Frozen calibration corpus JSON")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--summary-out", type=Path, default=None)
    ap.add_argument("--mode", choices=("mock", "human", "llm"), default="mock")
    ap.add_argument("--llm-call-module", default="", help="Optional dotted path to llm callable")
    args = ap.parse_args()

    suspicions = _load_suspicions(args.suspicions)
    row_lookup = row_lookup_from_jsonl(args.source_jsonl) if args.source_jsonl else {}
    corpus_lookup = load_corpus_outcomes(args.corpus) if args.corpus and args.corpus.is_file() else None

    llm_fn = None
    if args.mode == "llm":
        if not args.llm_call_module:
            raise SystemExit("--llm-call-module required for llm mode")
        mod_name, _, fn_name = args.llm_call_module.rpartition(".")
        import importlib

        mod = importlib.import_module(mod_name)
        llm_call = getattr(mod, fn_name)

        from participation_adjudication_v1 import build_adjudication_bundle

        def _llm_fn(bundle):
            return llm_adjudicate_bundle(bundle, llm_call=llm_call)

        llm_fn = _llm_fn

    records = adjudicate_suspicions(
        suspicions,
        row_lookup=row_lookup,
        mode=args.mode,
        corpus_lookup=corpus_lookup,
        llm_fn=llm_fn,
    )
    write_adjudication_jsonl(records, args.out)
    summary = summarize_adjudication_report(suspicions, records)
    print(json.dumps(summary, indent=2))
    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

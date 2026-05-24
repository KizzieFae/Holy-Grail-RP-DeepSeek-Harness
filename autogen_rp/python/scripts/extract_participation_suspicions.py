#!/usr/bin/env python3
"""Extract participation suspicion records from cohesion/emission JSONL (#246)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PY / "rp_app"))

from participation_suspicion_extract import (  # noqa: E402
    extract_suspicions_from_jsonl,
    write_suspicion_jsonl,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract C3 suspicion records from JSONL")
    ap.add_argument("--jsonl", type=Path, required=True, help="Cohesion or emission JSONL input")
    ap.add_argument("--out", type=Path, required=True, help="Output suspicion JSONL")
    ap.add_argument("--summary-out", type=Path, default=None)
    args = ap.parse_args()
    if not args.jsonl.is_file():
        raise SystemExit(f"Input not found: {args.jsonl}")
    records = extract_suspicions_from_jsonl(args.jsonl)
    write_suspicion_jsonl(records, args.out)
    summary = {
        "schema_version": "participation_suspicion_summary.v1",
        "input": str(args.jsonl),
        "raw_deterministic_suspicion_count": len(records),
    }
    print(json.dumps(summary, indent=2))
    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} suspicion records -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()

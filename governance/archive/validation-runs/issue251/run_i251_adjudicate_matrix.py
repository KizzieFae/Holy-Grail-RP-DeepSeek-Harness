#!/usr/bin/env python3
"""Issue #251 — post-process replay matrix with #243-B/#249 semantic adjudication."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_OUT = Path(__file__).resolve().parent
_PY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PY / "rp_app"))
sys.path.insert(0, str(_OUT))

from i251_replay_adjudication import merge_adjudication_into_matrix  # noqa: E402

DEFAULT_IN = _OUT / "i251_exit_stability_matrix.json"
DEFAULT_OUT = _OUT / "i251_exit_stability_matrix_adjudicated.json"


def _print_comparison_table(summary: dict) -> None:
    print("\n=== Deterministic vs adjudicated (pilot) ===", flush=True)
    for k in (
        "n",
        "deterministic_correct_rate",
        "deterministic_correct_rate_clean_s2",
        "adjudicated_correct_rate",
        "adjudicated_correct_rate_exit",
        "adjudicated_correct_rate_non_exit",
        "ambiguous_rate",
        "structurally_contaminated_semantically_correct_count",
    ):
        print(f"  {k}: {summary.get(k)}", flush=True)

    print("\n| Case | Det S1 | Det S2 | Det OK | Adj OK | Lane | Eval cat |", flush=True)
    print("|---|---|---|---|---|---|---|", flush=True)
    for row in summary.get("comparison_rows") or []:
        print(
            f"| {row.get('case_id')} | {row.get('deterministic_s1')} | "
            f"{row.get('deterministic_s2')} | {row.get('deterministic_correct')} | "
            f"{row.get('adjudicated_correct')} | {row.get('failure_lane')} | "
            f"{row.get('corrected_category')} |",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="in_path", default=str(DEFAULT_IN))
    parser.add_argument("--out", dest="out_path", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    in_path = Path(args.in_path)
    payload = json.loads(in_path.read_text(encoding="utf-8"))
    merged = merge_adjudication_into_matrix(payload)
    merged["adjudication_generated_at"] = datetime.now(UTC).isoformat()
    merged["adjudication_source_matrix"] = str(in_path)

    out_path = Path(args.out_path)
    out_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)
    _print_comparison_table(merged.get("adjudication_summary") or {})


if __name__ == "__main__":
    main()

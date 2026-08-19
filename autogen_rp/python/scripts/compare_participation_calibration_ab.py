#!/usr/bin/env python3
"""Side-by-side comparison for participation calibration A/B emission-map runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _archive_paths import VALIDATION_RUNS_ARCHIVE

_PY_ROOT = Path(__file__).resolve().parents[1]
_RUBRIC_KEYS = (
    "C1_correct_no_change",
    "C2_correct_covered_change",
    "C3_missed_covered_change",
    "C4_false_positive_covered_change",
    "C5_legality_retry",
    "C6_unclassified",
    "C7_ambiguous",
    "C8_fiction_denies_transition",
)


def _load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rubric_counts(summary: dict) -> dict[str, int]:
    raw = summary.get("rubric_class_counts") or {}
    return {k: int(raw.get(k, 0) or 0) for k in _RUBRIC_KEYS}


def main() -> None:
    p = argparse.ArgumentParser(description="Compare baseline vs calibrated emission-map summaries.")
    p.add_argument("--baseline-summary", type=Path, required=True)
    p.add_argument("--calibrated-summary", type=Path, required=True)
    p.add_argument("--out", type=Path, default=VALIDATION_RUNS_ARCHIVE / "participation_calibration_ab_comparison.json")
    args = p.parse_args()

    baseline = _load_summary(args.baseline_summary)
    calibrated = _load_summary(args.calibrated_summary)
    b_counts = _rubric_counts(baseline)
    c_counts = _rubric_counts(calibrated)

    comparison = {
        "schema_version": "participation_calibration_ab_comparison.v1",
        "baseline": {
            "summary_path": str(args.baseline_summary),
            "audit_session_number": baseline.get("audit_session_number"),
            "probe_emitted_proposal_count": baseline.get("probe_emitted_proposal_count"),
            "F_suspect_miss_count": baseline.get("F_suspect_miss_count"),
            "rubric_class_counts": b_counts,
            "probe_first_actor_class": baseline.get("probe_first_actor_class") or {},
        },
        "calibrated": {
            "summary_path": str(args.calibrated_summary),
            "audit_session_number": calibrated.get("audit_session_number"),
            "probe_emitted_proposal_count": calibrated.get("probe_emitted_proposal_count"),
            "F_suspect_miss_count": calibrated.get("F_suspect_miss_count"),
            "rubric_class_counts": c_counts,
            "probe_first_actor_class": calibrated.get("probe_first_actor_class") or {},
        },
        "delta": {
            "probe_emitted_proposal_count": (
                int(calibrated.get("probe_emitted_proposal_count") or 0)
                - int(baseline.get("probe_emitted_proposal_count") or 0)
            ),
            "F_suspect_miss_count": (
                int(calibrated.get("F_suspect_miss_count") or 0)
                - int(baseline.get("F_suspect_miss_count") or 0)
            ),
            "rubric_class_counts": {
                k: c_counts.get(k, 0) - b_counts.get(k, 0) for k in _RUBRIC_KEYS
            },
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

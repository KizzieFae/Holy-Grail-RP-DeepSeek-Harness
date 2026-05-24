#!/usr/bin/env python3
"""Aggregate baseline vs selective-flex cohesion slate comparisons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _arm(label: str, path: Path, summary: dict) -> dict:
    raw = summary.get("rubric_class_counts") or {}
    adj = summary.get("adjudication_report") or {}
    return {
        "label": label,
        "summary_path": str(path),
        "audit_session_number": summary.get("audit_session_number"),
        "covered_change_emitted_count": summary.get("covered_change_emitted_count"),
        "covered_change_probe_count": summary.get("covered_change_probe_count"),
        "covered_change_probe_total": summary.get("covered_change_probe_total"),
        "fiction_roster_drift_count": summary.get("fiction_roster_drift_count"),
        "tether_probe_count": summary.get("tether_probe_count"),
        "rebound_probe_count": summary.get("rebound_probe_count"),
        "filler_probe_count": summary.get("filler_probe_count"),
        "probe_emitted_proposal_count": summary.get("probe_emitted_proposal_count"),
        "rubric_class_counts": {k: int(raw.get(k, 0) or 0) for k in _RUBRIC_KEYS},
        "raw_c3_suspicion_count": summary.get("raw_c3_suspicion_count")
        or int(raw.get("C3_missed_covered_change", 0) or 0),
        "validation_failure_count": summary.get("validation_failure_count")
        or adj.get("adjudicated_failure_count"),
        "adjudication_report": adj,
        "probe_detail": summary.get("probe_detail") or {},
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Compare baseline vs selective-flex cohesion summaries.")
    p.add_argument("--baseline-summary", type=Path, required=True)
    p.add_argument("--flex-summary", type=Path, required=True)
    p.add_argument("--archetype-id", type=str, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    baseline = _load(args.baseline_summary)
    flex = _load(args.flex_summary)
    b = _arm("baseline", args.baseline_summary, baseline)
    f = _arm("selective_flex", args.flex_summary, flex)
    comparison = {
        "schema_version": "cohesion_slate_comparison.v1",
        "archetype_id": args.archetype_id,
        "baseline": b,
        "selective_flex": f,
        "delta": {
            "covered_change_emitted_count": int(f.get("covered_change_emitted_count") or 0)
            - int(b.get("covered_change_emitted_count") or 0),
            "covered_change_probe_count": int(f.get("covered_change_probe_count") or 0)
            - int(b.get("covered_change_probe_count") or 0),
            "fiction_roster_drift_count": int(f.get("fiction_roster_drift_count") or 0)
            - int(b.get("fiction_roster_drift_count") or 0),
            "probe_emitted_proposal_count": int(f.get("probe_emitted_proposal_count") or 0)
            - int(b.get("probe_emitted_proposal_count") or 0),
            "tether_probe_count": int(f.get("tether_probe_count") or 0)
            - int(b.get("tether_probe_count") or 0),
            "validation_failure_count": int(f.get("validation_failure_count") or 0)
            - int(b.get("validation_failure_count") or 0),
            "raw_c3_suspicion_count": int(f.get("raw_c3_suspicion_count") or 0)
            - int(b.get("raw_c3_suspicion_count") or 0),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

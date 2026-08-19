#!/usr/bin/env python3
"""Three-arm comparison for #227 anchor-only must_remain Willow departure experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE

_PY_ROOT = REPO_ROOT
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
_WILLOW_KEYS = (
    "willow_rebound_probe_count",
    "willow_tether_probe_count",
    "willow_in_room_focus_probe_count",
    "willow_fiction_roster_drift_count",
)


def _load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _arm_block(label: str, path: Path, summary: dict) -> dict:
    raw = summary.get("rubric_class_counts") or {}
    rubric = {k: int(raw.get(k, 0) or 0) for k in _RUBRIC_KEYS}
    return {
        "label": label,
        "summary_path": str(path),
        "audit_session_number": summary.get("audit_session_number"),
        "willow_presence_constraint_seen": summary.get("willow_presence_constraint_seen"),
        "probe_emitted_proposal_count": summary.get("probe_emitted_proposal_count"),
        "F_suspect_miss_count": summary.get("F_suspect_miss_count"),
        "rubric_class_counts": rubric,
        "willow_probe_detail": summary.get("willow_probe_detail") or {},
        **{k: summary.get(k) for k in _WILLOW_KEYS},
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Compare baseline vs flexible Willow departure arms.")
    p.add_argument("--baseline-summary", type=Path, required=True)
    p.add_argument("--willow-flex-summary", type=Path, required=True)
    p.add_argument("--alphas-flex-summary", type=Path, required=True)
    p.add_argument(
        "--out",
        type=Path,
        default=VALIDATION_RUNS_ARCHIVE / "willow_departure_experiment_comparison.json",
    )
    args = p.parse_args()

    baseline = _load_summary(args.baseline_summary)
    willow_flex = _load_summary(args.willow_flex_summary)
    alphas_flex = _load_summary(args.alphas_flex_summary)

    arms = {
        "baseline": _arm_block("baseline_all_must_remain", args.baseline_summary, baseline),
        "willow_flex": _arm_block(
            "anchor_willow_flexible", args.willow_flex_summary, willow_flex
        ),
        "alphas_flex": _arm_block(
            "anchor_alphas_flexible", args.alphas_flex_summary, alphas_flex
        ),
    }

    def _delta(a: dict, b: dict) -> dict:
        return {
            "probe_emitted_proposal_count": int(b.get("probe_emitted_proposal_count") or 0)
            - int(a.get("probe_emitted_proposal_count") or 0),
            "F_suspect_miss_count": int(b.get("F_suspect_miss_count") or 0)
            - int(a.get("F_suspect_miss_count") or 0),
            "rubric_class_counts": {
                k: int((b.get("rubric_class_counts") or {}).get(k, 0))
                - int((a.get("rubric_class_counts") or {}).get(k, 0))
                for k in _RUBRIC_KEYS
            },
            **{
                k: int(b.get(k) or 0) - int(a.get(k) or 0)
                for k in _WILLOW_KEYS
            },
        }

    comparison = {
        "schema_version": "willow_departure_experiment_comparison.v1",
        "experiment_id": "i227_anchor_only_must_remain",
        "arms": arms,
        "delta_willow_flex_vs_baseline": _delta(arms["baseline"], arms["willow_flex"]),
        "delta_alphas_flex_vs_baseline": _delta(arms["baseline"], arms["alphas_flex"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

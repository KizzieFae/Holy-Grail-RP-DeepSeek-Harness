#!/usr/bin/env python3
"""Issue #251 — broad exit-stability validation matrix (treatment-only, frozen audits)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_PY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PY / "rp_app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompt_topology_issue240 import (
    ISSUE251_MIN_SEVERANCE_CLARIFICATION_MARKER,
    build_issue251_min_severance_clarification_block,
)
from i251_replay_adjudication import merge_adjudication_into_matrix
from run_i251_anchor_guard_experiment import run_sample

OUT_DIR = Path(__file__).resolve().parent
PLAN = OUT_DIR / "i251_exit_stability_matrix_plan.json"
DEFAULT_SAMPLE_N = 1


def load_plan() -> dict[str, Any]:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def classify_row(row: dict[str, Any]) -> dict[str, Any]:
    fa = row.get("first_attempt") or {}
    s1 = fa.get("S1_semantic_intent_correct")
    s2 = fa.get("S2_structural_legality_pass")
    decision = fa.get("decision")
    kinds = list(fa.get("proposal_kinds") or [])
    clean = bool(s2)
    expected = row.get("doctrine_expected")
    if expected == "off_focal":
        correct = s1 is True and decision == "covered_change" and kinds == ["off_focal"]
        false_negative = clean and decision == "no_covered_change" and not kinds
        false_positive = False
        if clean and "off_focal" in kinds and not correct:
            false_positive = True
    else:
        correct = s1 is True and decision == "no_covered_change" and "off_focal" not in kinds
        false_positive = clean and "off_focal" in kinds
        false_negative = False
    other = clean and not correct and not false_positive and not false_negative
    return {
        "semantic_decision": decision,
        "proposal_kinds": kinds,
        "S1": s1,
        "S2": s2,
        "clean_interpretable": clean,
        "expected_label": row.get("expected_label"),
        "outcome_correct": correct,
        "false_positive_off_focal": false_positive,
        "false_negative_missed_off_focal": false_negative,
        "outcome_other_clean": other,
        "s2_contamination": not s2,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    classified = []
    for r in rows:
        if r.get("status") == "artifact_missing" or not r.get("first_attempt"):
            continue
        m = classify_row(r)
        classified.append({**r, "metrics": m})

    clean = [c for c in classified if c["metrics"]["clean_interpretable"]]
    exits = [c for c in clean if c.get("cohort") == "exit"]
    non_exits = [c for c in clean if c.get("cohort") == "non_exit"]

    def rate(items: list[dict], key: str) -> float | None:
        if not items:
            return None
        return round(sum(1 for i in items if i["metrics"][key]) / len(items), 3)

    by_category: dict[str, list[dict]] = defaultdict(list)
    for c in classified:
        by_category[c.get("category") or "unknown"].append(c)

    category_summary = {}
    for cat, items in sorted(by_category.items()):
        cat_clean = [i for i in items if i["metrics"]["clean_interpretable"]]
        category_summary[cat] = {
            "n": len(items),
            "n_clean": len(cat_clean),
            "correct_clean": sum(1 for i in cat_clean if i["metrics"]["outcome_correct"]),
            "false_positive": sum(
                1 for i in cat_clean if i["metrics"]["false_positive_off_focal"]
            ),
            "false_negative": sum(
                1 for i in cat_clean if i["metrics"]["false_negative_missed_off_focal"]
            ),
        }

    return {
        "n_attempted": len(rows),
        "n_classified": len(classified),
        "n_clean": len(clean),
        "correct_clean": sum(1 for c in clean if c["metrics"]["outcome_correct"]),
        "exit_n_clean": len(exits),
        "exit_success_rate_clean": rate(exits, "outcome_correct"),
        "exit_false_negative_rate_clean": rate(exits, "false_negative_missed_off_focal"),
        "non_exit_n_clean": len(non_exits),
        "non_exit_correct_rate_clean": rate(non_exits, "outcome_correct"),
        "false_positive_rate_clean": rate(non_exits, "false_positive_off_focal"),
        "s2_contamination_rate": round(
            sum(1 for c in classified if c["metrics"]["s2_contamination"])
            / max(len(classified), 1),
            3,
        ),
        "by_category": category_summary,
        "samples": classified,
    }


async def run_experiment(*, dry_run: bool = False, sample_n: int) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    plan = load_plan()
    clarification = build_issue251_min_severance_clarification_block()
    all_rows: list[dict[str, Any]] = []

    for spec in plan.get("cases") or []:
        case_id = spec["case_id"]
        for sample_index in range(sample_n):
            print(
                f"=== {case_id} sample {sample_index + 1}/{sample_n} ===",
                flush=True,
            )
            if dry_run:
                all_rows.append(
                    {
                        "case_id": case_id,
                        "sample_index": sample_index,
                        "dry_run": True,
                    }
                )
                continue
            row = await run_sample(
                case_id=case_id,
                session=spec["session"],
                rnd=int(spec["round"]),
                turn=int(spec["turn"]),
                actor=spec["actor"],
                cohort=spec["cohort"],
                doctrine_expected=spec["doctrine_expected"],
                note=spec.get("category"),
                arm="treatment",
                sample_index=sample_index,
            )
            row["category"] = spec.get("category")
            row["expected_result_label"] = spec.get("expected_label")
            fa = row.get("first_attempt") or {}
            print(
                f"  S1={fa.get('S1_semantic_intent_correct')} S2={fa.get('S2_structural_legality_pass')} "
                f"decision={fa.get('decision')} kinds={fa.get('proposal_kinds')}",
                flush=True,
            )
            all_rows.append(row)

    summary = summarize(all_rows)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_id": os.environ.get(
            "I251_EXIT_STABILITY_EXPERIMENT_ID",
            plan.get("experiment_id"),
        ),
        "topology": plan.get("topology"),
        "arm": "treatment_only",
        "sample_n_per_case": sample_n,
        "clarification_marker": ISSUE251_MIN_SEVERANCE_CLARIFICATION_MARKER,
        "clarification_wording": clarification,
        "ontology_note": plan.get("ontology_note"),
        "excluded_case_ids": plan.get("excluded_case_ids"),
        "dry_run": dry_run,
        "summary": summary,
        "all_samples": all_rows,
    }
    out_name = os.environ.get(
        "I251_EXIT_STABILITY_OUT", "i251_exit_stability_matrix.json"
    )
    payload = merge_adjudication_into_matrix(payload)
    out_path = OUT_DIR / out_name
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)
    if payload.get("adjudication_summary"):
        s = payload["adjudication_summary"]
        print(
            f"Adjudication: det={s.get('deterministic_correct_rate')} "
            f"adj={s.get('adjudicated_correct_rate')} "
            f"ambiguous={s.get('ambiguous_rate')} "
            f"S2-contaminated-but-adj-ok={s.get('structurally_contaminated_semantically_correct_count')}",
            flush=True,
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--sample-n",
        type=int,
        default=int(os.environ.get("I251_EXIT_STABILITY_SAMPLE_N", DEFAULT_SAMPLE_N)),
    )
    args = parser.parse_args()
    asyncio.run(run_experiment(dry_run=args.dry_run, sample_n=args.sample_n))


if __name__ == "__main__":
    main()

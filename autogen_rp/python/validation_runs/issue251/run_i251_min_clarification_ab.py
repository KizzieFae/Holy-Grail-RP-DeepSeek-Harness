#!/usr/bin/env python3
"""Issue #251 — minimal severance clarification A/B (GM3 + P03, N=10 treatment)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
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
SAMPLE_N = 10

CASES = [
    (
        "GM3",
        "session_912",
        1,
        12,
        "willow_reeves",
        "anchor",
        "off_focal",
        "covered_change + off_focal",
    ),
    (
        "P03",
        "session_908",
        1,
        7,
        "willow_reeves",
        "guard",
        "no_covered_change",
        "no_covered_change (no off_focal)",
    ),
]


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
        incorrect_nc = clean and decision == "no_covered_change" and not kinds
        incorrect_off = False
        if clean and "off_focal" in kinds and not correct:
            incorrect_off = True
    else:
        correct = s1 is True and decision == "no_covered_change" and "off_focal" not in kinds
        incorrect_off = clean and "off_focal" in kinds
        incorrect_nc = False
    other = clean and not correct and not incorrect_nc and not incorrect_off
    return {
        "semantic_decision": decision,
        "proposal_kinds": kinds,
        "S1": s1,
        "S2": s2,
        "clean_interpretable": clean,
        "expected_label": row.get("expected_result_label"),
        "outcome_correct": correct,
        "outcome_incorrect_no_covered_change": incorrect_nc,
        "outcome_incorrect_off_focal": incorrect_off,
        "outcome_other_clean": other,
        "s2_contamination": not s2,
    }


def summarize_samples(rows: list[dict[str, Any]]) -> dict[str, Any]:
    classified = [classify_row(r) for r in rows if r.get("first_attempt")]
    n = len(classified)
    return {
        "n": n,
        "correct": sum(1 for c in classified if c["outcome_correct"]),
        "incorrect_no_covered_change": sum(
            1 for c in classified if c["outcome_incorrect_no_covered_change"]
        ),
        "incorrect_off_focal": sum(
            1 for c in classified if c["outcome_incorrect_off_focal"]
        ),
        "other_clean": sum(1 for c in classified if c["outcome_other_clean"]),
        "s2_contamination": sum(1 for c in classified if c["s2_contamination"]),
        "samples": [
            {**rows[i], "metrics": classified[i]} for i in range(min(len(rows), len(classified)))
        ],
    }


async def run_experiment(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    clarification = build_issue251_min_severance_clarification_block()
    all_rows: list[dict[str, Any]] = []

    for (
        case_id,
        session,
        rnd,
        turn,
        actor,
        cohort,
        expected,
        expected_label,
    ) in CASES:
        for sample_index in range(SAMPLE_N):
            print(
                f"=== {case_id} treatment sample {sample_index + 1}/{SAMPLE_N} ===",
                flush=True,
            )
            if dry_run:
                all_rows.append(
                    {
                        "case_id": case_id,
                        "arm": "treatment",
                        "sample_index": sample_index,
                        "dry_run": True,
                    }
                )
                continue
            row = await run_sample(
                case_id=case_id,
                session=session,
                rnd=rnd,
                turn=turn,
                actor=actor,
                cohort=cohort,
                doctrine_expected=expected,
                note="min_clarification_ab",
                arm="treatment",
                sample_index=sample_index,
            )
            row["expected_result_label"] = expected_label
            fa = row.get("first_attempt") or {}
            print(
                f"  S1={fa.get('S1_semantic_intent_correct')} S2={fa.get('S2_structural_legality_pass')} "
                f"decision={fa.get('decision')} kinds={fa.get('proposal_kinds')}",
                flush=True,
            )
            all_rows.append(row)

    gm3_rows = [r for r in all_rows if r.get("case_id") == "GM3"]
    p03_rows = [r for r in all_rows if r.get("case_id") == "P03"]

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_id": os.environ.get(
            "I251_MIN_CLARIFICATION_EXPERIMENT_ID",
            "issue251_min_severance_clarification_ab_v1",
        ),
        "topology": "v1_next7_issue251_awareness_clean",
        "arm": "treatment_only",
        "sample_n_per_case": SAMPLE_N,
        "clarification_marker": ISSUE251_MIN_SEVERANCE_CLARIFICATION_MARKER,
        "clarification_wording": clarification,
        "dry_run": dry_run,
        "gm3": summarize_samples(gm3_rows),
        "p03": summarize_samples(p03_rows),
        "all_samples": all_rows,
    }
    out_name = os.environ.get(
        "I251_MIN_CLARIFICATION_OUT",
        "i251_min_clarification_ab_matrix.json",
    )
    payload = merge_adjudication_into_matrix(
        {**payload, "all_samples": all_rows}
    )
    out_path = OUT_DIR / out_name
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)
    if payload.get("adjudication_summary"):
        s = payload["adjudication_summary"]
        print(
            f"Adjudication: det={s.get('deterministic_correct_rate')} "
            f"adj={s.get('adjudicated_correct_rate')}",
            flush=True,
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Issue #251 — Phase 1 dual-arm doctrine isolation rerun (A hybrid vs B physical)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
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

from i251_doctrine_alignment import (
    evaluate_doctrine_alignment,
    summarize_doctrine_alignment,
)
from i251_replay_adjudication import adjudicate_replay_row, summarize_adjudicated_vs_deterministic
from prompt_topology_issue240 import (
    ISSUE251_AWARENESS_CLEAN_MARKER,
    ISSUE251_AWARENESS_DOCTRINE_MARKER,
    ISSUE251_PHYSICAL_SEVERANCE_DOCTRINE_MARKER,
    ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER,
    ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER,
    ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER,
    apply_issue251_awareness_clean_prompt_overrides,
    apply_issue251_physical_severance_prompt_overrides,
    issue251_awareness_contamination_hits,
    issue251_physical_severance_contamination_hits,
)
from prompt_topology_manifest import extract_topology_manifest
from i251_metrics import enrich_attempt_metrics
from run_i251_anchor_guard_experiment import (
    attempt_metrics,
    call_character_once,
    find_committed_artifact,
    scene_state_from_prompt,
    sys_prompt,
)

OUT_DIR = Path(__file__).resolve().parent
PLAN_PATH = OUT_DIR / "i251_doctrine_isolation_phase1_plan.json"
MATRIX_OUT = OUT_DIR / "i251_doctrine_isolation_phase1_matrix.json"
ADJ_OUT = OUT_DIR / "i251_doctrine_isolation_phase1_matrix_adjudicated.json"
SUMMARY_OUT = OUT_DIR / "i251_doctrine_isolation_phase1_summary.json"

_ARM_APPLY = {
    "A": apply_issue251_awareness_clean_prompt_overrides,
    "B": apply_issue251_physical_severance_prompt_overrides,
}


def load_plan() -> dict[str, Any]:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def apply_doctrine_arm_prompt(prompt: str, char_name: str, arm_id: str) -> str:
    fn = _ARM_APPLY.get(arm_id)
    if fn is None:
        raise ValueError(f"unknown doctrine arm: {arm_id}")
    return fn(prompt, char_name)


def preflight_doctrine(prompt: str, arm_cfg: dict[str, Any]) -> dict[str, Any]:
    arm_id = arm_cfg["arm_id"]
    manifest = extract_topology_manifest(prompt)
    base: dict[str, Any] = {
        "doctrine_arm": arm_id,
        "doctrine_schema_version": arm_cfg["doctrine_schema_version"],
        "schema_marker_present": ISSUE240_V1_NEXT7_PROPOSAL_SCHEMA_A_MARKER in prompt,
        "topology_inferred": manifest.get("topology_inferred"),
        "fuzzy_threshold_absent": ISSUE240_V1_NEXT7_FUZZY_THRESHOLD_MARKER not in prompt,
    }
    if arm_id == "A":
        hits = issue251_awareness_contamination_hits(prompt)
        for forbidden in arm_cfg.get("forbidden_markers") or []:
            if forbidden in prompt:
                hits.append(f"cross_arm:{forbidden}")
        base.update(
            {
                "awareness_doctrine_marker": ISSUE251_AWARENESS_DOCTRINE_MARKER in prompt,
                "awareness_clean_marker": ISSUE251_AWARENESS_CLEAN_MARKER in prompt,
                "contamination_hits": hits,
                "contamination_clean": hits == [],
            }
        )
    elif arm_id == "B":
        hits = issue251_physical_severance_contamination_hits(prompt)
        for forbidden in arm_cfg.get("forbidden_markers") or []:
            if forbidden in prompt:
                hits.append(f"cross_arm:{forbidden}")
        for phrase in arm_cfg.get("forbidden_phrases") or []:
            if phrase in prompt:
                hits.append(f"forbidden_phrase:{phrase}")
        base.update(
            {
                "physical_severance_doctrine_marker": ISSUE251_PHYSICAL_SEVERANCE_DOCTRINE_MARKER
                in prompt,
                "physical_severance_isolation_marker": ISSUE251_PHYSICAL_SEVERANCE_ISOLATION_MARKER
                in prompt,
                "contamination_hits": hits,
                "contamination_clean": hits == [],
            }
        )
    return base


async def run_isolation_sample(
    *,
    case_spec: dict[str, Any],
    arm_cfg: dict[str, Any],
    sample_index: int,
) -> dict[str, Any]:
    case_id = case_spec["case_id"]
    session = case_spec["session"]
    rnd = int(case_spec["round"])
    turn = int(case_spec["turn"])
    actor = case_spec["actor"]
    arm_id = arm_cfg["arm_id"]

    committed_path = find_committed_artifact(session, rnd, turn, actor)
    if committed_path is None:
        return {
            "case_id": case_id,
            "doctrine_arm": arm_id,
            "sample_index": sample_index,
            "status": "artifact_missing",
            "error": f"missing {session} R{rnd}T{turn} {actor}",
        }

    audit = json.loads(committed_path.read_text(encoding="utf-8"))
    bot_name = str(audit.get("bot_name") or actor)
    original_prompt = sys_prompt(audit)
    if not original_prompt:
        raise ValueError(f"{case_id}: empty system prompt")

    arm_prompt = apply_doctrine_arm_prompt(original_prompt, bot_name, arm_id)
    prompt_sha256 = hashlib.sha256(arm_prompt.encode("utf-8")).hexdigest()
    pf = preflight_doctrine(arm_prompt, arm_cfg)
    scene_state = scene_state_from_prompt(original_prompt)

    raw = await call_character_once(arm_prompt, bot_name)
    attempt = enrich_attempt_metrics(
        attempt_metrics(raw=raw, bot_name=bot_name, scene_state=scene_state),
        case_spec["doctrine_expected"],
    )

    arm_labels = (case_spec.get("expected_labels") or {}).get(arm_id) or {}
    expected_label = arm_labels.get("label") or case_spec.get("doctrine_expected")
    l3_rubric = (case_spec.get("L3_rubric") or {}).get(arm_id)

    row: dict[str, Any] = {
        "case_id": case_id,
        "cohort_group": case_spec.get("cohort_group"),
        "category": case_spec.get("category"),
        "cohort": case_spec.get("cohort"),
        "doctrine_arm": arm_id,
        "doctrine_schema_version": arm_cfg["doctrine_schema_version"],
        "topology": arm_cfg["topology"],
        "sample_index": sample_index,
        "session": session,
        "round": rnd,
        "turn": turn,
        "actor": actor,
        "bot_name": bot_name,
        "doctrine_expected": case_spec["doctrine_expected"],
        "expected_result_label": expected_label,
        "source_artifact": str(committed_path),
        "prompt_sha256": prompt_sha256,
        "preflight": pf,
        "L1_deterministic": attempt,
        "first_attempt": attempt,
        "raw_response_excerpt": raw[:2000],
    }
    row["L2_adjudicated"] = adjudicate_replay_row(row)
    row["adjudication"] = row["L2_adjudicated"]
    row["L3_doctrine_alignment"] = evaluate_doctrine_alignment(
        doctrine_arm=arm_id,
        doctrine_schema_version=arm_cfg["doctrine_schema_version"],
        doctrine_expected=case_spec["doctrine_expected"],
        attempt=attempt,
        expected_label=expected_label,
        l3_rubric=l3_rubric,
    )
    row["doctrine_alignment"] = row["L3_doctrine_alignment"]
    return row


def _cohort_slice(rows: list[dict[str, Any]], group: str) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("cohort_group") == group]


def build_comparison_report(rows: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("status") == "artifact_missing":
            continue
        by_arm[str(r.get("doctrine_arm"))].append(r)

    l3_summary = summarize_doctrine_alignment(rows)
    adjudication_by_arm: dict[str, Any] = {}
    for arm, arm_rows in by_arm.items():
        adjudication_by_arm[arm] = summarize_adjudicated_vs_deterministic(
            arm_rows, adjudications=[r.get("adjudication") or {} for r in arm_rows]
        )

    preflight_failures = [
        {
            "case_id": r.get("case_id"),
            "doctrine_arm": r.get("doctrine_arm"),
            "sample_index": r.get("sample_index"),
            "contamination_hits": (r.get("preflight") or {}).get("contamination_hits"),
        }
        for r in rows
        if not (r.get("preflight") or {}).get("contamination_clean", True)
    ]

    gm3_rows = [r for r in rows if r.get("case_id") == "EXIT-C-GM3"]
    gm3_by_arm: dict[str, Any] = {}
    for arm in ("A", "B"):
        arm_gm3 = [r for r in gm3_rows if r.get("doctrine_arm") == arm]
        clean = [
            r
            for r in arm_gm3
            if (r.get("first_attempt") or {}).get("S2_structural_legality_pass")
        ]
        gm3_by_arm[arm] = {
            "n": len(arm_gm3),
            "S1_pass": sum(
                1
                for r in arm_gm3
                if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
            ),
            "S2_clean_S1_pass": sum(
                1
                for r in clean
                if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
            ),
            "L3_aligned": sum(
                1
                for r in arm_gm3
                if (r.get("doctrine_alignment") or {}).get("doctrine_aligned")
            ),
            "decisions": [
                (r.get("first_attempt") or {}).get("decision") for r in arm_gm3
            ],
        }

    return {
        "experiment_id": plan.get("experiment_id"),
        "generated_at": datetime.now(UTC).isoformat(),
        "doctrine_alignment_summary": l3_summary,
        "adjudication_by_arm": adjudication_by_arm,
        "preflight_contamination_failures": preflight_failures,
        "gm3_summary": gm3_by_arm,
        "cohort_groups": {
            group: {
                arm: {
                    "n": len(
                        [
                            r
                            for r in _cohort_slice(by_arm.get(arm, []), group)
                        ]
                    ),
                    "S2_clean_S1_rate": summarize_doctrine_alignment(
                        _cohort_slice(by_arm.get(arm, []), group)
                    )["by_arm"]
                    .get(arm, {})
                    .get("S2_clean_S1_rate"),
                }
                for arm in ("A", "B")
            }
            for group in (
                "gm3_discriminator",
                "exit_temporary_threshold",
                "exit_explicit_controls",
                "non_exit_guards",
            )
        },
        "success_criteria_ref": plan.get("success_criteria_ref"),
    }


async def run_experiment(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    plan = load_plan()
    arms = plan.get("doctrine_arms") or {}
    all_rows: list[dict[str, Any]] = []

    for case_spec in plan.get("cases") or []:
        sample_n = int(case_spec.get("sample_n") or 1)
        for arm_id in ("A", "B"):
            arm_cfg = arms[arm_id]
            for sample_index in range(sample_n):
                label = (
                    f"=== {case_spec['case_id']} arm={arm_id} "
                    f"sample {sample_index + 1}/{sample_n} ==="
                )
                print(label, flush=True)
                if dry_run:
                    all_rows.append(
                        {
                            "case_id": case_spec["case_id"],
                            "doctrine_arm": arm_id,
                            "sample_index": sample_index,
                            "dry_run": True,
                        }
                    )
                    continue
                row = await run_isolation_sample(
                    case_spec=case_spec,
                    arm_cfg=arm_cfg,
                    sample_index=sample_index,
                )
                fa = row.get("first_attempt") or {}
                pf = row.get("preflight") or {}
                l3 = row.get("doctrine_alignment") or {}
                print(
                    f"  preflight_clean={pf.get('contamination_clean')} "
                    f"S1={fa.get('S1_semantic_intent_correct')} "
                    f"S2={fa.get('S2_structural_legality_pass')} "
                    f"L3={l3.get('doctrine_aligned')} "
                    f"dec={fa.get('decision')}",
                    flush=True,
                )
                all_rows.append(row)

    comparison = build_comparison_report(all_rows, plan) if not dry_run else {}
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_id": plan.get("experiment_id"),
        "status": "dry_run" if dry_run else "complete",
        "plan_schema": plan.get("schema_version"),
        "doctrine_arms": {
            k: {
                "topology": v.get("topology"),
                "doctrine_schema_version": v.get("doctrine_schema_version"),
            }
            for k, v in arms.items()
        },
        "execution_summary": plan.get("execution_summary"),
        "samples": all_rows,
        "comparison_report": comparison,
    }

    out_path = MATRIX_OUT
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}", flush=True)

    adj_payload = dict(payload)
    adj_payload["adjudication_summary"] = comparison.get("adjudication_by_arm")
    adj_payload["doctrine_alignment_summary"] = comparison.get("doctrine_alignment_summary")
    ADJ_OUT.write_text(json.dumps(adj_payload, indent=2), encoding="utf-8")
    print(f"Wrote {ADJ_OUT}", flush=True)

    if comparison:
        SUMMARY_OUT.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
        print(f"Wrote {SUMMARY_OUT}", flush=True)
        gm3 = comparison.get("gm3_summary") or {}
        delta = (comparison.get("doctrine_alignment_summary") or {}).get(
            "A_vs_B_delta"
        ) or {}
        print(f"GM3 summary: {json.dumps(gm3)}", flush=True)
        print(f"A vs B delta: {json.dumps(delta)}", flush=True)

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

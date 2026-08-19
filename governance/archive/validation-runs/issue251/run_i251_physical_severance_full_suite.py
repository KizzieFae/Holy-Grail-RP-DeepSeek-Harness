#!/usr/bin/env python3
"""Issue #251 — full suite under physical/perceptual severance doctrine (Arm B only)."""

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

from i251_doctrine_alignment import evaluate_doctrine_alignment, summarize_doctrine_alignment
from i251_doctrine_preflight import build_physical_severance_preflight, extract_active_doctrine_slices
from i251_metrics import enrich_attempt_metrics
from i251_replay_adjudication import adjudicate_replay_row, summarize_adjudicated_vs_deterministic
from prompt_topology_issue240 import (
    ISSUE251_PHYSICAL_SEVERANCE_DOCTRINE_MARKER,
    apply_issue251_physical_severance_prompt_overrides,
    build_issue251_physical_severance_doctrine_block,
)
from run_i251_anchor_guard_experiment import (
    attempt_metrics,
    call_character_once,
    find_committed_artifact,
    scene_state_from_prompt,
    sys_prompt,
)

OUT_DIR = Path(__file__).resolve().parent
BROAD_PLAN = OUT_DIR / "i251_exit_stability_matrix_plan.json"
META_PLAN = OUT_DIR / "i251_physical_severance_full_suite_plan.meta.json"
MATRIX_OUT = OUT_DIR / "i251_physical_severance_full_suite_matrix.json"
ADJ_OUT = OUT_DIR / "i251_physical_severance_full_suite_matrix_adjudicated.json"
SUMMARY_OUT = OUT_DIR / "i251_physical_severance_full_suite_summary.json"
PREFLIGHT_OUT = OUT_DIR / "i251_physical_severance_full_suite_prompt_preflight.json"
GM3_MD = OUT_DIR / "i251_physical_severance_full_suite_gm3_summary.md"
ALIGNMENT_MD = OUT_DIR / "i251_physical_severance_full_suite_doctrine_alignment.md"

TOPOLOGY = "v1_next7_issue251_physical_severance_v1"
DOCTRINE_SCHEMA = "physical_severance_v1"


def load_suite_plan() -> dict[str, Any]:
    meta = json.loads(META_PLAN.read_text(encoding="utf-8"))
    broad = json.loads(BROAD_PLAN.read_text(encoding="utf-8"))
    overrides = meta.get("sample_n_overrides") or {}
    default_n = int(meta.get("sample_n_default") or 3)
    cases = []
    for spec in broad.get("cases") or []:
        if spec["case_id"] in set(meta.get("excluded_case_ids") or []):
            continue
        row = dict(spec)
        row["sample_n"] = int(overrides.get(spec["case_id"], default_n))
        cases.append(row)
    return {
        **meta,
        "cases": cases,
        "n_cases": len(cases),
        "estimated_samples": sum(c["sample_n"] for c in cases),
    }


def sample_n_for(case_id: str, plan: dict[str, Any]) -> int:
    overrides = plan.get("sample_n_overrides") or {}
    return int(overrides.get(case_id, plan.get("sample_n_default") or 3))


async def run_suite_sample(
    *,
    case_spec: dict[str, Any],
    sample_index: int,
) -> dict[str, Any]:
    case_id = case_spec["case_id"]
    session = case_spec["session"]
    rnd = int(case_spec["round"])
    turn = int(case_spec["turn"])
    actor = case_spec["actor"]

    committed_path = find_committed_artifact(session, rnd, turn, actor)
    if committed_path is None:
        return {
            "case_id": case_id,
            "sample_index": sample_index,
            "status": "artifact_missing",
        }

    audit = json.loads(committed_path.read_text(encoding="utf-8"))
    bot_name = str(audit.get("bot_name") or actor)
    original_prompt = sys_prompt(audit)
    if not original_prompt:
        raise ValueError(f"{case_id}: empty system prompt")

    arm_prompt = apply_issue251_physical_severance_prompt_overrides(original_prompt, bot_name)
    prompt_sha256 = hashlib.sha256(arm_prompt.encode("utf-8")).hexdigest()
    pf = build_physical_severance_preflight(arm_prompt)
    if not pf["contamination_clean"]:
        raise SystemExit(
            f"PREFLIGHT FAILED {case_id} arm sample {sample_index}: {pf['contamination_hits']}"
        )

    scene_state = scene_state_from_prompt(original_prompt)
    raw = await call_character_once(arm_prompt, bot_name)
    attempt = enrich_attempt_metrics(
        attempt_metrics(raw=raw, bot_name=bot_name, scene_state=scene_state),
        case_spec["doctrine_expected"],
    )

    expected_label = case_spec.get("expected_label") or case_spec["doctrine_expected"]
    row: dict[str, Any] = {
        "case_id": case_id,
        "category": case_spec.get("category"),
        "cohort": case_spec.get("cohort"),
        "doctrine_arm": "physical_severance",
        "doctrine_schema_version": DOCTRINE_SCHEMA,
        "topology": TOPOLOGY,
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
        "prompt_proof": {
            "topology": TOPOLOGY,
            "prompt_sha256": prompt_sha256,
            "required_markers": pf["required_markers_present"],
            "forbidden_active_absent": pf["forbidden_active_doctrine_absent"],
            "doctrine_block_matches_spec": pf["doctrine_block_matches_spec"],
            "active_doctrine_excerpt": pf["active_doctrine_excerpt"][:800],
        },
        "L1_deterministic": attempt,
        "first_attempt": attempt,
        "raw_response_excerpt": raw[:2000],
    }
    row["L2_adjudicated"] = adjudicate_replay_row(row)
    row["adjudication"] = row["L2_adjudicated"]
    row["L3_doctrine_alignment"] = evaluate_doctrine_alignment(
        doctrine_arm="physical_severance",
        doctrine_schema_version=DOCTRINE_SCHEMA,
        doctrine_expected=case_spec["doctrine_expected"],
        attempt=attempt,
        expected_label=expected_label,
        l3_rubric="Physical/perceptual severance completion at beat end.",
    )
    l3 = row["L3_doctrine_alignment"]
    adj = (row["adjudication"] or {}).get("adjudicated") or {}
    row["L3_doctrine_alignment"]["l243_ambiguity_disagrees_with_physical_doctrine"] = bool(
        adj.get("ambiguous_or_recoverable")
        and l3.get("doctrine_aligned") is True
    ) or bool(
        adj.get("ambiguous_or_recoverable")
        and case_spec["doctrine_expected"] == "off_focal"
        and attempt.get("decision") == "no_covered_change"
    )
    row["doctrine_alignment"] = row["L3_doctrine_alignment"]
    return row


def classify_row(row: dict[str, Any]) -> dict[str, Any]:
    fa = row.get("first_attempt") or {}
    s1 = fa.get("S1_semantic_intent_correct")
    s2 = fa.get("S2_structural_legality_pass")
    decision = fa.get("decision")
    kinds = list(fa.get("proposal_kinds") or [])
    expected = row.get("doctrine_expected")
    clean = bool(s2)
    if expected == "off_focal":
        correct = s1 is True and decision == "covered_change" and kinds == ["off_focal"]
        false_negative = clean and decision == "no_covered_change" and not kinds
        false_positive = False
    else:
        correct = s1 is True and decision == "no_covered_change" and "off_focal" not in kinds
        false_positive = clean and "off_focal" in kinds
        false_negative = False
    return {
        "outcome_correct": correct,
        "false_positive_off_focal": false_positive,
        "false_negative_missed_off_focal": false_negative,
        "clean_interpretable": clean,
    }


def build_summary(rows: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    ok_rows = [r for r in rows if r.get("status") != "artifact_missing"]
    for r in ok_rows:
        r["metrics"] = classify_row(r)

    exits = [r for r in ok_rows if r.get("cohort") == "exit"]
    non_exits = [r for r in ok_rows if r.get("cohort") == "non_exit"]
    gm3 = [r for r in ok_rows if r.get("case_id") == "EXIT-C-GM3"]
    threshold = [
        r
        for r in exits
        if r.get("category") in ("C_temporary_departure", "D_threshold_hesitation")
        and r.get("case_id") != "EXIT-C-GM3"
    ]
    explicit = [
        r for r in exits if r.get("category") in ("A_quiet_practical", "B_emotional_departure")
    ]

    def rate(items: list[dict], key: str) -> float | None:
        vals = [(r.get("first_attempt") or {}).get(key) for r in items]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 3)

    def l3_rate(items: list[dict]) -> float | None:
        vals = [(r.get("doctrine_alignment") or {}).get("doctrine_aligned") for r in items]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 3)

    def adj_rate(items: list[dict]) -> float | None:
        vals = [
            (r.get("adjudication") or {}).get("adjudicated", {}).get(
                "adjudicated_semantically_correct"
            )
            for r in items
        ]
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        return round(sum(1 for v in vals if v) / len(vals), 3)

    clean_exits = [r for r in exits if (r.get("first_attempt") or {}).get("S2_structural_legality_pass")]
    guard_fp = sum(
        1
        for r in non_exits
        if "off_focal" in ((r.get("first_attempt") or {}).get("proposal_kinds") or [])
    )

    adjudications = [r.get("adjudication") or {} for r in ok_rows]
    l3_summary = summarize_doctrine_alignment(ok_rows)
    adj_summary = summarize_adjudicated_vs_deterministic(ok_rows, adjudications=adjudications)

    preflight_by_case: dict[str, Any] = {}
    for r in ok_rows:
        cid = r["case_id"]
        if cid not in preflight_by_case:
            preflight_by_case[cid] = {
                "case_id": cid,
                "prompt_sha256": r.get("prompt_sha256"),
                "preflight": r.get("preflight"),
                "prompt_proof": r.get("prompt_proof"),
            }

    return {
        "experiment_id": plan.get("experiment_id"),
        "generated_at": datetime.now(UTC).isoformat(),
        "topology": TOPOLOGY,
        "doctrine_schema_version": DOCTRINE_SCHEMA,
        "n_cases": plan.get("n_cases"),
        "n_samples": len(ok_rows),
        "all_samples_adjudicated": all(r.get("adjudication") for r in ok_rows),
        "all_samples_l3": all(r.get("doctrine_alignment") for r in ok_rows),
        "all_preflight_clean": all((r.get("preflight") or {}).get("contamination_clean") for r in ok_rows),
        "aggregate": {
            "S1_rate": rate(ok_rows, "S1_semantic_intent_correct"),
            "S2_clean_S1_rate": rate(clean_exits + [r for r in non_exits if (r.get("first_attempt") or {}).get("S2_structural_legality_pass")], "S1_semantic_intent_correct"),
            "L3_alignment_rate": l3_rate(ok_rows),
            "adjudicated_correct_rate": adj_rate(ok_rows),
            "ambiguous_rate": round(
                sum(
                    1
                    for r in ok_rows
                    if (r.get("adjudication") or {})
                    .get("adjudicated", {})
                    .get("ambiguous_or_recoverable")
                )
                / max(len(ok_rows), 1),
                3,
            ),
            "guard_false_off_focal_count": guard_fp,
            "guard_false_off_focal_rate": round(guard_fp / max(len(non_exits), 1), 3),
        },
        "gm3": {
            "n": len(gm3),
            "S1_pass": sum(1 for r in gm3 if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")),
            "S2_clean_S1_pass": sum(
                1
                for r in gm3
                if (r.get("first_attempt") or {}).get("S2_structural_legality_pass")
                and (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
            ),
            "L3_aligned": sum(1 for r in gm3 if (r.get("doctrine_alignment") or {}).get("doctrine_aligned")),
            "adjudicated_ok": sum(
                1
                for r in gm3
                if (r.get("adjudication") or {}).get("adjudicated", {}).get("adjudicated_semantically_correct") is True
            ),
            "ambiguous": sum(
                1
                for r in gm3
                if (r.get("adjudication") or {}).get("adjudicated", {}).get("ambiguous_or_recoverable")
            ),
        },
        "threshold_exits": {
            "n": len(threshold),
            "S1_rate": rate(threshold, "S1_semantic_intent_correct"),
            "L3_rate": l3_rate(threshold),
            "adj_rate": adj_rate(threshold),
        },
        "explicit_exits": {
            "n": len(explicit),
            "S1_rate": rate(explicit, "S1_semantic_intent_correct"),
            "L3_rate": l3_rate(explicit),
        },
        "non_exit_guards": {
            "n": len(non_exits),
            "S1_rate": rate(non_exits, "S1_semantic_intent_correct"),
            "false_off_focal": guard_fp,
        },
        "adjudication_summary": adj_summary,
        "doctrine_alignment_summary": l3_summary,
        "preflight_by_case": preflight_by_case,
    }


def write_gm3_md(summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    gm3 = [r for r in rows if r.get("case_id") == "EXIT-C-GM3"]
    lines = [
        "# GM3 — physical/perceptual severance full suite",
        "",
        f"Generated: {summary.get('generated_at')}",
        f"Topology: `{TOPOLOGY}`",
        "",
        "## Aggregate",
        "",
        f"- Samples: {summary['gm3']['n']}",
        f"- S1 pass: {summary['gm3']['S1_pass']}/{summary['gm3']['n']}",
        f"- L3 aligned: {summary['gm3']['L3_aligned']}/{summary['gm3']['n']}",
        f"- Adjudicated OK: {summary['gm3']['adjudicated_ok']}",
        f"- Ambiguous (L2): {summary['gm3']['ambiguous']}",
        "",
        "## Per-sample",
        "",
    ]
    for r in gm3:
        fa = r.get("first_attempt") or {}
        adj = (r.get("adjudication") or {}).get("adjudicated") or {}
        l3 = r.get("doctrine_alignment") or {}
        lines.append(
            f"- sample {r.get('sample_index')}: dec={fa.get('decision')} S1={fa.get('S1_semantic_intent_correct')} "
            f"S2={fa.get('S2_structural_legality_pass')} L3={l3.get('doctrine_aligned')} "
            f"L2_amb={adj.get('ambiguous_or_recoverable')} L2_ok={adj.get('adjudicated_semantically_correct')}"
        )
    GM3_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_alignment_md(summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    divergent = []
    for r in rows:
        fa = r.get("first_attempt") or {}
        adj = (r.get("adjudication") or {}).get("adjudicated") or {}
        l3 = r.get("doctrine_alignment") or {}
        s1 = fa.get("S1_semantic_intent_correct")
        l3a = l3.get("doctrine_aligned")
        l2 = adj.get("adjudicated_semantically_correct")
        if s1 != l3a or (l2 is not None and l2 != l3a and not adj.get("ambiguous_or_recoverable")):
            divergent.append(r)
    lines = [
        "# L1 / L2 / L3 doctrine alignment — physical severance full suite",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "## Layer agreement",
        "",
        f"- L3 alignment rate: {summary['aggregate']['L3_alignment_rate']}",
        f"- Adjudicated correct rate: {summary['aggregate']['adjudicated_correct_rate']}",
        f"- Ambiguous rate (L2): {summary['aggregate']['ambiguous_rate']}",
        "",
        f"## Divergent samples (n={len(divergent)})",
        "",
    ]
    for r in divergent[:40]:
        fa = r.get("first_attempt") or {}
        adj = (r.get("adjudication") or {}).get("adjudicated") or {}
        l3 = r.get("doctrine_alignment") or {}
        lines.append(
            f"- {r.get('case_id')} sample {r.get('sample_index')}: S1={fa.get('S1_semantic_intent_correct')} "
            f"L2={adj.get('adjudicated_semantically_correct')} amb={adj.get('ambiguous_or_recoverable')} "
            f"L3={l3.get('doctrine_aligned')}"
        )
    ALIGNMENT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_experiment(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    plan = load_suite_plan()
    print(
        f"Suite: {plan['n_cases']} cases, ~{plan['estimated_samples']} samples, topology={TOPOLOGY}",
        flush=True,
    )

    # Prove prompt on GM3 before full run
    gm3_path = find_committed_artifact("session_912", 1, 12, "willow_reeves")
    if gm3_path:
        audit = json.loads(gm3_path.read_text(encoding="utf-8"))
        bot = str(audit.get("bot_name") or "Willow_Reeves")
        proof_prompt = apply_issue251_physical_severance_prompt_overrides(sys_prompt(audit), bot)
        proof_pf = build_physical_severance_preflight(proof_prompt)
        if not proof_pf["contamination_clean"]:
            raise SystemExit(f"GM3 preflight proof failed: {proof_pf['contamination_hits']}")
        print(f"GM3 preflight proof OK sha={hashlib.sha256(proof_prompt.encode()).hexdigest()[:16]}", flush=True)

    all_rows: list[dict[str, Any]] = []
    for spec in plan["cases"]:
        n = spec["sample_n"]
        for sample_index in range(n):
            print(f"=== {spec['case_id']} sample {sample_index + 1}/{n} ===", flush=True)
            if dry_run:
                all_rows.append({"case_id": spec["case_id"], "sample_index": sample_index, "dry_run": True})
                continue
            row = await run_suite_sample(case_spec=spec, sample_index=sample_index)
            fa = row.get("first_attempt") or {}
            print(
                f"  S1={fa.get('S1_semantic_intent_correct')} S2={fa.get('S2_structural_legality_pass')} "
                f"L3={(row.get('doctrine_alignment') or {}).get('doctrine_aligned')} dec={fa.get('decision')}",
                flush=True,
            )
            all_rows.append(row)

    summary = build_summary(all_rows, plan) if not dry_run else {}
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_id": plan.get("experiment_id"),
        "status": "dry_run" if dry_run else "complete",
        "topology": TOPOLOGY,
        "doctrine_schema_version": DOCTRINE_SCHEMA,
        "doctrine_era": "physical_severance_v1",
        "plan": {"n_cases": plan.get("n_cases"), "estimated_samples": plan.get("estimated_samples")},
        "samples": all_rows,
        "summary": summary,
    }

    MATRIX_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    adj_payload = {**payload, "adjudication_summary": summary.get("adjudication_summary")}
    ADJ_OUT.write_text(json.dumps(adj_payload, indent=2), encoding="utf-8")
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    PREFLIGHT_OUT.write_text(
        json.dumps(summary.get("preflight_by_case") or {}, indent=2), encoding="utf-8"
    )
    if not dry_run:
        write_gm3_md(summary, all_rows)
        write_alignment_md(summary, all_rows)

    print(f"\nWrote {MATRIX_OUT}", flush=True)
    print(f"Wrote {ADJ_OUT}", flush=True)
    print(f"Wrote {SUMMARY_OUT}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

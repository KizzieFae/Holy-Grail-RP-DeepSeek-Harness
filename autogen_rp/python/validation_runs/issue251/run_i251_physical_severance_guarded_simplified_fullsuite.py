#!/usr/bin/env python3
"""Issue #251 — full 103-sample suite under simplified structural Arm C doctrine."""

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
from i251_doctrine_preflight import (
    active_physical_severance_guarded_contamination_hits,
    build_physical_severance_guarded_preflight,
    extract_active_doctrine_slices,
)
from i251_metrics import enrich_attempt_metrics
from i251_replay_adjudication import adjudicate_replay_row, summarize_adjudicated_vs_deterministic
from prompt_topology_issue240 import (
    ISSUE251_PHYSICAL_SEVERANCE_GUARDED_ISOLATION_MARKER,
    apply_issue251_physical_severance_guarded_prompt_overrides,
    build_issue251_physical_severance_guarded_doctrine_block,
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
META_PLAN = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_plan.meta.json"
ARM_B_MATRIX = OUT_DIR / "i251_physical_severance_full_suite_matrix.json"
OLD_ARM_C_MATRIX = OUT_DIR / "i251_physical_severance_guarded_suite_matrix.json"
FOCUSED_MATRIX = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_matrix.json"

MATRIX_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_matrix.json"
ADJ_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_matrix_adjudicated.json"
SUMMARY_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_summary.json"
PREFLIGHT_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_preflight.json"
GM3_MD = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_gm3_summary.md"
GUARD_DELTA_MD = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_guard_delta.md"
COMPARISON_MD = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_comparison.md"
DRAFT_COMMENT = OUT_DIR / "i251_physical_severance_guarded_simplified_fullsuite_draft_issue_comment.md"

TOPOLOGY = "v1_next7_issue251_physical_severance_guarded_v1"
DOCTRINE_SCHEMA = "physical_severance_guarded_v1"
DOCTRINE_ARM = "physical_severance_guarded"
DOCTRINE_VARIANT = "simplified_structural_v1"

ARM_B_FP_CASES = frozenset(
    {
        "NE-900T5",
        "NE-901T11",
        "NE-901T5",
        "NE-910R10",
        "NE-910R11",
        "NE-910R12",
        "NE-910R3T3",
        "NE-CTRL-GM2",
        "NE-GM4",
        "NE-P02",
        "NE-P05",
    }
)

FORBIDDEN_OLD_IN_ACTIVE = (
    "perceptual severance",
    "ordinary unaided",
    "shared scene boundary",
    "exit arc",
    "Canonical positive",
    "temporary-task framing alone",
    "shared-awareness continuity",
    "all four",
    "doorway tether",
)

KEY_CASES = ("NE-900T5", "NE-P02", "NE-901T5", "NE-GM4", "EXIT-B-910R5T3", "EXIT-C-GM3")


def load_suite_plan() -> dict[str, Any]:
    meta = json.loads(META_PLAN.read_text(encoding="utf-8"))
    broad = json.loads(BROAD_PLAN.read_text(encoding="utf-8"))
    overrides = meta.get("sample_n_overrides") or {}
    default_n = int(meta.get("sample_n_default") or 3)
    excluded = set(meta.get("excluded_case_ids") or [])
    cases = []
    for spec in broad.get("cases") or []:
        if spec["case_id"] in excluded:
            continue
        row = dict(spec)
        row["sample_n"] = int(overrides.get(spec["case_id"], default_n))
        cases.append(row)
    return {
        **meta,
        "cases": cases,
        "n_cases": len(cases),
        "estimated_samples": sum(c["sample_n"] for c in cases),
        "excluded_case_ids": sorted(excluded),
    }


def _fp_key(row: dict[str, Any]) -> bool:
    return "off_focal" in ((row.get("first_attempt") or {}).get("proposal_kinds") or [])


def _load_index(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        (r["case_id"], r["sample_index"]): r
        for r in data.get("samples") or []
        if r.get("status") != "artifact_missing" and not r.get("dry_run")
    }


def _suite_metrics(rows: list[dict]) -> dict[str, Any]:
    ok = [r for r in rows if r.get("status") != "artifact_missing"]
    guards = [r for r in ok if r.get("cohort") == "non_exit"]
    gm3 = [r for r in ok if r.get("case_id") == "EXIT-C-GM3"]
    exits = [r for r in ok if r.get("cohort") == "exit"]
    threshold = [
        r
        for r in exits
        if r.get("category") in ("C_temporary_departure", "D_threshold_hesitation")
        and r.get("case_id") != "EXIT-C-GM3"
    ]
    explicit = [
        r for r in exits if r.get("category") in ("A_quiet_practical", "B_emotional_departure")
    ]

    def s1_pass(rs: list[dict]) -> int:
        return sum(1 for r in rs if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct"))

    def rate(rs: list[dict], key: str) -> float | None:
        vals = [(r.get("first_attempt") or {}).get(key) for r in rs]
        vals = [v for v in vals if v is not None]
        return round(sum(1 for v in vals if v) / len(vals), 3) if vals else None

    guard_fp = sum(1 for r in guards if _fp_key(r))
    return {
        "n_samples": len(ok),
        "guard_n": len(guards),
        "guard_false_off_focal": guard_fp,
        "guard_fp_rate": round(guard_fp / max(len(guards), 1), 3),
        "gm3_n": len(gm3),
        "gm3_S1_pass": s1_pass(gm3),
        "gm3_L3_pass": sum(
            1 for r in gm3 if (r.get("doctrine_alignment") or {}).get("doctrine_aligned")
        ),
        "threshold_n": len(threshold),
        "threshold_S1_rate": rate(threshold, "S1_semantic_intent_correct"),
        "explicit_n": len(explicit),
        "explicit_S1_rate": rate(explicit, "S1_semantic_intent_correct"),
        "S1_rate": rate(ok, "S1_semantic_intent_correct"),
        "ambiguous_rate": round(
            sum(
                1
                for r in ok
                if (r.get("adjudication") or {})
                .get("adjudicated", {})
                .get("ambiguous_or_recoverable")
            )
            / max(len(ok), 1),
            3,
        ),
    }


async def run_sample(*, case_spec: dict[str, Any], sample_index: int) -> dict[str, Any]:
    case_id = case_spec["case_id"]
    session = case_spec["session"]
    rnd = int(case_spec["round"])
    turn = int(case_spec["turn"])
    actor = case_spec["actor"]

    committed_path = find_committed_artifact(session, rnd, turn, actor)
    if committed_path is None:
        return {"case_id": case_id, "sample_index": sample_index, "status": "artifact_missing"}

    audit = json.loads(committed_path.read_text(encoding="utf-8"))
    bot_name = str(audit.get("bot_name") or actor)
    original_prompt = sys_prompt(audit)
    if not original_prompt:
        raise ValueError(f"{case_id}: empty system prompt")

    arm_prompt = apply_issue251_physical_severance_guarded_prompt_overrides(original_prompt, bot_name)
    prompt_sha256 = hashlib.sha256(arm_prompt.encode("utf-8")).hexdigest()
    pf = build_physical_severance_guarded_preflight(arm_prompt)
    if not pf["contamination_clean"]:
        raise SystemExit(
            f"PREFLIGHT FAILED {case_id} sample {sample_index}: {pf['contamination_hits']}"
        )

    slices = extract_active_doctrine_slices(
        arm_prompt, isolation_marker=ISSUE251_PHYSICAL_SEVERANCE_GUARDED_ISOLATION_MARKER
    )
    forbidden_in_active = [p for p in FORBIDDEN_OLD_IN_ACTIVE if p in slices["semantic_doctrine_slice"]]

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
        "doctrine_arm": DOCTRINE_ARM,
        "doctrine_schema_version": DOCTRINE_SCHEMA,
        "doctrine_variant": DOCTRINE_VARIANT,
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
            "doctrine_variant": DOCTRINE_VARIANT,
            "prompt_sha256": prompt_sha256,
            "required_markers": pf["required_markers_present"],
            "forbidden_active_absent": pf["forbidden_active_doctrine_absent"],
            "forbidden_old_phrases_in_active_slice": forbidden_in_active,
            "doctrine_block_matches_spec": pf["doctrine_block_matches_spec"],
        },
        "L1_deterministic": attempt,
        "first_attempt": attempt,
        "raw_response_excerpt": raw[:2000],
    }
    row["L2_adjudicated"] = adjudicate_replay_row(row)
    row["adjudication"] = row["L2_adjudicated"]
    row["L3_doctrine_alignment"] = evaluate_doctrine_alignment(
        doctrine_arm=DOCTRINE_ARM,
        doctrine_schema_version=DOCTRINE_SCHEMA,
        doctrine_expected=case_spec["doctrine_expected"],
        attempt=attempt,
        expected_label=expected_label,
    )
    row["doctrine_alignment"] = row["L3_doctrine_alignment"]
    return row


def build_summary(rows: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    ok_rows = [r for r in rows if r.get("status") != "artifact_missing"]
    adjudications = [r.get("adjudication") or {} for r in ok_rows]

    non_exits = [r for r in ok_rows if r.get("cohort") == "non_exit"]
    guard_fp = sum(1 for r in non_exits if _fp_key(r))
    fp_cases = [r for r in non_exits if r.get("case_id") in ARM_B_FP_CASES]
    fp_case_fp = sum(1 for r in fp_cases if _fp_key(r))

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

    current = _suite_metrics(ok_rows)
    arm_b = _suite_metrics(list(_load_index(ARM_B_MATRIX).values())) if ARM_B_MATRIX.is_file() else {}
    old_c = (
        _suite_metrics(list(_load_index(OLD_ARM_C_MATRIX).values()))
        if OLD_ARM_C_MATRIX.is_file()
        else {}
    )
    focused_idx = _load_index(FOCUSED_MATRIX)
    focused = _suite_metrics(list(focused_idx.values())) if focused_idx else {}

    return {
        "experiment_id": plan["experiment_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "topology": TOPOLOGY,
        "doctrine_schema_version": DOCTRINE_SCHEMA,
        "doctrine_variant": DOCTRINE_VARIANT,
        "n_cases": plan["n_cases"],
        "n_samples": len(ok_rows),
        "excluded_case_ids": plan.get("excluded_case_ids"),
        "all_samples_adjudicated": all(r.get("adjudication") for r in ok_rows),
        "all_samples_l3": all(r.get("doctrine_alignment") for r in ok_rows),
        "all_preflight_clean": all(
            (r.get("preflight") or {}).get("contamination_clean") for r in ok_rows
        ),
        "simplified_fullsuite": current,
        "baseline_arm_b": arm_b,
        "baseline_old_arm_c": old_c,
        "baseline_focused_simplified": focused,
        "non_exit_guards": {
            "n": current.get("guard_n"),
            "false_off_focal": guard_fp,
            "S1_rate": current.get("S1_rate"),
        },
        "gm3": {
            "n": current.get("gm3_n"),
            "S1_pass": current.get("gm3_S1_pass"),
            "L3_aligned": current.get("gm3_L3_pass"),
        },
        "threshold_exits": {
            "n": current.get("threshold_n"),
            "S1_rate": current.get("threshold_S1_rate"),
        },
        "explicit_exits": {
            "n": current.get("explicit_n"),
            "S1_rate": current.get("explicit_S1_rate"),
        },
        "aggregate": {
            "guard_false_off_focal_count": guard_fp,
            "guard_false_off_focal_rate": current.get("guard_fp_rate"),
            "arm_b_fp_case_guard_false_count": fp_case_fp,
            "arm_b_fp_case_guard_n": len(fp_cases),
            "S1_rate": current.get("S1_rate"),
            "ambiguous_rate": current.get("ambiguous_rate"),
        },
        "adjudication_summary": summarize_adjudicated_vs_deterministic(
            ok_rows, adjudications=adjudications
        ),
        "doctrine_alignment_summary": summarize_doctrine_alignment(ok_rows),
        "preflight_by_case": preflight_by_case,
        "doctrine_block_sha256": hashlib.sha256(
            build_issue251_physical_severance_guarded_doctrine_block().encode()
        ).hexdigest(),
    }


def _case_table(rows: list[dict], case_id: str, b_idx: dict, c_idx: dict, f_idx: dict) -> list[str]:
    case_rows = sorted([r for r in rows if r.get("case_id") == case_id], key=lambda x: x["sample_index"])
    lines = [f"### {case_id}", ""]
    fp_s = sum(1 for r in case_rows if _fp_key(r))
    lines.append(f"- Samples: {len(case_rows)} | Simplified FP: {fp_s}")
    for r in case_rows:
        si = r["sample_index"]
        fa = r.get("first_attempt") or {}
        exp = r.get("doctrine_expected")
        lines.append(
            f"  - si{si}: dec={fa.get('decision')} kinds={fa.get('proposal_kinds')} "
            f"S1={fa.get('S1_semantic_intent_correct')} exp={exp}"
        )
        for label, idx in (("B", b_idx), ("oldC", c_idx), ("focused", f_idx)):
            br = idx.get((case_id, si))
            if br:
                bfa = br.get("first_attempt") or {}
                lines.append(
                    f"    - {label}: dec={bfa.get('decision')} kinds={bfa.get('proposal_kinds')}"
                )
    lines.append("")
    return lines


def write_comparison_md(summary: dict, rows: list[dict]) -> None:
    cur = summary["simplified_fullsuite"]
    b = summary.get("baseline_arm_b") or {}
    oc = summary.get("baseline_old_arm_c") or {}
    fc = summary.get("baseline_focused_simplified") or {}
    b_idx = _load_index(ARM_B_MATRIX)
    c_idx = _load_index(OLD_ARM_C_MATRIX)
    f_idx = _load_index(FOCUSED_MATRIX)

    lines = [
        "# Full-suite comparison — simplified structural Arm C",
        "",
        f"Generated: {summary.get('generated_at')}",
        f"Samples: {summary.get('n_samples')} | Excluded: {summary.get('excluded_case_ids')}",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Simplified (full) | Arm B | Old Arm C | Focused simplified |",
        "|--------|-----------------|-------|-----------|-------------------|",
        f"| Guard false `off_focal` | {cur.get('guard_false_off_focal')}/{cur.get('guard_n')} ({cur.get('guard_fp_rate')}) | "
        f"{b.get('guard_false_off_focal', '—')}/{b.get('guard_n', '—')} ({b.get('guard_fp_rate', '—')}) | "
        f"{oc.get('guard_false_off_focal', '—')}/{oc.get('guard_n', '—')} ({oc.get('guard_fp_rate', '—')}) | "
        f"{fc.get('guard_false_off_focal', '—')}/{fc.get('guard_n', '—')} ({fc.get('guard_fp_rate', '—')}) |",
        f"| GM3 S1/L3 | {cur.get('gm3_S1_pass')}/{cur.get('gm3_n')} | "
        f"{b.get('gm3_S1_pass', '—')}/{b.get('gm3_n', '—')} | "
        f"{oc.get('gm3_S1_pass', '—')}/{oc.get('gm3_n', '—')} | "
        f"{fc.get('gm3_S1_pass', '—')}/{fc.get('gm3_n', '—')} |",
        f"| Threshold exit S1 rate | {cur.get('threshold_S1_rate')} | {b.get('threshold_S1_rate', '—')} | "
        f"{oc.get('threshold_S1_rate', '—')} | — |",
        f"| Explicit exit S1 rate | {cur.get('explicit_S1_rate')} | {b.get('explicit_S1_rate', '—')} | "
        f"{oc.get('explicit_S1_rate', '—')} | — |",
        f"| Ambiguous (L2) | {cur.get('ambiguous_rate')} | {b.get('ambiguous_rate', '—')} | "
        f"{oc.get('ambiguous_rate', '—')} | {fc.get('ambiguous_rate', '—')} |",
        "",
        "## Key cases",
        "",
    ]
    ok_rows = [r for r in rows if r.get("status") != "artifact_missing"]
    for cid in KEY_CASES:
        lines.extend(_case_table(ok_rows, cid, b_idx, c_idx, f_idx))

    COMPARISON_MD.write_text("\n".join(lines), encoding="utf-8")


def write_guard_delta(summary: dict, rows: list[dict]) -> None:
    b_idx = _load_index(ARM_B_MATRIX)
    c_idx = _load_index(OLD_ARM_C_MATRIX)
    guards = [r for r in rows if r.get("cohort") == "non_exit" and r.get("status") != "artifact_missing"]
    agg = summary["aggregate"]
    lines = [
        "# Guard false `off_focal` — simplified full suite",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "## Aggregate",
        "",
        f"| Source | guard FP | n |",
        f"|--------|----------|---|",
        f"| **Simplified full** | {agg['guard_false_off_focal_count']} | {summary['non_exit_guards']['n']} |",
    ]
    for label, key in (
        ("Arm B", "baseline_arm_b"),
        ("Old Arm C", "baseline_old_arm_c"),
        ("Focused", "baseline_focused_simplified"),
    ):
        bl = summary.get(key) or {}
        lines.append(
            f"| {label} | {bl.get('guard_false_off_focal', '—')} | {bl.get('guard_n', '—')} |"
        )
    lines.append("")
    by_case: dict[str, list] = defaultdict(list)
    for r in guards:
        by_case[r["case_id"]].append(r)
    for cid in sorted(by_case.keys()):
        crs = sorted(by_case[cid], key=lambda x: x["sample_index"])
        fp = sum(1 for r in crs if _fp_key(r))
        fp_b = sum(1 for r in crs if _fp_key(b_idx.get((cid, r["sample_index"]), {})))
        fp_c = sum(1 for r in crs if _fp_key(c_idx.get((cid, r["sample_index"]), {})))
        lines.append(f"### {cid}: simplified {fp}/{len(crs)} | B {fp_b} | oldC {fp_c}")
    GUARD_DELTA_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gm3_md(summary: dict, rows: list[dict]) -> None:
    gm3 = sorted(
        [r for r in rows if r.get("case_id") == "EXIT-C-GM3"],
        key=lambda x: x["sample_index"],
    )
    g = summary["gm3"]
    lines = [
        "# GM3 — simplified structural full suite",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        f"| Source | S1/L3 pass |",
        f"|--------|------------|",
        f"| Simplified full | {g['S1_pass']}/{g['n']} |",
        f"| Arm B | {summary.get('baseline_arm_b', {}).get('gm3_S1_pass', '—')}/10 |",
        f"| Old Arm C | {summary.get('baseline_old_arm_c', {}).get('gm3_S1_pass', '—')}/10 |",
        f"| Focused | {summary.get('baseline_focused_simplified', {}).get('gm3_S1_pass', '—')}/10 |",
        "",
        "## Per-sample",
        "",
    ]
    for r in gm3:
        fa = r.get("first_attempt") or {}
        l3 = r.get("doctrine_alignment") or {}
        adj = (r.get("adjudication") or {}).get("adjudicated") or {}
        lines.append(
            f"- sample {r['sample_index']}: dec={fa.get('decision')} S1={fa.get('S1_semantic_intent_correct')} "
            f"L3={l3.get('doctrine_aligned')} L2_amb={adj.get('ambiguous_or_recoverable')}"
        )
    GM3_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_draft_comment(summary: dict) -> None:
    cur = summary["simplified_fullsuite"]
    b = summary.get("baseline_arm_b") or {}
    oc = summary.get("baseline_old_arm_c") or {}
    text = f"""## §B.5 — simplified structural Arm C full suite (draft)

**Status:** Full 103-sample suite complete. **Not** validated. **Not** production.

### Suite

- Topology: `{TOPOLOGY}`
- Doctrine variant: `{DOCTRINE_VARIANT}`
- Samples: {summary['n_samples']} (n=32 cohort; excluded {summary.get('excluded_case_ids')})
- Preflight: **{'all clean' if summary['all_preflight_clean'] else 'FAILURES'}**

### Headline

| Metric | Simplified | Arm B | Old Arm C |
|--------|------------|-------|-----------|
| Guard false `off_focal` | {cur.get('guard_false_off_focal')}/{cur.get('guard_n')} | {b.get('guard_false_off_focal', '—')}/{b.get('guard_n', '—')} | {oc.get('guard_false_off_focal', '—')}/{oc.get('guard_n', '—')} |
| GM3 S1 | {cur.get('gm3_S1_pass')}/10 | {b.get('gm3_S1_pass', '—')}/10 | {oc.get('gm3_S1_pass', '—')}/10 |

### Artifacts

- `i251_physical_severance_guarded_simplified_fullsuite_matrix.json`
- `i251_physical_severance_guarded_simplified_fullsuite_summary.json`
- `i251_physical_severance_guarded_simplified_fullsuite_comparison.md`

### Next

- Governance canonization review if metrics hold on key cases (NE-GM4, EXIT-B).
- Do **not** close #251 without explicit sign-off.
"""
    DRAFT_COMMENT.write_text(text, encoding="utf-8")


async def run_experiment(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    plan = load_suite_plan()
    print(
        f"Full suite: {plan['n_cases']} cases, ~{plan['estimated_samples']} samples, "
        f"variant={DOCTRINE_VARIANT}",
        flush=True,
    )

    gm3_path = find_committed_artifact("session_912", 1, 12, "willow_reeves")
    if gm3_path:
        audit = json.loads(gm3_path.read_text(encoding="utf-8"))
        bot = str(audit.get("bot_name") or "Willow_Reeves")
        proof = apply_issue251_physical_severance_guarded_prompt_overrides(sys_prompt(audit), bot)
        pf = build_physical_severance_guarded_preflight(proof)
        hits = active_physical_severance_guarded_contamination_hits(proof)
        if not pf["contamination_clean"] or hits:
            raise SystemExit(f"Preflight/contamination failed: {pf.get('contamination_hits')} {hits}")
        print(f"Preflight proof OK sha={hashlib.sha256(proof.encode()).hexdigest()[:16]}", flush=True)

    all_rows: list[dict[str, Any]] = []
    for spec in plan["cases"]:
        n = spec["sample_n"]
        for sample_index in range(n):
            print(f"=== {spec['case_id']} sample {sample_index + 1}/{n} ===", flush=True)
            if dry_run:
                all_rows.append({"case_id": spec["case_id"], "sample_index": sample_index, "dry_run": True})
                continue
            row = await run_sample(case_spec=spec, sample_index=sample_index)
            fa = row.get("first_attempt") or {}
            print(
                f"  S1={fa.get('S1_semantic_intent_correct')} L3={(row.get('doctrine_alignment') or {}).get('doctrine_aligned')} "
                f"dec={fa.get('decision')} kinds={fa.get('proposal_kinds')}",
                flush=True,
            )
            all_rows.append(row)

    summary = build_summary(all_rows, plan) if not dry_run else {}
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "experiment_id": plan["experiment_id"],
        "status": "dry_run" if dry_run else "complete",
        "topology": TOPOLOGY,
        "doctrine_schema_version": DOCTRINE_SCHEMA,
        "doctrine_variant": DOCTRINE_VARIANT,
        "plan": {
            "n_cases": plan["n_cases"],
            "estimated_samples": plan["estimated_samples"],
            "excluded_case_ids": plan.get("excluded_case_ids"),
        },
        "samples": all_rows,
        "summary": summary,
    }

    MATRIX_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    ADJ_OUT.write_text(
        json.dumps({**payload, "adjudication_summary": summary.get("adjudication_summary")}, indent=2),
        encoding="utf-8",
    )
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    PREFLIGHT_OUT.write_text(json.dumps(summary.get("preflight_by_case") or {}, indent=2), encoding="utf-8")
    if not dry_run:
        write_guard_delta(summary, all_rows)
        write_gm3_md(summary, all_rows)
        write_comparison_md(summary, all_rows)
        write_draft_comment(summary)

    print(f"\nWrote {MATRIX_OUT}", flush=True)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_experiment(dry_run=args.dry_run))


if __name__ == "__main__":
    main()

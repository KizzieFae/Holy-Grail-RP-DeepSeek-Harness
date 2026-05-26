#!/usr/bin/env python3
"""Issue #251 — focused rerun under simplified Arm C guarded doctrine."""

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
META_PLAN = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_plan.meta.json"
ARM_B_MATRIX = OUT_DIR / "i251_physical_severance_full_suite_matrix.json"
OLD_ARM_C_MATRIX = OUT_DIR / "i251_physical_severance_guarded_suite_matrix.json"

MATRIX_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_matrix.json"
ADJ_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_matrix_adjudicated.json"
SUMMARY_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_summary.json"
PREFLIGHT_OUT = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_preflight.json"
GM3_MD = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_gm3_summary.md"
GUARD_DELTA_MD = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_guard_delta.md"
DRAFT_COMMENT = OUT_DIR / "i251_physical_severance_guarded_simplified_focused_draft_issue_comment.md"

TOPOLOGY = "v1_next7_issue251_physical_severance_guarded_v1"
DOCTRINE_SCHEMA = "physical_severance_guarded_v1"
DOCTRINE_ARM = "physical_severance_guarded"
DOCTRINE_VARIANT = "simplified_structural_v1"

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


def load_focused_plan() -> dict[str, Any]:
    meta = json.loads(META_PLAN.read_text(encoding="utf-8"))
    broad = json.loads(BROAD_PLAN.read_text(encoding="utf-8"))
    focused_ids = set(meta["focused_case_ids"])
    overrides = meta.get("sample_n_overrides") or {}
    default_n = int(meta.get("sample_n_default") or 3)
    cases = []
    for spec in broad["cases"]:
        if spec["case_id"] not in focused_ids:
            continue
        row = dict(spec)
        row["sample_n"] = int(overrides.get(spec["case_id"], default_n))
        cases.append(row)
    missing = focused_ids - {c["case_id"] for c in cases}
    if missing:
        raise SystemExit(f"Focused plan missing case_ids: {sorted(missing)}")
    return {
        **meta,
        "cases": cases,
        "n_cases": len(cases),
        "estimated_samples": sum(c["sample_n"] for c in cases),
    }


def _fp_key(row: dict[str, Any]) -> bool:
    return "off_focal" in ((row.get("first_attempt") or {}).get("proposal_kinds") or [])


def _load_baseline_index(path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        (r["case_id"], r["sample_index"]): r
        for r in data.get("samples") or []
        if r.get("status") != "artifact_missing"
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
    active = slices["semantic_doctrine_slice"]
    forbidden_in_active = [p for p in FORBIDDEN_OLD_IN_ACTIVE if p in active]

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
        "focused_group": _focused_group(case_id),
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
            "active_doctrine_excerpt": pf["active_doctrine_excerpt"][:1200],
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


def _focused_group(case_id: str) -> str:
    meta = json.loads(META_PLAN.read_text(encoding="utf-8"))
    groups = meta.get("cohort_groups") or {}
    for name, ids in groups.items():
        if case_id in ids:
            return name
    return "other"


def _cohort_rows(rows: list[dict], group: str) -> list[dict]:
    return [r for r in rows if r.get("focused_group") == group]


def _group_stats(items: list[dict]) -> dict[str, Any]:
    if not items:
        return {"n": 0}
    guards = [r for r in items if r.get("cohort") == "non_exit"]
    exits = [r for r in items if r.get("cohort") == "exit"]

    def s1_pass(rs: list[dict]) -> int:
        return sum(1 for r in rs if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct"))

    def l3_pass(rs: list[dict]) -> int:
        return sum(1 for r in rs if (r.get("doctrine_alignment") or {}).get("doctrine_aligned"))

    guard_fp = sum(1 for r in guards if _fp_key(r))
    return {
        "n": len(items),
        "S1_pass": s1_pass(items),
        "L3_aligned": l3_pass(items),
        "guard_n": len(guards),
        "guard_false_off_focal": guard_fp,
        "guard_fp_rate": round(guard_fp / max(len(guards), 1), 3),
        "exit_n": len(exits),
        "exit_S1_pass": s1_pass(exits),
        "exit_L3_aligned": l3_pass(exits),
    }


def build_summary(rows: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    ok_rows = [r for r in rows if r.get("status") != "artifact_missing"]
    adjudications = [r.get("adjudication") or {} for r in ok_rows]

    b_idx = _load_baseline_index(ARM_B_MATRIX)
    c_idx = _load_baseline_index(OLD_ARM_C_MATRIX)

    guard_rows = _cohort_rows(ok_rows, "guard_threshold")
    gm3_rows = _cohort_rows(ok_rows, "gm3")
    exit_rows = _cohort_rows(ok_rows, "explicit_exit")

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

    def baseline_subset(idx: dict, subset: list[dict]) -> dict[str, Any]:
        keys = [(r["case_id"], r["sample_index"]) for r in subset]
        matched = [idx[k] for k in keys if k in idx]
        guards = [r for r in matched if r.get("cohort") == "non_exit"]
        gm3 = [r for r in matched if r.get("case_id") == "EXIT-C-GM3"]
        exits = [r for r in matched if r.get("cohort") == "exit"]
        return {
            "n_matched": len(matched),
            "guard_false_off_focal": sum(1 for r in guards if _fp_key(r)),
            "guard_n": len(guards),
            "gm3_S1_pass": sum(
                1 for r in gm3 if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
            ),
            "gm3_n": len(gm3),
            "exit_S1_pass": sum(
                1 for r in exits if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct")
            ),
            "exit_n": len(exits),
        }

    return {
        "experiment_id": plan["experiment_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "topology": TOPOLOGY,
        "doctrine_schema_version": DOCTRINE_SCHEMA,
        "doctrine_variant": DOCTRINE_VARIANT,
        "n_cases": plan["n_cases"],
        "n_samples": len(ok_rows),
        "all_samples_adjudicated": all(r.get("adjudication") for r in ok_rows),
        "all_samples_l3": all(r.get("doctrine_alignment") for r in ok_rows),
        "all_preflight_clean": all(
            (r.get("preflight") or {}).get("contamination_clean") for r in ok_rows
        ),
        "guard_threshold": _group_stats(guard_rows),
        "gm3": _group_stats(gm3_rows),
        "explicit_exit": _group_stats(exit_rows),
        "aggregate": {
            "S1_rate": round(
                sum(1 for r in ok_rows if (r.get("first_attempt") or {}).get("S1_semantic_intent_correct"))
                / max(len(ok_rows), 1),
                3,
            ),
            "L3_alignment_rate": round(
                sum(1 for r in ok_rows if (r.get("doctrine_alignment") or {}).get("doctrine_aligned"))
                / max(len(ok_rows), 1),
                3,
            ),
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
        },
        "baseline_arm_b_focused_subset": baseline_subset(b_idx, ok_rows),
        "baseline_old_arm_c_focused_subset": baseline_subset(c_idx, ok_rows),
        "adjudication_summary": summarize_adjudicated_vs_deterministic(
            ok_rows, adjudications=adjudications
        ),
        "doctrine_alignment_summary": summarize_doctrine_alignment(ok_rows),
        "preflight_by_case": preflight_by_case,
        "doctrine_block_sha256": hashlib.sha256(
            build_issue251_physical_severance_guarded_doctrine_block().encode()
        ).hexdigest(),
    }


def write_guard_delta(rows: list[dict], summary: dict) -> None:
    b_idx = _load_baseline_index(ARM_B_MATRIX)
    c_idx = _load_baseline_index(OLD_ARM_C_MATRIX)
    guard_rows = _cohort_rows([r for r in rows if r.get("status") != "artifact_missing"], "guard_threshold")

    lines = [
        "# Guard/threshold delta — simplified Arm C focused",
        "",
        f"Generated: {summary.get('generated_at')}",
        f"Doctrine variant: `{DOCTRINE_VARIANT}`",
        "",
        "## Aggregate (guard cohort only)",
        "",
        f"| Source | guard FP | guard n |",
        f"|--------|----------|---------|",
    ]
    g = summary["guard_threshold"]
    bb = summary["baseline_arm_b_focused_subset"]
    oc = summary["baseline_old_arm_c_focused_subset"]
    lines.append(f"| **Simplified Arm C (this run)** | {g['guard_false_off_focal']} | {g['guard_n']} |")
    lines.append(f"| Arm B (same cases/samples) | {bb.get('guard_false_off_focal', '—')} | {bb.get('guard_n', '—')} |")
    lines.append(f"| Old Arm C cinematic (same cases/samples) | {oc.get('guard_false_off_focal', '—')} | {oc.get('guard_n', '—')} |")
    lines.append("")
    lines.append("## Per-case")
    lines.append("")

    by_case: dict[str, list[dict]] = defaultdict(list)
    for r in guard_rows:
        by_case[r["case_id"]].append(r)

    for cid in sorted(by_case.keys()):
        case_rows = sorted(by_case[cid], key=lambda x: x["sample_index"])
        fp_s = sum(1 for r in case_rows if _fp_key(r))
        fp_b = sum(1 for r in case_rows if _fp_key(b_idx.get((cid, r["sample_index"]), {})))
        fp_c = sum(1 for r in case_rows if _fp_key(c_idx.get((cid, r["sample_index"]), {})))
        lines.append(f"### {cid}")
        lines.append(f"- Simplified: **{fp_s}/{len(case_rows)}** FP | Arm B: **{fp_b}/{len(case_rows)}** | Old Arm C: **{fp_c}/{len(case_rows)}**")
        for r in case_rows:
            si = r["sample_index"]
            fa = r.get("first_attempt") or {}
            adj = (r.get("adjudication") or {}).get("adjudicated") or {}
            l3 = r.get("doctrine_alignment") or {}
            lines.append(
                f"  - sample {si}: dec={fa.get('decision')} kinds={fa.get('proposal_kinds')} "
                f"S1={fa.get('S1_semantic_intent_correct')} L3={l3.get('doctrine_aligned')} "
                f"L2_fp={adj.get('adjudicated_false_positive')} "
                f"(B_fp={_fp_key(b_idx.get((cid, si), {}))} C_fp={_fp_key(c_idx.get((cid, si), {}))})"
            )
        lines.append("")

    GUARD_DELTA_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_gm3_md(summary: dict, rows: list[dict]) -> None:
    gm3 = [r for r in rows if r.get("case_id") == "EXIT-C-GM3"]
    bb = summary["baseline_arm_b_focused_subset"]
    oc = summary["baseline_old_arm_c_focused_subset"]
    g = summary["gm3"]
    lines = [
        "# GM3 — simplified Arm C focused",
        "",
        f"Generated: {summary.get('generated_at')}",
        "",
        "## Aggregate",
        "",
        f"| Source | S1/L3 pass | n |",
        f"|--------|------------|---|",
        f"| Simplified Arm C | {g['S1_pass']}/{g['n']} | {g['n']} |",
        f"| Arm B (matched) | {bb.get('gm3_S1_pass', '—')}/{bb.get('gm3_n', '—')} | |",
        f"| Old Arm C (matched) | {oc.get('gm3_S1_pass', '—')}/{oc.get('gm3_n', '—')} | |",
        "",
        "## Per-sample",
        "",
    ]
    for r in sorted(gm3, key=lambda x: x["sample_index"]):
        fa = r.get("first_attempt") or {}
        adj = (r.get("adjudication") or {}).get("adjudicated") or {}
        l3 = r.get("doctrine_alignment") or {}
        lines.append(
            f"- sample {r['sample_index']}: dec={fa.get('decision')} S1={fa.get('S1_semantic_intent_correct')} "
            f"S2={fa.get('S2_structural_legality_pass')} L3={l3.get('doctrine_aligned')} "
            f"L2_ok={adj.get('adjudicated_semantically_correct')} amb={adj.get('ambiguous_or_recoverable')}"
        )
    GM3_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_draft_comment(summary: dict) -> None:
    g = summary["guard_threshold"]
    gm = summary["gm3"]
    ex = summary["explicit_exit"]
    text = f"""## §B.5 — simplified Arm C focused validation (draft)

**Status:** Focused rerun complete. **Not** validated. **Not** production.

### Scope

- Doctrine variant: `{DOCTRINE_VARIANT}`
- Topology: `{TOPOLOGY}`
- Samples: {summary['n_samples']} across {summary['n_cases']} cases
- Preflight: **{'all clean' if summary['all_preflight_clean'] else 'FAILURES'}**

### Headline

| Cohort | Simplified Arm C | Arm B (subset) | Old Arm C (subset) |
|--------|----------------|----------------|---------------------|
| Guard FP | {g['guard_false_off_focal']}/{g['guard_n']} | {summary['baseline_arm_b_focused_subset'].get('guard_false_off_focal', '—')}/{summary['baseline_arm_b_focused_subset'].get('guard_n', '—')} | {summary['baseline_old_arm_c_focused_subset'].get('guard_false_off_focal', '—')}/{summary['baseline_old_arm_c_focused_subset'].get('guard_n', '—')} |
| GM3 S1 | {gm['S1_pass']}/{gm['n']} | {summary['baseline_arm_b_focused_subset'].get('gm3_S1_pass', '—')}/{summary['baseline_arm_b_focused_subset'].get('gm3_n', '—')} | {summary['baseline_old_arm_c_focused_subset'].get('gm3_S1_pass', '—')}/{summary['baseline_old_arm_c_focused_subset'].get('gm3_n', '—')} |
| Explicit exit S1 | {ex['exit_S1_pass']}/{ex['exit_n']} | {summary['baseline_arm_b_focused_subset'].get('exit_S1_pass', '—')}/{summary['baseline_arm_b_focused_subset'].get('exit_n', '—')} | {summary['baseline_old_arm_c_focused_subset'].get('exit_S1_pass', '—')}/{summary['baseline_old_arm_c_focused_subset'].get('exit_n', '—')} |

### Artifacts

- `i251_physical_severance_guarded_simplified_focused_matrix.json`
- `i251_physical_severance_guarded_simplified_focused_summary.json`
- `i251_physical_severance_guarded_simplified_focused_guard_delta.md`
- `i251_physical_severance_guarded_simplified_focused_gm3_summary.md`
"""
    DRAFT_COMMENT.write_text(text, encoding="utf-8")


async def run_experiment(*, dry_run: bool = False) -> dict[str, Any]:
    if not dry_run and not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is required for live reruns")

    plan = load_focused_plan()
    print(
        f"Focused: {plan['n_cases']} cases, ~{plan['estimated_samples']} samples, "
        f"variant={DOCTRINE_VARIANT}",
        flush=True,
    )

    path = find_committed_artifact("session_912", 1, 12, "willow_reeves")
    if path:
        audit = json.loads(path.read_text(encoding="utf-8"))
        bot = str(audit.get("bot_name") or "Willow_Reeves")
        proof = apply_issue251_physical_severance_guarded_prompt_overrides(sys_prompt(audit), bot)
        pf = build_physical_severance_guarded_preflight(proof)
        if not pf["contamination_clean"]:
            raise SystemExit(f"GM3 preflight proof failed: {pf['contamination_hits']}")
        hits = active_physical_severance_guarded_contamination_hits(proof)
        if hits:
            raise SystemExit(f"GM3 contamination hits: {hits}")
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
        "plan": {"n_cases": plan["n_cases"], "estimated_samples": plan["estimated_samples"]},
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
        write_guard_delta(all_rows, summary)
        write_gm3_md(summary, all_rows)
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

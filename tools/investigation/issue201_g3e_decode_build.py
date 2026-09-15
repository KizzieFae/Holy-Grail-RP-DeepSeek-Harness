#!/usr/bin/env python3
"""Build G3-E decode adjudication JSON from locked scores and answer key."""
import json
import hashlib
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "data/investigation_runs/issue201-g3e-live-2026-09-15T19-07-03-775Z"
DIMS = [
    "factual_world_consistency",
    "character_knowledge_fidelity",
    "natural_integration_of_retrieved_knowledge",
    "responsiveness",
    "character_fidelity",
    "initiative",
    "coherence",
    "unnecessary_exposition",
    "narrative_usefulness_adjunct",
]
A2 = "a2_indexed_retrieval"
A4 = "lean_a4_knowledge"


def main() -> None:
    lock = json.loads(
        (ROOT / "governance/records/issue-201-g3-e-blind-score-lock-2026-09-15.json").read_text(
            encoding="utf-8"
        )
    )
    scores = {s["blind_label"]: s["scores"] for s in lock["samples"]}
    key = json.loads(
        (EVIDENCE / "outputs/issue201-g3e-blind-answer-key.json").read_text(encoding="utf-8")
    )
    cap = json.loads((EVIDENCE / "capability-matrix-live.json").read_text(encoding="utf-8"))
    cap_by_run = {r["run_id"]: r for r in cap["rows"]}
    pre = json.loads((EVIDENCE / "issue201-g3e-live-pre-decode-report.json").read_text(encoding="utf-8"))

    decode_rows = []
    for row in key:
        label = row["blind_label"]
        sc = scores[label]
        capr = cap_by_run[row["run_id"]]
        decode_rows.append(
            {
                **row,
                "governance_scores": sc,
                "governance_mean_9d": round(sum(sc) / 9, 4),
                "narrative_usefulness": sc[8],
                "objective_outcome": capr["outcome"],
                "tier1_clear": capr["tier1_clear"],
            }
        )

    lib = []
    k3 = []
    for mf in sorted((EVIDENCE / "outputs").glob("*-meta.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        entries = m.get("librarian_ledger_entries") or []
        if entries:
            lib.append(
                {
                    "run_id": m["run_id"],
                    "case_id": m["case_id"],
                    "architecture_arm": m["architecture_arm"],
                    "entry_count": len(entries),
                    "classifications": [e.get("classification") for e in entries],
                    "decision_changed": [e.get("decision_changed") for e in entries],
                    "observable_benefit": [e.get("observable_benefit") for e in entries],
                }
            )
        if m["case_id"] == "K3":
            k3.append(
                {
                    "run_id": m["run_id"],
                    "architecture_arm": m["architecture_arm"],
                    "k3_forensics": m.get("k3_forensics", {}),
                }
            )

    arms = defaultdict(lambda: defaultdict(list))
    for r in decode_rows:
        arm = r["architecture_arm"]
        arms[arm]["means"].append(r["governance_mean_9d"])
        arms[arm]["narr"].append(r["narrative_usefulness"])
        for i, d in enumerate(DIMS):
            arms[arm][d].append(r["governance_scores"][i])

    arm_summary = {}
    for arm in [A2, A4]:
        arm_summary[arm] = {
            "n": len(arms[arm]["means"]),
            "overall_mean_9d": statistics.mean(arms[arm]["means"]),
            "narrative_usefulness_mean": statistics.mean(arms[arm]["narr"]),
            "dimension_means": {d: statistics.mean(arms[arm][d]) for d in DIMS},
            "dimension_ranges": {
                d: {"min": min(arms[arm][d]), "max": max(arms[arm][d])} for d in DIMS
            },
        }

    delta = {d: arm_summary[A2]["dimension_means"][d] - arm_summary[A4]["dimension_means"][d] for d in DIMS}
    delta["overall_9d"] = arm_summary[A2]["overall_mean_9d"] - arm_summary[A4]["overall_mean_9d"]
    delta["narrative_usefulness"] = (
        arm_summary[A2]["narrative_usefulness_mean"] - arm_summary[A4]["narrative_usefulness_mean"]
    )

    decode = {
        "schema": "issue201_g3e_blind_decode_v1",
        "issue": 201,
        "decoded_at": "2026-09-15T20:30:00Z",
        "score_lock_record": "governance/records/issue-201-g3-e-blind-score-lock-2026-09-15.json",
        "execution_record_sha": "3a6a5c6",
        "blind_packet_sha256": hashlib.sha256(
            (EVIDENCE / "outputs/issue201-g3e-blind-packet.json").read_bytes()
        ).hexdigest(),
        "answer_key_sha256": hashlib.sha256(
            (EVIDENCE / "outputs/issue201-g3e-blind-answer-key.json").read_bytes()
        ).hexdigest(),
        "population_mean_all_dimensions": lock["population_mean_all_dimensions"],
        "decode_mapping": decode_rows,
        "arm_summary": arm_summary,
        "a2_minus_a4_delta": delta,
        "arm_accounting": pre["arm_accounting"],
        "tier1_report": pre["tier1_report"],
        "librarian_mediation_by_run": lib,
        "k3_forensics_by_run": k3,
        "status": "decoded_pending_governance_adjudication",
    }

    out = ROOT / "governance/records/issue-201-g3-e-blind-decode-adjudication-2026-09-15.json"
    out.write_text(json.dumps(decode, indent=2), encoding="utf-8")
    print(f"wrote {out}")

    print("\nCASE TABLE")
    for case in ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]:
        rows = sorted(
            [r for r in decode_rows if r["case_id"] == case],
            key=lambda x: (x["architecture_arm"], x["rep_index"]),
        )
        for r in rows:
            arm_short = "A2" if r["architecture_arm"] == A2 else "A4"
            print(
                f"{case} r{r['rep_index']} {arm_short} {r['blind_label']} "
                f"mean={r['governance_mean_9d']} narr={r['narrative_usefulness']} obj={r['objective_outcome']}"
            )


if __name__ == "__main__":
    main()

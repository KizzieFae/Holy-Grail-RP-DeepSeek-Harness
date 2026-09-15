#!/usr/bin/env python3
"""Summarize D-01-L longitudinal report for governance execution record."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT = REPO / "data/investigation_runs/issue201-package-d-d01l-2026-09-14T22-12-05-873Z/issue201-package-d-d01l-longitudinal-report.json"


def sum_inference(seq: dict, field: str) -> int:
    total = 0
    for turn in seq.get("turns", []):
        inf = turn.get("inference", {})
        total += inf.get(field, 0) or 0
    return total


def sum_wall_ms(seq: dict) -> int:
    return sum(t.get("operation_wall_ms", 0) or 0 for t in seq.get("turns", []))


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    sequences = report["sequences"]
    print("SEQUENCE SUMMARY")
    for s in sorted(sequences, key=lambda x: (x["scenario_key"], x["arm_id"], x["repetition_index"])):
        print(
            json.dumps(
                {
                    "sequence_id": s["sequence_id"],
                    "arm": s["arm_id"],
                    "scenario": s["scenario_key"],
                    "rep": s["repetition_index"],
                    "turns": s["turn_count_completed"],
                    "wall_min": round(sum_wall_ms(s) / 60000, 2),
                    "st_preamble": sum_inference(s, "storyteller_preamble_inference_count"),
                    "st_post": sum_inference(s, "storyteller_post_commit_inference_count"),
                    "plot": sum_inference(s, "plot_inference_count"),
                    "total_inf": sum_inference(s, "inference_count"),
                    "objective_issues": sum(len(t.get("objective", {}).get("issues", [])) for t in s["turns"]),
                    "all_committed": s.get("all_committed"),
                }
            )
        )

    print("\nARM TOTALS")
    for arm in ("control", "ablated"):
        arm_seqs = [s for s in sequences if s["arm_id"] == arm]
        print(
            arm,
            {
                "sequences": len(arm_seqs),
                "st_preamble": sum(sum_inference(s, "storyteller_preamble_inference_count") for s in arm_seqs),
                "st_post": sum(sum_inference(s, "storyteller_post_commit_inference_count") for s in arm_seqs),
                "plot": sum(sum_inference(s, "plot_inference_count") for s in arm_seqs),
                "wall_min": round(sum(sum_wall_ms(s) for s in arm_seqs) / 60000, 2),
            },
        )

    print("\nFAILURES", json.dumps(report.get("failures", []), indent=2))
    print("\nREPLACEMENT", json.dumps(report.get("replacement_runs", []), indent=2))


if __name__ == "__main__":
    main()

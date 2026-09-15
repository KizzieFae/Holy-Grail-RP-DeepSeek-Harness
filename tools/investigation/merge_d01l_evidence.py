#!/usr/bin/env python3
"""Merge D-01-L replacement sequence into primary evidence root and rebuild blind packet."""

import json
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PRIMARY = REPO / "data/investigation_runs/issue201-package-d-d01l-2026-09-14T22-12-05-873Z"
RETRY = REPO / "data/investigation_runs/issue201-package-d-d01l-2026-09-15T00-18-44-424Z"
OUT = PRIMARY / "outputs"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    retry_seq_path = RETRY / "outputs/D01L-ablated-arkham_stress-seq1-a1-sequence.json"
    retry_seq = json.loads(retry_seq_path.read_text(encoding="utf-8"))
    retry_seq["sequence_id"] = "D01L-ablated-arkham_stress-seq1-a1"
    retry_seq["replacement_for"] = "D01L-ablated-arkham_stress-seq1"
    retry_seq["replacement_trigger"] = "contaminated_incomplete_sequence_after_two_attempts"
    retry_seq["expansion_authorized"] = True
    (OUT / "D01L-ablated-arkham_stress-seq1-a1-sequence.json").write_text(
        json.dumps(retry_seq, indent=2) + "\n", encoding="utf-8"
    )
    for turn in retry_seq["turns"]:
        src = RETRY / "outputs" / (
            f"D01L-ablated-arkham_stress-seq1-a1-t{turn['turn_index']}-presentation.txt"
        )
        dst = OUT / (
            f"D01L-ablated-arkham_stress-seq1-a1-t{turn['turn_index']}-presentation.txt"
        )
        if src.exists():
            shutil.copy2(src, dst)

    by_key: dict[tuple[str, str, int], dict] = {}
    for fp in sorted(OUT.glob("D01L-*-sequence.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        if not data.get("all_committed"):
            continue
        key = (data["arm_id"], data["scenario_key"], data["repetition_index"])
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = data
            continue
        # Prefer replacement sequence over failed original.
        if data.get("replacement_for") or "-a" in data["sequence_id"]:
            by_key[key] = data

    sequences = sorted(
        by_key.values(),
        key=lambda x: (x["scenario_key"], x["arm_id"], x["repetition_index"]),
    )
    print(f"merged sequences: {len(sequences)}")
    for s in sequences:
        print(
            f"  {s['arm_id']} {s['scenario_key']} rep{s['repetition_index']} -> {s['sequence_id']}"
        )

    briefing_keys = {
        "arkham_asylum_mess_hall_arena": "arkham_mess_hall_stress",
        "ayame_household_entry_evaluation": "ayame_household_entry",
    }
    shuffled = sequences[:]
    random.seed(201)
    random.shuffle(shuffled)
    for i, s in enumerate(shuffled):
        s["blind_label"] = f"SEQ-{chr(65 + i)}"

    packet = {
        "schema": "issue201_blind_sequence_packet_v1",
        "purpose": "D-01-L longitudinal Storyteller preamble test — complete sequence bundles",
        "causal_question": (
            "Does synchronous preamble Storyteller cognition add material multi-turn "
            "narrative value when Plot and post-commit Storyteller remain available?"
        ),
        "instructions": (
            "Score each complete sequence using the 10 sequence-level dimensions (primary). "
            "Per-turn 11-dimension rubric is secondary. Do not request arm, session, "
            "inference, or latency data until after scoring is locked."
        ),
        "sequence_level_dimensions": [
            "thread persistence",
            "escalation coherence",
            "agenda persistence",
            "delayed consequences",
            "scene momentum",
            "cross-turn initiative",
            "reactive-loop avoidance",
            "premature-resolution avoidance",
            "plot-drift control",
            "cross-turn emotional/narrative continuity",
        ],
        "sequences": [
            {
                "blind_label": s["blind_label"],
                "scenario_briefing_key": briefing_keys[s["scenario_id"]],
                "turns": [
                    {
                        "turn_index": t["turn_index"],
                        "player_stimulus": t["exact_player_stimulus"],
                        "presentation_text": t["presentation_text"],
                    }
                    for t in s["turns"]
                ],
            }
            for s in shuffled
        ],
    }
    answer_key = [
        {
            "blind_label": s["blind_label"],
            "sequence_id": s["sequence_id"],
            "arm_id": s["arm_id"],
            "scenario_key": s["scenario_key"],
            "scenario_id": s["scenario_id"],
            "repetition_index": s["repetition_index"],
            "policy_id": s["policy_id"],
            "policy_hash": s["policy_hash"],
            "branch_trajectory": s["branch_trajectory"],
        }
        for s in shuffled
    ]
    (OUT / "issue201-d01l-blind-sequence-packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "issue201-d01l-blind-sequence-answer-key.json").write_text(
        json.dumps(answer_key, indent=2) + "\n", encoding="utf-8"
    )

    report_path = PRIMARY / "issue201-package-d-d01l-longitudinal-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["sequences"] = sequences
    report["replacement_runs"] = [
        {
            "trigger": "contaminated_incomplete_sequence",
            "condition": "contaminated/incomplete sequence (authorized expansion trigger #2)",
            "original_sequence_id": "D01L-ablated-arkham_stress-seq1",
            "replacement_sequence_id": "D01L-ablated-arkham_stress-seq1-a1",
            "replacement_evidence_root": str(RETRY),
            "attempts_before_replacement": 2,
            "expansion_bound": "+1 sequence/scenario/arm maximum",
        }
    ]
    report["human_blind_eval"] = {
        "packetPath": str(OUT / "issue201-d01l-blind-sequence-packet.json"),
        "keyPath": str(OUT / "issue201-d01l-blind-sequence-answer-key.json"),
        "sequence_count": len(sequences),
        "excluded": 0,
        "status": "prepared_for_governance_blind_scoring",
    }
    report["merged_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"blind packet sequences: {len(sequences)}")


if __name__ == "__main__":
    main()

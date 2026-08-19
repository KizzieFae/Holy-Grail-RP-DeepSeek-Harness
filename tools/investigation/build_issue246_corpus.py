#!/usr/bin/env python3
"""Build Issue #246 frozen adjudication corpus from cohesion/willow JSONL extracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PY = REPO_ROOT
sys.path.insert(0, str(LEGACY_RP_APP))

from participation_suspicion_extract import make_suspicion_id  # noqa: E402
from _repo_paths import DATA_DIR, FIXTURES_DIR, INVESTIGATION_DIR, LEGACY_RP_APP, REPO_ROOT, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir  # noqa: E402

VR = VALIDATION_RUNS_ARCHIVE

# Manual review anchors from issue227_selective_cohesion_evidence_synthesis.md
ANCHORS: dict[tuple[int, str, str], tuple[str, str]] = {
    (899, "P03", "Willow_Reeves"): ("case_11", "adjudicated_failure"),
    (899, "P04", "Willow_Reeves"): ("case_12", "adjudicated_failure"),
    (902, "P03", "Hannah_Lovelace"): ("case_15", "adjudicated_failure"),
    (901, "P04", "Willow_Reeves"): ("case_13", "ambiguous_or_unresolved"),
    (902, "P01", "Hannah_Lovelace"): ("case_14", "ambiguous_or_unresolved"),
    (907, "P03", "Celina"): ("case_24", "ambiguous_or_unresolved"),
}

JSONL_SOURCES = [
    VR / "willow_departure_baseline_v1.jsonl",
    VR / "willow_departure_willow_flex_v1.jsonl",
    VR / "willow_departure_alphas_flex_v1.jsonl",
    VR / "cohesion_slate/household_baseline.jsonl",
    VR / "cohesion_slate/household_flex.jsonl",
    VR / "cohesion_slate/arkham_baseline.jsonl",
    VR / "cohesion_slate/arkham_flex.jsonl",
    VR / "cohesion_slate/apartment_baseline.jsonl",
    VR / "cohesion_slate/apartment_flex.jsonl",
]


def _load_c3_rows() -> list[dict]:
    rows: list[dict] = []
    for path in JSONL_SOURCES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("parse_partial"):
                continue
            if row.get("rubric_class") != "C3_missed_covered_change":
                continue
            actor = str(row.get("actor") or "")
            if "parse" in actor.lower():
                continue
            rows.append(row)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Build #246 frozen adjudication corpus")
    ap.add_argument(
        "--out",
        type=Path,
        default=FIXTURES_DIR / "issue227" / "adjudication_corpus_cohesion_v1.json",
    )
    args = ap.parse_args()

    rows = _load_c3_rows()
    cases: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        session = row.get("audit_session_number")
        probe = str(row.get("probe_id") or "")
        actor = str(row.get("actor") or "")
        sid = make_suspicion_id(
            audit_session_number=session,
            turn_number=row.get("turn_number"),
            actor=actor,
            probe_id=probe,
        )
        if sid in seen:
            continue
        seen.add(sid)
        key = (int(session), probe, actor)
        if key in ANCHORS:
            case_id, outcome = ANCHORS[key]
            case_class = "true_miss" if outcome == "adjudicated_failure" else "weakened"
        else:
            case_id = f"auto_{len(cases)+1:02d}"
            outcome = "adjudicated_non_failure"
            case_class = "false_positive_topology"
        cases.append(
            {
                "case_id": case_id,
                "suspicion_id": sid,
                "calibration_outcome": outcome,
                "case_class": case_class,
                "audit_session_number": session,
                "probe_id": probe,
                "actor": actor,
                "rubric_class": row.get("rubric_class"),
            }
        )

    corpus = {
        "schema_version": "issue246_adjudication_corpus_v1",
        "description": "Frozen #227 cohesion C3 suspicion calibration anchors (#246)",
        "jsonl_sources": [str(p.relative_to(_PY)).replace("\\", "/") for p in JSONL_SOURCES],
        "limitations": [
            "human_calibration_anchor: not canonical semantic truth",
            "calibration_outcome drives mock regression only",
        ],
        "cases": sorted(cases, key=lambda c: c["case_id"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases -> {args.out}")


if __name__ == "__main__":
    main()

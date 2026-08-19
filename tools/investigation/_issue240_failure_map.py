"""Issue #240 applied-overlay failure bucket mapper (investigation helper)."""
from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _issue240_audit_classifier import (  # noqa: E402
    OFF_FOCAL_CUES,
    REENTRY_CUES,
    _beats_text,
    _overlay_applied,
    _proposals,
    _semantic_decision_label,
    classify_turn,
)

GRADUAL_CUES = re.compile(
    r"\b(withdraw|margin|distance|quiet|minimal|edge|turn(?:s|ed)?\s+away|"
    r"pull(?:s|ed)?\s+back|disengag|guard|shut\s+down|look(?:s|ed)?\s+away|"
    r"couch|bunk|window|step(?:s|ped)?\s+(?:back|away|off)|re-?enter|return)\b",
    re.I,
)


def bucket_applied_turn(data: dict) -> str:
    if not _overlay_applied(data):
        return "not_applied"
    po = data.get("parsed_output") or {}
    decision = _semantic_decision_label(data)
    beats = _beats_text(data)
    props = _proposals(data)
    primary, secondary = classify_turn(data)
    has_movement = bool(
        OFF_FOCAL_CUES.search(beats)
        or REENTRY_CUES.search(beats)
        or GRADUAL_CUES.search(beats)
    )

    if decision == "omission":
        return "no_semantic_engagement"
    if decision == "empty_array":
        return "fake_engagement"
    if decision == "no_covered_change":
        if has_movement:
            return "prose_movement_decision_no_change"
        return "semantic_engagement_no_change"
    if decision == "covered_change":
        if not props:
            return "covered_change_without_proposals"
        if primary == "F0":
            return "honest_covered_change"
        if primary in {"F3", "F4"}:
            return "proposal_mismatched"
        return "covered_change_other"
    if props and primary in {"F3", "F4"}:
        return "proposal_mismatched"
    if props:
        return "legacy_proposal_emit"
    if has_movement:
        return "prose_movement_decision_no_change"
    return "no_visible_movement"


def analyze_sessions(session_ids: list[str]) -> dict:
    base = resolve_rp_audits_dir()
    rows: list[dict] = []
    for sid in session_ids:
        sdir = base / (sid if sid.startswith("session_") else f"session_{sid}")
        if not sdir.is_dir():
            continue
        for fp in sorted(sdir.rglob("*_full.json")):
            data = json.loads(fp.read_text(encoding="utf-8"))
            if data.get("bot_type") != "character":
                continue
            if not _overlay_applied(data):
                continue
            primary, secondary = classify_turn(data)
            rows.append(
                {
                    "session": sdir.name,
                    "turn": data.get("turn_number"),
                    "bot": data.get("bot_name"),
                    "decision": _semantic_decision_label(data),
                    "primary": primary,
                    "secondary": secondary,
                    "proposal_count": len(_proposals(data)),
                    "bucket": bucket_applied_turn(data),
                    "beats_snip": _beats_text(data)[:180],
                }
            )
    return {
        "applied_turns": rows,
        "bucket_counts": dict(Counter(r["bucket"] for r in rows)),
        "decision_counts": dict(Counter(r["decision"] for r in rows)),
        "primary_counts": dict(Counter(r["primary"] for r in rows)),
    }


if __name__ == "__main__":
    ids = sys.argv[1:]
    out = analyze_sessions(ids)
    print(json.dumps(out, indent=2))

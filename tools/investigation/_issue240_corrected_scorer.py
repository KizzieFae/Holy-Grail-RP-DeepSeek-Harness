"""Issue #240 corrected ontology scorer — investigation helper, not product code."""
from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _issue240_audit_classifier import (  # noqa: E402
    _beats_text,
    _overlay_applied,
    _proposals,
    _semantic_decision_label,
    classify_turn,
)

# In-room / same-space — NOT excursion semantics
IN_ROOM = re.compile(
    r"\b("
    r"couch|bunk|bed|desk|kitchenette|mattress|blanket|pillow|drawer|"
    r"window(?:sill)?|tool\s+bag|sketchbook|mini-fridge|closet|"
    r"crossed\s+to\s+(?:my|her|the)\s+(?:bunk|desk|couch|bed)|"
    r"swung\s+onto\s+(?:my|her|the)\s+bunk|"
    r"sat\s+(?:on|down\s+on)\s+(?:the\s+)?(?:couch|bunk|bed|edge)"
    r")\b",
    re.I,
)

# Informational bathroom/hallway mention (directions, not executed exit)
INFO_BOUNDARY = re.compile(
    r"\b(bathroom(?:'s|\s+is|\s+door)|down\s+the\s+hall|third\s+door)\b",
    re.I,
)

# Executed scene-boundary transition (net durable state may change)
EXEC_DEPART = re.compile(
    r"\b("
    r"(?:walk(?:ed|s|ing)?|step(?:ped|s|ping)?|head(?:ed|s|ing)?|slip(?:ped|s|ping)?|"
    r"move(?:d|s|ing)?|cross(?:ed|es|ing)?|exit(?:ed|s|ing)?|leave(?:s|d|ing)?|"
    r"push(?:ed|es|ing)?)\s+(?:out|past|through|into|toward|down)\s+"
    r"(?:the\s+)?(?:open\s+)?(?:door(?:way)?|hall(?:way)?|corridor|building|outside|bathroom|room)"
    r"|(?:into|to|toward|through)\s+(?:the\s+)?(?:hall(?:way)?|corridor|bathroom|shower|outside)"
    r"|(?:out\s+(?:into|of|the)\s+(?:the\s+)?(?:hall(?:way)?|corridor|door|room|building))"
    r"|walked\s+past\s+her\s+through"
    r")\b",
    re.I,
)

EXEC_RETURN = re.compile(
    r"\b("
    r"(?:return(?:ed|s|ing)?|re-?enter(?:ed|s|ing)?|come(?:s|back)?\s+back|"
    r"step(?:ped|s|ping)?\s+back\s+in)\s+(?:to|into)\s+"
    r"(?:the\s+)?(?:room|dorm|exchange|conversation|focal|doorway)"
    r"|(?:back\s+into\s+the\s+(?:room|dorm|living\s+room))"
    r")\b",
    re.I,
)

ROUND_TRIP = re.compile(
    r"(?:slip(?:ped|s)?\s+out|left\s+(?:the\s+)?room|into\s+the\s+hall).*(?:return(?:ed|s)?|back\s+into|stepped\s+inside)",
    re.I | re.S,
)


def boundary_signals(beats: str) -> dict[str, bool]:
    depart = bool(EXEC_DEPART.search(beats))
    ret = bool(EXEC_RETURN.search(beats))
    in_room_only = bool(IN_ROOM.search(beats)) and not depart
    info_only = bool(INFO_BOUNDARY.search(beats)) and not depart
    round_trip = bool(ROUND_TRIP.search(beats))
    return {
        "exec_depart": depart,
        "exec_return": ret,
        "in_room_only": in_room_only,
        "info_boundary_only": info_only,
        "round_trip_same_turn": round_trip and depart and ret,
    }


def legal_alternatives(
    *,
    signals: dict[str, bool],
    actor: str,
    must_remain: bool = False,
) -> list[str]:
    alts: list[str] = []
    if signals["round_trip_same_turn"]:
        alts.append("no_covered_change (only legal net-state for same-turn round-trip)")
        return alts
    if signals["exec_depart"] and not signals["exec_return"]:
        alts.extend(["covered_change + excursion_lifecycle/open", "covered_change + off_focal"])
    elif signals["exec_return"] and not signals["exec_depart"]:
        alts.append("covered_change + reentry")
    elif signals["exec_depart"] and signals["exec_return"]:
        alts.append("no_covered_change (open+close same turn illegal)")
    if must_remain:
        alts = [a for a in alts if "off_focal" not in a]
        if not alts and signals["exec_depart"]:
            alts.append("no_covered_change (must_remain blocks off_focal commit)")
    if signals["in_room_only"] or signals["info_boundary_only"]:
        alts = ["no_covered_change (in-room / informational only)"]
    if not alts:
        alts.append("no_covered_change (no net boundary transition)")
    return alts


def corrected_classify(data: dict[str, Any], *, must_remain: bool = False) -> dict[str, Any]:
    beats = _beats_text(data)
    signals = boundary_signals(beats)
    decision = _semantic_decision_label(data)
    props = _proposals(data)
    primary, secondary = classify_turn(data)
    overlay = _overlay_applied(data)
    alts = legal_alternatives(signals=signals, actor=str(data.get("bot_name") or ""), must_remain=must_remain)

    category = "success"
    rationale = ""

    prop_kinds = [f"{p.get('kind')}/{p.get('operation', '')}".strip("/") for p in props]

    if primary == "F0" and decision == "covered_change" and props:
        category = "success"
        rationale = "Honest covered_change with aligned proposals."
    elif signals["round_trip_same_turn"] and decision == "no_covered_change":
        category = "contract-limited / legal compression"
        rationale = "Same-turn round-trip; net state unchanged; open+close illegal."
    elif (signals["in_room_only"] or signals["info_boundary_only"]) and decision == "no_covered_change":
        category = "evaluator/classifier defect"
        rationale = "In-room repositioning or informational boundary mention; not a semantic miss."
    elif signals["exec_depart"] and not signals["exec_return"] and decision == "no_covered_change":
        if overlay:
            category = "true semantic miss"
            rationale = "Executed departure with durable net-state change available; overlay applied."
        else:
            category = "ambiguous ontology threshold"
            rationale = "Executed departure without overlay; threshold judgment may vary."
    elif decision == "covered_change" and not props:
        category = "true semantic miss"
        rationale = "covered_change without proposals."
    elif decision == "covered_change" and primary in {"F3", "F4"}:
        category = "evaluator/classifier defect"
        rationale = "Performative or contradiction flagged; needs beat review."
    elif decision == "no_covered_change" and overlay and not any(
        signals[k] for k in ("exec_depart", "exec_return", "round_trip_same_turn")
    ):
        category = "success"
        rationale = "Honest no_covered_change; no executed boundary transition."
    elif decision == "no_covered_change" and overlay:
        category = "ambiguous ontology threshold"
        rationale = "Overlay applied but participation shift unclear or partial."
    elif not overlay and decision == "no_covered_change":
        category = "success"
        rationale = "Ambient beat; no overlay pressure."

    return {
        "session": None,
        "turn": data.get("turn_number"),
        "bot": data.get("bot_name"),
        "overlay_applied": overlay,
        "semantic_decision": decision,
        "proposals": prop_kinds,
        "classifier_primary": primary,
        "classifier_secondary": secondary,
        "boundary_signals": signals,
        "legal_alternatives": alts,
        "corrected_category": category,
        "corrected_rationale": rationale,
        "beats_snip": beats[:320],
    }


def analyze_session(session_dir: Path, *, must_remain: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for fp in sorted(session_dir.rglob("*_full.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("bot_type") != "character":
            continue
        if fp.name.endswith("_validation_full.json"):
            continue
        row = corrected_classify(data, must_remain=must_remain)
        row["session"] = session_dir.name
        row["file"] = fp.name
        rows.append(row)
    cats = Counter(r["corrected_category"] for r in rows)
    overlay_rows = [r for r in rows if r["overlay_applied"]]
    misses = [r for r in rows if r["corrected_category"] == "true semantic miss"]
    return {
        "session": session_dir.name,
        "character_turns": len(rows),
        "corrected_category_counts": dict(cats),
        "overlay_applied_turns": len(overlay_rows),
        "true_misses": misses,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--must-remain", action="store_true", help="Willow lane legality")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()
    base = resolve_rp_audits_dir()
    results = [
        analyze_session(
            base / (s if s.startswith("session_") else f"session_{s}"),
            must_remain=args.must_remain,
        )
        for s in args.sessions
        if (base / (s if s.startswith("session_") else f"session_{s}")).is_dir()
    ]
    out = {"sessions": results}
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    for r in results:
        print(
            f"{r['session']}: turns={r['character_turns']} "
            f"overlay={r['overlay_applied_turns']} misses={len(r['true_misses'])} "
            f"cats={r['corrected_category_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

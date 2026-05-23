"""Build Issue #240 frozen Willow adjudication corpus (evaluation-only, non-authoritative)."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

sys_path = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(sys_path))
from _issue240_audit_classifier import (  # noqa: E402
    OFF_FOCAL_CUES,
    REENTRY_CUES,
    _beats_text,
    _overlay_applied,
    _semantic_decision_label,
    classify_turn,
)
from _issue240_failure_map import GRADUAL_CUES, bucket_applied_turn  # noqa: E402

AUDITS = Path(__file__).resolve().parent.parent / "rp_app" / "data" / "rp_audits"
WILLOW_SCENARIO = "audit_i225_willow_must_remain_v2_offstage_cycles"
DEFAULT_SESSIONS = [
    "825",
    "828",
    "831",
    "833",
    "834",
    "837",
    "840",
    "841",
    "843",
    "845",
    "846",
    "847",
]

STRONG_OFF_FOCAL = re.compile(
    r"\b(kitchenette|kitchen|off.?focal|offstage|leave(?:s|ing)?\s+the\s+(?:room|exchange)|"
    r"step(?:s|ped)?\s+out|exit(?:s|ed|ing)?\s+(?:to|toward))\b",
    re.I,
)
STRONG_REENTRY = re.compile(
    r"\b(re-?enter(?:s|ed|ing)?\s+the\s+(?:exchange|conversation)|"
    r"return(?:s|ed|ing)?\s+to\s+the\s+(?:exchange|conversation|focal))\b",
    re.I,
)
AFFECT_ONLY = re.compile(
    r"\b(sigh|breath|exhale|voice|tone|expression|feel|emotion|quiet|silence)\b",
    re.I,
)


def _recent_participation_snip(prompt: str, limit: int = 600) -> str:
    for header in (
        "RECENT PARTICIPATION ARC",
        "COVERED-CHANGE THRESHOLD",
        "ACTIVE SCENE FOCUS",
    ):
        idx = prompt.find(header)
        if idx >= 0:
            chunk = prompt[idx : idx + limit]
            return chunk.strip()
    return ""


def _trigger_snip(data: dict[str, Any]) -> str:
    return str(data.get("effective_user_trigger") or "").strip()


def _beats_list(data: dict[str, Any]) -> list[dict[str, Any]]:
    po = data.get("parsed_output") or {}
    beats = po.get("beats") or []
    return [b for b in beats if isinstance(b, dict)]


def _semantic_eval(data: dict[str, Any]) -> dict[str, Any]:
    po = data.get("parsed_output") or {}
    ev = po.get("semantic_evaluation")
    return ev if isinstance(ev, dict) else {}


def _transcript_tail(data: dict[str, Any], n: int = 2) -> list[str]:
    sys_c = ""
    for msg in data.get("input_messages") or []:
        if msg.get("role") == "system":
            sys_c = str(msg.get("content") or "")
            break
    idx = sys_c.find("RECENT SCENE TRANSCRIPT")
    if idx < 0:
        return []
    tail = sys_c[idx : idx + 2500]
    return [tail[:800]]


def pre_triage(case: dict[str, Any]) -> tuple[str, str, bool]:
    """Return (label, rationale, needs_human_review)."""
    beats = case["beats_text"]
    decision = case["semantic_decision"]
    bucket = case["failure_bucket"]
    primary = case["classifier_primary"]

    if primary == "F0" and decision == "covered_change":
        return (
            "clear_covered_change",
            "Model emitted honest covered_change with F0 alignment.",
            False,
        )

    if STRONG_OFF_FOCAL.search(beats) or STRONG_REENTRY.search(beats):
        if decision == "no_covered_change":
            return (
                "ambiguous",
                "Beats contain strong off_focal/reentry cues but model judged no_covered_change.",
                True,
            )
        return (
            "clear_covered_change",
            "Strong off_focal/reentry cues with covered_change decision.",
            False,
        )

    if bucket == "semantic_engagement_no_change" and not case["movement_cues"]:
        return (
            "clear_no_covered_change",
            "No participation movement cues; honest no_covered_change plausible.",
            False,
        )

    if bucket == "prose_movement_decision_no_change":
        return (
            "ambiguous",
            "Gradual movement/housekeeping prose with no_covered_change — threshold disagreement likely.",
            True,
        )

    if decision == "no_covered_change" and not case["movement_cues"]:
        return (
            "clear_no_covered_change",
            "Static beat; no material participation shift evident in prose.",
            False,
        )

    if decision == "covered_change" and primary in {"F3", "F4"}:
        return (
            "ambiguous",
            "covered_change decision but classifier flagged performative/contradiction.",
            True,
        )

    return (
        "ambiguous",
        "Participation shift unclear from automated cues alone.",
        True,
    )


def extract_case(fp: Path) -> dict[str, Any] | None:
    data = json.loads(fp.read_text(encoding="utf-8"))
    if data.get("bot_type") != "character":
        return None
    if str(data.get("session_owner") or "") != WILLOW_SCENARIO:
        return None
    if str(data.get("bot_name") or "") not in {"Willow_Reeves", "Willow Reeves"}:
        return None
    if not _overlay_applied(data):
        return None

    beats_text = _beats_text(data)
    primary, secondary = classify_turn(data)
    sys_c = ""
    for msg in data.get("input_messages") or []:
        if msg.get("role") == "system":
            sys_c = str(msg.get("content") or "")
            break

    case_id = f"{data.get('session_number')}_t{data.get('turn_number')}_willow"
    return {
        "case_id": case_id,
        "session_id": f"session_{data.get('session_number')}",
        "turn_index": data.get("turn_number"),
        "scenario_id": WILLOW_SCENARIO,
        "actor": data.get("bot_name"),
        "topology_era": "semantic_eval_v1_next5_plus",
        "trigger_context": _trigger_snip(data),
        "participation_context_snip": _recent_participation_snip(sys_c),
        "transcript_context_snip": _transcript_tail(data),
        "beats": _beats_list(data),
        "beats_text": beats_text,
        "motivation": (data.get("parsed_output") or {}).get("motivation"),
        "semantic_evaluation": _semantic_eval(data),
        "semantic_decision": _semantic_decision_label(data),
        "classifier_primary": primary,
        "classifier_secondary": secondary,
        "failure_bucket": bucket_applied_turn(data),
        "movement_cues": bool(
            OFF_FOCAL_CUES.search(beats_text)
            or REENTRY_CUES.search(beats_text)
            or GRADUAL_CUES.search(beats_text)
        ),
        "audit_path": str(fp.relative_to(AUDITS.parent.parent.parent)).replace("\\", "/"),
    }


def build_corpus(session_ids: list[str]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for sid in session_ids:
        sdir = AUDITS / (sid if sid.startswith("session_") else f"session_{sid}")
        if not sdir.is_dir():
            continue
        for fp in sorted(sdir.rglob("*willow*_full.json")):
            case = extract_case(fp)
            if case:
                label, rationale, needs_human = pre_triage(case)
                case["pre_triage_label"] = label
                case["pre_triage_rationale"] = rationale
                case["needs_human_review"] = needs_human
                cases.append(case)

    cases.sort(key=lambda c: (c["session_id"], c["turn_index"]))
    label_counts = Counter(c["pre_triage_label"] for c in cases)
    human_count = sum(1 for c in cases if c["needs_human_review"])

    return {
        "schema_version": "issue240_adjudication_corpus_v1",
        "purpose": "evaluation_only — not runtime authority, not continuity authority",
        "doctrine": "#224 no prose authority; corpus labels are calibration benchmarks only",
        "source_sessions": session_ids,
        "case_count": len(cases),
        "pre_triage_counts": dict(label_counts),
        "needs_human_review_count": human_count,
        "cases": cases,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "sessions",
        nargs="*",
        default=DEFAULT_SESSIONS,
        help="Session ids (default: semantic_eval Willow applied-overlay era)",
    )
    ap.add_argument(
        "-o",
        "--out",
        default=str(
            Path(__file__).resolve().parent.parent
            / "data"
            / "issue240"
            / "adjudication_corpus_willow_v1.json"
        ),
    )
    args = ap.parse_args()
    corpus = build_corpus(args.sessions)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: corpus[k] for k in corpus if k != "cases"}, indent=2))


if __name__ == "__main__":
    main()

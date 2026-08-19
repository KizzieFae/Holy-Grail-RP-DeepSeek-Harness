"""Issue #240 V1 matrix classifier — investigation helper, not product code."""
from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

OFF_FOCAL_CUES = re.compile(
    r"\b(kitchen|kitchenette|off.?focal|offstage|step(?:s|ped)?\s+(?:out|away|off)|"
    r"withdraw|leave\s+the\s+(?:room|exchange|focal)|excursion|reentry|re-enter)\b",
    re.I,
)
REENTRY_CUES = re.compile(r"\b(re-?enter|return(?:s|ed|ing)?\s+to|come\s+back)\b", re.I)
_ONLY_ACTOR = re.compile(r"\b([A-Za-z][A-Za-z _]*?)\s+ONLY\b", re.I)
_ACTOR_TARGETED_MODE = "actor_targeted_overlay"


def _overlay_meta(data: dict[str, Any]) -> dict[str, Any]:
    md = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    return {
        "overlay_schedule_mode": data.get("overlay_schedule_mode") or md.get("overlay_schedule_mode"),
        "overlay_target_actor": data.get("overlay_target_actor") or md.get("overlay_target_actor"),
        "overlay_applied": data.get("overlay_applied", md.get("overlay_applied")),
        "overlay_skipped_reason": data.get("overlay_skipped_reason")
        or md.get("overlay_skipped_reason"),
    }


def _overlay_demands_semantic_engagement(data: dict[str, Any]) -> bool:
    """True when overlay trigger demands semantic engagement (legacy or v1_next7 wire)."""
    trig = str(data.get("effective_user_trigger") or "")
    t = trig.lower()
    has_wire = "semantic_proposals" in t or "semantic_evaluation" in t
    return has_wire and (
        "required:" in t
        or "required " in t
        or "must include" in t
        or "must emit" in t
        or "same required" in t
    )


def _overlay_demands_proposals(data: dict[str, Any]) -> bool:
    """Backward-compatible alias for overlay semantic-engagement detection."""
    return _overlay_demands_semantic_engagement(data)


def _expected_overlay_actor(data: dict[str, Any]) -> str | None:
    meta = _overlay_meta(data)
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        target = str(meta.get("overlay_target_actor") or "").strip()
        return target or None
    trig = str(data.get("effective_user_trigger") or "")
    m = _ONLY_ACTOR.search(trig)
    if not m:
        return None
    return str(m.group(1) or "").strip()


def _overlay_opportunity(data: dict[str, Any]) -> bool:
    meta = _overlay_meta(data)
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        return bool(meta.get("overlay_target_actor"))
    return _overlay_demands_proposals(data)


def _overlay_applied(data: dict[str, Any]) -> bool:
    meta = _overlay_meta(data)
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        return meta.get("overlay_applied") is True
    return _overlay_demands_proposals(data) and _actor_aligned(data) is True


def _actor_aligned(data: dict[str, Any]) -> bool | None:
    meta = _overlay_meta(data)
    if meta.get("overlay_schedule_mode") == _ACTOR_TARGETED_MODE:
        if not meta.get("overlay_target_actor"):
            return None
        if meta.get("overlay_applied") is not True:
            return False
        expected = str(meta.get("overlay_target_actor") or "")
        bot = str(data.get("bot_name") or "").strip()
        if not bot:
            return False
        exp_norm = expected.replace("_", " ").casefold()
        bot_norm = bot.replace("_", " ").casefold()
        return exp_norm in bot_norm or bot_norm in exp_norm
    if not _overlay_demands_proposals(data):
        return None
    expected = _expected_overlay_actor(data)
    if not expected:
        return None
    bot = str(data.get("bot_name") or "").strip()
    if not bot:
        return False
    exp_norm = expected.replace("_", " ").casefold()
    bot_norm = bot.replace("_", " ").casefold()
    return exp_norm in bot_norm or bot_norm in exp_norm


def _beats_text(data: dict[str, Any]) -> str:
    po = data.get("parsed_output") or {}
    parts: list[str] = []
    for b in po.get("beats") or []:
        if isinstance(b, dict):
            parts.append(str(b.get("action") or ""))
            parts.append(str(b.get("dialogue") or ""))
    return " ".join(parts)


def _semantic_evaluation(po: dict[str, Any]) -> dict[str, Any] | None:
    ev = po.get("semantic_evaluation")
    return ev if isinstance(ev, dict) else None


def _semantic_decision_label(data: dict[str, Any]) -> str:
    po = data.get("parsed_output") or {}
    if not isinstance(po, dict):
        return "invalid"
    ev = _semantic_evaluation(po)
    if isinstance(ev, dict):
        decision = str(ev.get("decision") or "").strip()
        if decision in {"covered_change", "no_covered_change"}:
            return decision
    raw = str(data.get("raw_response") or "")
    if '"semantic_proposals": []' in raw or (
        isinstance(po.get("semantic_proposals"), list) and po.get("semantic_proposals") == []
    ):
        return "empty_array"
    if _proposals(data):
        return "legacy_proposal_emit"
    return "omission"


def _proposals(data: dict[str, Any]) -> list[dict[str, Any]]:
    po = data.get("parsed_output") or {}
    sp = po.get("semantic_proposals")
    if isinstance(sp, list) and sp:
        return [p for p in sp if isinstance(p, dict)]
    ev = _semantic_evaluation(po)
    if isinstance(ev, dict) and ev.get("decision") == "covered_change":
        props = ev.get("proposals")
        if isinstance(props, list):
            return [p for p in props if isinstance(p, dict)]
    return []


def _trigger_expects_off_focal(data: dict[str, Any]) -> bool:
    trig = str(data.get("effective_user_trigger") or "").lower()
    return "off_focal" in trig or "kitchen" in trig or "kitchenette" in trig


def _trigger_expects_reentry(data: dict[str, Any]) -> bool:
    trig = str(data.get("effective_user_trigger") or "").lower()
    return "reentry" in trig or "re-enter" in trig


def _honest_f0(data: dict[str, Any]) -> bool:
    props = _proposals(data)
    if not props:
        return False
    beats = _beats_text(data)
    trig = str(data.get("effective_user_trigger") or "").lower()
    bot = str(data.get("bot_name") or "")
    for p in props:
        kind = str(p.get("kind") or "")
        char = str(p.get("character") or "")
        if kind == "off_focal":
            if bot and char and char.lower() != bot.lower():
                return False
            if _trigger_expects_off_focal(data):
                if not (OFF_FOCAL_CUES.search(beats) or OFF_FOCAL_CUES.search(trig)):
                    return False
        if kind == "reentry":
            if bot and char and char.lower() != bot.lower():
                return False
            if _trigger_expects_reentry(data):
                if not (REENTRY_CUES.search(beats) or REENTRY_CUES.search(trig)):
                    return False
    return True


def classify_turn(data: dict[str, Any]) -> tuple[str, list[str]]:
    tags: list[str] = []
    po = data.get("parsed_output")
    if not isinstance(po, dict):
        return "F1", ["schema_syntax"]

    overlay = _overlay_applied(data)
    props = _proposals(data)
    raw = str(data.get("raw_response") or "")
    raw_has_key = "semantic_proposals" in raw
    ev = _semantic_evaluation(po)
    decision = str(ev.get("decision") or "").strip() if isinstance(ev, dict) else ""

    if overlay:
        if decision == "no_covered_change":
            beats = _beats_text(data)
            if OFF_FOCAL_CUES.search(beats) or REENTRY_CUES.search(beats):
                return "F7", tags + ["honest_no_covered_change", "prose_implies_covered"]
            return "F7", tags + ["honest_no_covered_change"]
        if decision == "covered_change":
            if props:
                if _honest_f0(data):
                    return "F0", tags + ["semantic_evaluation"]
                return "F4", tags + ["prose_structure_contradiction", "semantic_evaluation"]
            return "F2", tags + ["covered_change_without_proposals"]
        if props:
            if _honest_f0(data):
                return "F0", tags
            return "F4", tags + ["prose_structure_contradiction"]
        if raw_has_key and '"semantic_proposals": []' in raw:
            return "F3", tags + ["performative_structure", "empty_array_cosplay"]
        if "semantic_proposals" in po and po.get("semantic_proposals") == []:
            return "F3", tags + ["performative_structure"]
        return "F2", tags + ["semantic_omission"]

    if props:
        if _honest_f0(data):
            return "F0", tags
        return "F4", tags

    beats = _beats_text(data)
    if OFF_FOCAL_CUES.search(beats) or REENTRY_CUES.search(beats):
        return "F2", tags + ["semantic_omission", "prose_implies_covered"]

    return "F7", tags


def analyze_session(session_dir: Path) -> dict[str, Any]:
    turns: list[dict[str, Any]] = []
    for fp in sorted(session_dir.rglob("*_full.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("bot_type") != "character":
            continue
        primary, secondary = classify_turn(data)
        meta = _overlay_meta(data)
        opportunity = _overlay_opportunity(data)
        applied = _overlay_applied(data)
        aligned = _actor_aligned(data)
        props = _proposals(data)
        semantic_decision = _semantic_decision_label(data)
        turns.append(
            {
                "file": fp.name,
                "bot": data.get("bot_name"),
                "turn": data.get("turn_number"),
                "overlay_opportunity": opportunity,
                "overlay_applied": applied,
                "overlay_targeted": applied,
                "actor_aligned": aligned,
                "overlay_target_actor": meta.get("overlay_target_actor"),
                "overlay_skipped_reason": meta.get("overlay_skipped_reason"),
                "overlay_schedule_mode": meta.get("overlay_schedule_mode"),
                "primary": primary,
                "secondary": secondary,
                "proposal_count": len(props),
                "semantic_decision": semantic_decision,
            }
        )
    codes = Counter(t["primary"] for t in turns)
    opportunities = [t for t in turns if t["overlay_opportunity"]]
    applied_turns = [t for t in turns if t["overlay_applied"]]
    skipped_turns = [
        t
        for t in opportunities
        if not t["overlay_applied"]
        and t.get("overlay_skipped_reason") == "target_actor_did_not_act"
    ]
    overlay_aligned = [t for t in applied_turns if t["actor_aligned"] is True]
    overlay_emit = sum(1 for t in applied_turns if t["proposal_count"] > 0)
    aligned_f0 = sum(1 for t in overlay_aligned if t["primary"] == "F0")
    applied_decisions = Counter(t["semantic_decision"] for t in applied_turns)
    semantic_engagement = sum(
        1
        for t in applied_turns
        if t["semantic_decision"] in {"covered_change", "no_covered_change"}
    )
    return {
        "session": session_dir.name,
        "character_turns": len(turns),
        "codes": dict(codes),
        "f0_count": sum(1 for t in turns if t["primary"] == "F0"),
        "overlay_opportunities": len(opportunities),
        "overlay_applied_turns": len(applied_turns),
        "overlay_skipped_turns": len(skipped_turns),
        "overlay_targeted_turns": len(applied_turns),
        "overlay_actor_aligned_turns": len(overlay_aligned),
        "overlay_aligned_f0": aligned_f0,
        "overlay_nonempty_emit": overlay_emit,
        "applied_overlay_codes": dict(Counter(t["primary"] for t in applied_turns)),
        "applied_semantic_decisions": dict(applied_decisions),
        "overlay_semantic_engagement": semantic_engagement,
        "turns": turns,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()
    base = REPO_ROOT  # patched M13.6 / "rp_app" / "data" / "rp_audits"
    results = [
        analyze_session(base / s if s.startswith("session_") else base / f"session_{s}")
        for s in args.sessions
        if (base / (s if s.startswith("session_") else f"session_{s}")).is_dir()
    ]
    out = {"sessions": results}
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    for r in results:
        print(
            f"{r['session']}: turns={r['character_turns']} F0={r['f0_count']} codes={r['codes']} "
            f"overlay_opportunities={r['overlay_opportunities']} "
            f"applied={r['overlay_applied_turns']} skipped={r['overlay_skipped_turns']} "
            f"aligned_f0={r['overlay_aligned_f0']}/{r['overlay_actor_aligned_turns']} "
            f"applied_codes={r.get('applied_overlay_codes', {})} "
            f"decisions={r.get('applied_semantic_decisions', {})} "
            f"engagement={r.get('overlay_semantic_engagement', 0)}/{r['overlay_applied_turns']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

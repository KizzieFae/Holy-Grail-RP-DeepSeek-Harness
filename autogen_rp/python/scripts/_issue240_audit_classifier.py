"""Issue #240 V1 matrix classifier — investigation helper, not product code."""
from __future__ import annotations

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


def _overlay_demands_proposals(data: dict[str, Any]) -> bool:
    trig = str(data.get("effective_user_trigger") or "")
    t = trig.lower()
    return "semantic_proposals" in t and (
        "required:" in t
        or "required " in t
        or "must include" in t
        or "must emit" in t
        or "same required" in t
    )


def _expected_overlay_actor(data: dict[str, Any]) -> str | None:
    trig = str(data.get("effective_user_trigger") or "")
    m = _ONLY_ACTOR.search(trig)
    if not m:
        return None
    return str(m.group(1) or "").strip()


def _actor_aligned(data: dict[str, Any]) -> bool | None:
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


def _proposals(data: dict[str, Any]) -> list[dict[str, Any]]:
    po = data.get("parsed_output") or {}
    sp = po.get("semantic_proposals")
    if not isinstance(sp, list):
        return []
    return [p for p in sp if isinstance(p, dict)]


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

    overlay = _overlay_demands_proposals(data)
    props = _proposals(data)
    raw_has_key = "semantic_proposals" in str(data.get("raw_response") or "")

    if overlay:
        if props:
            if _honest_f0(data):
                return "F0", tags
            return "F4", tags + ["prose_structure_contradiction"]
        if raw_has_key and '"semantic_proposals": []' in str(data.get("raw_response") or ""):
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
        overlay = _overlay_demands_proposals(data)
        aligned = _actor_aligned(data)
        props = _proposals(data)
        turns.append(
            {
                "file": fp.name,
                "bot": data.get("bot_name"),
                "turn": data.get("turn_number"),
                "overlay_targeted": overlay,
                "actor_aligned": aligned,
                "primary": primary,
                "secondary": secondary,
                "proposal_count": len(props),
                "topology": "v1",
            }
        )
    codes = Counter(t["primary"] for t in turns)
    overlay_turns = [t for t in turns if t["overlay_targeted"]]
    overlay_aligned = [t for t in overlay_turns if t["actor_aligned"] is True]
    overlay_emit = sum(1 for t in overlay_turns if t["proposal_count"] > 0)
    aligned_f0 = sum(1 for t in overlay_aligned if t["primary"] == "F0")
    return {
        "session": session_dir.name,
        "character_turns": len(turns),
        "codes": dict(codes),
        "f0_count": sum(1 for t in turns if t["primary"] == "F0"),
        "overlay_targeted_turns": len(overlay_turns),
        "overlay_actor_aligned_turns": len(overlay_aligned),
        "overlay_aligned_f0": aligned_f0,
        "overlay_nonempty_emit": overlay_emit,
        "turns": turns,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()
    base = Path(__file__).resolve().parent.parent / "rp_app" / "data" / "rp_audits"
    results = [
        analyze_session(base / s if s.startswith("session_") else base / f"session_{s}")
        for s in args.sessions
        if (base / (s if s.startswith("session_") else f"session_{s}")).is_dir()
    ]
    out = {"sessions": results, "topology": "v1"}
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    for r in results:
        print(
            f"{r['session']}: turns={r['character_turns']} F0={r['f0_count']} codes={r['codes']} "
            f"overlay_emit={r['overlay_nonempty_emit']}/{r['overlay_targeted_turns']} "
            f"aligned_f0={r['overlay_aligned_f0']}/{r['overlay_actor_aligned_turns']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

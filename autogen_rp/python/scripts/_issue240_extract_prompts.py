"""Extract character prompt metrics from #240 V1 matrix audit sessions."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _issue240_audit_classifier import classify_turn, _overlay_demands_proposals, _actor_aligned

AUDITS = Path(__file__).resolve().parent.parent / "rp_app" / "data" / "rp_audits"
SEMANTIC_HEADER = "FOR THIS BEAT — SEMANTIC SELF-REPORT"


def _structural_summary(data: dict[str, Any]) -> dict[str, Any]:
    sys_c = ""
    for msg in data.get("input_messages") or []:
        if msg.get("role") == "system":
            sys_c = str(msg.get("content") or "")
            break
    out_rules_idx = sys_c.find("OUTPUT RULES:")
    trig_idx = sys_c.find("TRIGGER FOR THIS BEAT:")
    sem_idx = sys_c.find(SEMANTIC_HEADER)
    out_len = len(sys_c) - out_rules_idx if out_rules_idx >= 0 else None
    return {
        "system_chars": len(sys_c),
        "trigger_in_system_offset": trig_idx if trig_idx >= 0 else None,
        "trigger_in_system_pct": round(100 * trig_idx / len(sys_c), 1) if trig_idx >= 0 and sys_c else None,
        "semantic_self_report_offset": sem_idx if sem_idx >= 0 else None,
        "semantic_self_report_pct": round(100 * sem_idx / len(sys_c), 1) if sem_idx >= 0 and sys_c else None,
        "output_rules_offset": out_rules_idx if out_rules_idx >= 0 else None,
        "output_rules_chars": out_len,
        "output_rules_pct_from_end": round(100 * out_len / len(sys_c), 1) if out_len and sys_c else None,
        "has_v1_opening": "Act primarily as this character" in sys_c,
        "has_doctrine_phrase": "not compliance theater" in sys_c,
    }


def extract_session(session_dir: Path, out_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fp in sorted(session_dir.rglob("*_full.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("bot_type") != "character":
            continue
        primary, secondary = classify_turn(data)
        summary = _structural_summary(data)
        row = {
            "session": session_dir.name,
            "file": fp.name,
            "turn": data.get("turn_number"),
            "bot": data.get("bot_name"),
            "overlay_targeted": _overlay_demands_proposals(data),
            "actor_aligned": _actor_aligned(data),
            "classification": primary,
            "secondary": secondary,
            "topology": "v1",
            **summary,
        }
        rows.append(row)
        slug = f"{session_dir.name}_turn{int(data.get('turn_number') or 0):02d}_{data.get('bot_name', 'unknown')}"
        (out_dir / f"{slug}.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--out-dir", default="data/issue240_runs/prompt_extractions")
    args = ap.parse_args()
    out_dir = Path(__file__).resolve().parent.parent / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    for s in args.sessions:
        sess_dir = AUDITS / (s if s.startswith("session_") else f"session_{s}")
        if sess_dir.is_dir():
            all_rows.extend(extract_session(sess_dir, out_dir))
    index = out_dir / "INDEX.json"
    index.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_rows)} rows to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

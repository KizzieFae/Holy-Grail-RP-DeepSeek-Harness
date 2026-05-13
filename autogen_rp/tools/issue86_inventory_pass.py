#!/usr/bin/env python3
"""Issue #86 — deterministic rp_audits inventory (read-only; no mutations)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def session_sort_key(name: str) -> tuple[int, str]:
    m = re.match(r"session_(\d+)(.*)$", name, re.I)
    if m:
        return (int(m.group(1)), m.group(2) or "")
    return (10**9, name)


def parse_round_turn(p: Path) -> tuple[int, int]:
    """Best-effort from filename: ..._roundNNN_turnMM_..."""
    s = p.name
    rm = re.search(r"_round(\d{3})_turn(\d{2})_", s)
    if rm:
        return (int(rm.group(1)), int(rm.group(2)))
    return (0, 0)


def is_narrator_full(p: Path) -> bool:
    return "_narrator_" in p.name and p.name.endswith("_full.json")


def is_director_full(p: Path) -> bool:
    return "_director_" in p.name and p.name.endswith("_full.json")


def character_fulls(session_dir: Path) -> list[Path]:
    out: list[Path] = []
    for p in session_dir.rglob("*_full.json"):
        if not p.is_file():
            continue
        if is_narrator_full(p) or is_director_full(p):
            continue
        out.append(p)
    out.sort(key=lambda x: (parse_round_turn(x), str(x)))
    return out


def narrator_fulls(session_dir: Path) -> list[Path]:
    out = [p for p in session_dir.rglob("*_full.json") if p.is_file() and is_narrator_full(p)]
    out.sort(key=lambda x: (parse_round_turn(x), str(x)))
    return out


def load_json(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return None
        o = json.loads(raw)
        return o if isinstance(o, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def has_ctar_row(d: dict | None) -> bool:
    if not d:
        return False
    meta = d.get("metadata")
    if not isinstance(meta, dict):
        return False
    ctar = meta.get("ctar")
    return isinstance(ctar, dict) and "continuity_turn_index" in ctar


def has_ctx_cti(d: dict | None) -> bool:
    if not d:
        return False
    cs = d.get("context_snapshot")
    if not isinstance(cs, dict):
        return False
    return "continuity_turn_index" in cs


def has_phase1_idx(d: dict | None) -> bool:
    if not d:
        return False
    meta = d.get("metadata")
    if not isinstance(meta, dict):
        return False
    sg = meta.get("scene_grounding")
    if not isinstance(sg, dict):
        return False
    p1 = sg.get("phase1")
    if not isinstance(p1, dict):
        return False
    return "continuity_turn_index" in p1


def join_signals(d: dict | None) -> dict[str, bool]:
    return {
        "metadata_ctar": has_ctar_row(d),
        "context_snapshot_continuity_turn_index": has_ctx_cti(d),
        "phase1_continuity_turn_index": has_phase1_idx(d),
    }


def coverage_from_three(char_a: dict | None, char_b: dict | None, narr: dict | None) -> str:
    rows = [join_signals(char_a), join_signals(char_b), join_signals(narr)]
    # Primary agreed signal: metadata.ctar
    ctar_hits = sum(1 for r in rows if r["metadata_ctar"])
    if ctar_hits == 3:
        return "full"
    if ctar_hits == 0:
        # any secondary?
        any_secondary = any(
            r["context_snapshot_continuity_turn_index"] or r["phase1_continuity_turn_index"]
            for r in rows
        )
        if any_secondary:
            return "partial"
        return "none"
    return "partial"


def find_narrator_same_turn(narrators: list[Path], r: int, t: int) -> Path | None:
    for p in narrators:
        pr, pt = parse_round_turn(p)
        if pr == r and pt == t:
            return p
    return None


def inventory_session(session_dir: Path) -> dict:
    name = session_dir.name
    mnum = re.match(r"session_(\d+)", name, re.I)
    session_num = int(mnum.group(1)) if mnum else -1

    row: dict = {
        "session_path": str(session_dir.as_posix()),
        "session_number": session_num,
        "artifact__manifest": (session_dir / "_manifest.json").is_file(),
        "artifact__round_index": (session_dir / "_round_index.json").is_file(),
        "artifact__narrative": (session_dir / "_narrative.json").is_file(),
        "artifact__audit_summary": (session_dir / "_audit_summary.json").is_file(),
        "artifact__round_dirs": False,
        # Issue #69 spec artifact; not emitted by shipped tooling (#211). True only if
        # present on disk (adhoc/future evaluator).
        "artifact__scene_eval_v2": (session_dir / "_scene_eval_v2.json").is_file(),
        "artifact__fact_track_glob": bool(list(session_dir.glob("fact_track__*.json"))),
        "tag__36_retrieval_session_present": False,
        "tag__36_retrieval_mode": "unknown",
        "tag__79_summary_v1": False,
        "tag__79_status_v1": False,
        "tag__79_absent": False,
        "tag__72_join_coverage": "unknown",
        "tag__retrieval_run_level": "unknown",
        "tag__83_signal": "unknown",
        "notes": "",
    }

    try:
        round_dirs = [
            d
            for d in session_dir.iterdir()
            if d.is_dir() and d.name.startswith("round_")
        ]
    except OSError:
        round_dirs = []
    row["artifact__round_dirs"] = len(round_dirs) > 0

    summary_path = session_dir / "_audit_summary.json"
    if not row["artifact__audit_summary"]:
        row["tag__79_absent"] = True
        row["notes"] = (row["notes"] + "; " if row["notes"] else "") + "missing _audit_summary.json"
    summ = load_json(summary_path) if row["artifact__audit_summary"] else None
    if summ is None and row["artifact__audit_summary"]:
        row["tag__79_absent"] = True
        row["notes"] = (row["notes"] + "; " if row["notes"] else "") + "audit_summary unreadable or empty"

    if isinstance(summ, dict):
        if "continuity_observability_summary_v1" in summ:
            row["tag__79_summary_v1"] = True
        elif "continuity_observability_status_v1" in summ:
            row["tag__79_status_v1"] = True
        else:
            row["tag__79_absent"] = True

        rs = summ.get("retrieval_session")
        if isinstance(rs, dict):
            row["tag__36_retrieval_session_present"] = True
            mode = str(rs.get("retrieval_mode", "") or "").lower()
            if mode in ("on", "off"):
                row["tag__36_retrieval_mode"] = mode
                row["tag__retrieval_run_level"] = mode
            else:
                row["tag__36_retrieval_mode"] = "unknown"
                row["tag__retrieval_run_level"] = "unknown"
        else:
            row["tag__36_retrieval_mode"] = "unknown"
            row["tag__retrieval_run_level"] = "unknown"

        cos = summ.get("continuity_observability_summary_v1")
        if isinstance(cos, dict):
            sao = cos.get("session_audit_origin")
            if isinstance(sao, dict):
                hb = bool(sao.get("has_bypass"))
                bb = sao.get("bypass_beats")
                bypass_nonempty = isinstance(bb, list) and len(bb) > 0
                if hb or bypass_nonempty:
                    row["tag__83_signal"] = "has_bypass_signal"
                else:
                    row["tag__83_signal"] = "no_signal"
            else:
                row["tag__83_signal"] = "unknown"
        else:
            row["tag__83_signal"] = "unknown"

    ch = character_fulls(session_dir)
    na = narrator_fulls(session_dir)
    char_first: dict | None = None
    char_last: dict | None = None
    narr_pick: dict | None = None
    narr_path: Path | None = None
    notes_parts: list[str] = []

    if not ch:
        row["tag__72_join_coverage"] = "unknown"
        notes_parts.append("no_character_full_json")
    else:
        p_first, p_last = ch[0], ch[-1]
        char_first = load_json(p_first)
        char_last = load_json(p_last) if p_last != p_first else char_first
        r1, t1 = parse_round_turn(p_first)
        narr_path = find_narrator_same_turn(na, r1, t1)
        if narr_path is None:
            r2, t2 = parse_round_turn(p_last)
            narr_path = find_narrator_same_turn(na, r2, t2)
        if narr_path is None and na:
            narr_path = na[0]
            notes_parts.append("narrator_matched_first_turn_missing_used_first_narrator")
        narr_pick = load_json(narr_path) if narr_path else None
        if char_first is None or char_last is None:
            row["tag__72_join_coverage"] = "unknown"
            notes_parts.append("character_full_parse_fail")
        else:
            row["tag__72_join_coverage"] = coverage_from_three(char_first, char_last, narr_pick)

    if notes_parts:
        row["notes"] = (row["notes"] + "; " if row.get("notes") else "") + "; ".join(notes_parts)

    row["sample_paths"] = {
        "first_character_full": str(ch[0].as_posix()) if ch else None,
        "last_character_full": str(ch[-1].as_posix()) if len(ch) > 1 else (str(ch[0].as_posix()) if ch else None),
        "narrator_full": str(narr_path.as_posix()) if narr_path else None,
    }

    return row


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "python" / "rp_app" / "data" / "rp_audits"
    if not root.is_dir():
        print(json.dumps({"error": "rp_audits not found", "path": str(root)}))
        return 1

    dirs = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("session_")]
    dirs.sort(key=lambda p: session_sort_key(p.name))

    rows = [inventory_session(d) for d in dirs]
    out = {"root": str(root.as_posix()), "session_count": len(rows), "sessions": rows}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Scan character *_full.json audits: episodic:issue vs ACTIVE ISSUES / active_issue_ids.

Read-only investigation helper. Does not change runtime behavior.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]
_ROOT = _PY_ROOT / "rp_app" / "data" / "rp_audits"


def extract_issue_ids_from_episodic(text: str) -> list[str]:
    ids: list[str] = []
    if "episodic:issue" not in text:
        return ids
    for m in re.finditer(
        r"\[([^\]|]+)\s*\|\s*episodic:issue\]\s*\nIssue\s+(\S+)",
        text,
    ):
        ids.append(m.group(2).strip())
    return ids


def active_issues_block(text: str) -> tuple[list[str] | None, str]:
    m = re.search(
        r"ACTIVE ISSUES / PRESSURES \(ACTIONABLE NOW\):\s*\n(\[[\s\S]*?\])\n\nSTALLED",
        text,
    )
    if not m:
        return None, "no_active_issues_section"
    block = m.group(1)
    try:
        arr = json.loads(block)
    except json.JSONDecodeError:
        return None, "active_issues_json_fail"
    ids: list[str] = []
    for item in arr:
        if isinstance(item, dict) and item.get("issue_id"):
            ids.append(str(item["issue_id"]))
    return ids, "ok"


def scene_active_issue_ids(text: str) -> list[str] | None:
    # First occurrence is inside CURRENT SCENE STATE JSON
    m = re.search(r'"active_issue_ids"\s*:\s*\[', text)
    if not m:
        return None
    start = m.end() - 1
    depth = 0
    i = start
    while i < len(text):
        c = text[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                fragment = text[start : i + 1]
                try:
                    return list(json.loads(fragment))
                except json.JSONDecodeError:
                    return None
        i += 1
    return None


def director_active_issues(path: Path) -> list[str] | None:
    """Same round/turn director *_full.json (replace character slug after _turnNN_)."""
    name = path.name
    director_name = re.sub(
        r"^(.+_turn\d+_).+_full\.json$",
        r"\1director_full.json",
        name,
    )
    if director_name == name:
        return None
    director_path = path.parent / director_name
    if not director_path.is_file():
        return None
    try:
        data = json.loads(director_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    msgs = data.get("input_messages") or []
    if not msgs:
        return None
    content = msgs[0].get("content") or ""
    # Director payload is JSON embedded in string
    jm = re.search(r'"active_issues"\s*:\s*\[', content)
    if not jm:
        return None
    start = jm.end() - 1
    depth = 0
    i = start
    while i < len(content):
        c = content[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                fragment = content[start : i + 1]
                try:
                    arr = json.loads(fragment)
                except json.JSONDecodeError:
                    return None
                ids = []
                for item in arr:
                    if isinstance(item, dict) and item.get("issue_id"):
                        ids.append(str(item["issue_id"]))
                return ids
        i += 1
    return None


def main() -> int:
    root = _ROOT
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"No audits dir: {root}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for p in sorted(root.rglob("*_full.json")):
        low = p.name.lower()
        if "director" in low or "narrator" in low:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        msgs = data.get("input_messages") or []
        if not msgs or msgs[0].get("role") != "system":
            continue
        content = msgs[0].get("content") or ""
        if "RETRIEVED REFERENCE MATERIAL" not in content:
            continue
        if "episodic:issue" not in content:
            continue
        epi_ids = extract_issue_ids_from_episodic(content)
        ai_ids, ai_parse = active_issues_block(content)
        sids = scene_active_issue_ids(content)
        dir_ids = director_active_issues(p)
        for eid in epi_ids:
            in_ai = ai_ids is not None and eid in ai_ids
            in_scene = sids is not None and eid in sids
            in_dir = dir_ids is not None and eid in dir_ids
            rows.append(
                {
                    "path": str(p),
                    "session": data.get("session_number"),
                    "round": data.get("round_number"),
                    "turn": data.get("turn_number"),
                    "bot": data.get("bot_name"),
                    "episodic_issue_id": eid,
                    "in_active_issues": in_ai,
                    "in_scene_active_issue_ids": in_scene,
                    "in_director_active_issues": in_dir,
                    "active_issues_parse": ai_parse,
                    "n_active_issues": len(ai_ids or []),
                    "n_scene_ids": len(sids or []),
                }
            )

    mismatches = [
        r
        for r in rows
        if not r["in_active_issues"] or not r["in_scene_active_issue_ids"]
    ]
    total_epi_issue_lines = len(rows)
    print(json.dumps({"total_episodic_issue_rows": total_epi_issue_lines, "mismatches": len(mismatches), "rows": rows, "mismatch_detail": mismatches}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

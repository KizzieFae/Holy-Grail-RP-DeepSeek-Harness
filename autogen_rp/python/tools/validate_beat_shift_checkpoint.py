#!/usr/bin/env python3
"""Run automated beat-shift replay validation and scan on-disk director audits.

Usage (from autogen_rp/python):

    python tools/validate_beat_shift_checkpoint.py

Exit code 0 if pytest passes; audit scan is informational.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RP_APP = ROOT / "rp_app"
AUDITS = RP_APP / "data" / "rp_audits"


def _scan_director_audits_for_beat_shift() -> tuple[int, int]:
    """Return (files_with_beat_shift_true, total_director_full_json)."""
    if not AUDITS.is_dir():
        return 0, 0
    with_true = 0
    total = 0
    for path in AUDITS.rglob("*_full.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if '"bot_type"' not in text and "'bot_type'" not in text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if str(data.get("bot_type", "") or "").lower() != "director":
            continue
        total += 1
        meta = data.get("metadata") or {}
        if meta.get("beat_shift_active") is True:
            with_true += 1
    return with_true, total


def main() -> int:
    print("== Beat-shift replay tests (no LLM) ==", flush=True)
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "tests" / "test_beat_shift_replay_validation.py"),
            "-q",
        ],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        return r.returncode

    w, t = _scan_director_audits_for_beat_shift()
    print(flush=True)
    print("== On-disk director *_full.json audit scan ==", flush=True)
    print(f"Director full entries scanned: {t}")
    print(f"With metadata.beat_shift_active == true: {w}")
    if t > 0 and w == 0:
        print(
            "(If you expected true counts: older director audits predate metadata.beat_shift_active; "
            "generate new rounds after upgrading.)"
        )
    if t == 0:
        print(
            "(No director full audits found under rp_app/data/rp_audits — "
            "run a session with auditing enabled, then re-run this script.)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

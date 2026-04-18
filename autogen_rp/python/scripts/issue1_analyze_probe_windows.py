#!/usr/bin/env python3
"""Issue #1: find valid (priming -> probe) windows on non-owner N; run fact_spec (#58).

Reads one or more audit session directories under rp_app/data/rp_audits/session_*.
Usage (from autogen_rp/python)::

    python scripts/issue1_analyze_probe_windows.py \\
        --sessions ../../rp_app/data/rp_audits/session_123 \\
        --n-bot-name Magpie \\
        --nonce ZXQ-9173-PRIME \\
        --probe-substr "Who is the instigator" \\
        --fact-spec rp_app/data/issue1_fact_spec_v1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from audit_fact_tracking import analyze_fact_tracking, validate_fact_spec  # noqa: E402
from issue29_investigation import load_character_audit_rows  # noqa: E402


def _prompt(row: dict[str, Any]) -> str:
    return str(row.get("content", "") or "")


def find_valid_window(
    rows_n: list[dict[str, Any]],
    *,
    nonce: str,
    probe_substr: str,
) -> tuple[int, int] | None:
    for i in range(len(rows_n) - 1):
        if nonce not in _prompt(rows_n[i]):
            continue
        if probe_substr not in _prompt(rows_n[i + 1]):
            continue
        return (i, i + 1)
    return None


def main() -> None:
    p = argparse.ArgumentParser(description="Issue #1 probe window + fact_spec analysis")
    p.add_argument(
        "--sessions",
        nargs="+",
        type=Path,
        required=True,
        help="Audit session directory paths (each contains *_full.json)",
    )
    p.add_argument("--n-bot-name", required=True, help="Non-owner character bot_name filter")
    p.add_argument("--nonce", default="ZXQ-9173-PRIME")
    p.add_argument("--probe-substr", default="Who is the instigator")
    p.add_argument("--fact-spec", type=Path, required=True)
    args = p.parse_args()

    spec = json.loads(args.fact_spec.read_text(encoding="utf-8"))
    ok, reason = validate_fact_spec(spec)
    if not ok:
        print(f"invalid fact_spec: {reason}", file=sys.stderr)
        sys.exit(1)

    # Align actor_scope with CLI
    scope = spec.get("actor_scope")
    if isinstance(scope, dict) and scope.get("kind") == "character_name":
        scope["name"] = args.n_bot_name

    report: list[dict[str, object]] = []
    for sess in args.sessions:
        sess = sess.resolve()
        if not sess.is_dir():
            report.append({"session": str(sess), "error": "not_a_directory"})
            continue
        rows = load_character_audit_rows(sess)
        rows_n = [r for r in rows if r.get("bot_name") == args.n_bot_name]
        win = find_valid_window(rows_n, nonce=args.nonce, probe_substr=args.probe_substr)
        entry: dict[str, object] = {
            "session": str(sess),
            "n_row_count": len(rows_n),
            "valid_window": win is not None,
        }
        if win is not None:
            i0, i1 = win
            entry["priming_turn"] = rows_n[i0].get("turn_number")
            entry["probe_turn"] = rows_n[i1].get("turn_number")
            analysis = analyze_fact_tracking(sess, spec)
            entry["failure_classification"] = analysis.get("failure_classification")
            entry["indeterminate_reason"] = analysis.get("indeterminate_reason")
            entry["T_intro"] = analysis.get("T_intro")
            entry["T_divergence"] = analysis.get("T_divergence")
        report.append(entry)

    print(json.dumps({"runs": report}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

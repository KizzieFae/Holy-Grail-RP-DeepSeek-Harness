#!/usr/bin/env python3
"""Reconstruct Player-operation latency from execution evidence (#158)."""
import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = REPO / "data" / "execution_evidence"


def parse_iso(ts):
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load_session(session_id, evidence_root):
    base = evidence_root / session_id
    index = json.loads((base / "index.json").read_text(encoding="utf-8"))
    attempts = {}
    for eid in index.get("attempt_ids", []):
        p = base / "attempts" / f"{eid}.json"
        if p.exists():
            attempts[eid] = json.loads(p.read_text(encoding="utf-8"))
    return index, attempts


def operation_records(attempts):
    ops = {}
    for eid, att in attempts.items():
        corr = att.get("correlation") or {}
        role = corr.get("role")
        if role == "application_lifecycle":
            op = corr.get("operation_id") or (att.get("decision") or {}).get("operation_id")
            milestone = corr.get("milestone") or (att.get("decision") or {}).get("milestone")
            if op and milestone:
                ops.setdefault(op, {})[milestone] = att
        if role == "execution_span":
            op = corr.get("operation_id")
            if op:
                ops.setdefault(op, {}).setdefault("spans", []).append(att)
    return ops


def inference_rows(attempts, operation_id=None, round_id=None):
    rows = []
    for eid, att in attempts.items():
        if not att.get("request"):
            continue
        corr = att.get("correlation") or {}
        if operation_id and corr.get("operation_id") not in (None, operation_id):
            assoc_op = (att.get("associations") or {}).get("operation_id")
            if assoc_op != operation_id:
                continue
        if round_id and corr.get("hg_round_id") != round_id:
            continue
        timing = (att.get("inference_health") or {}).get("timing") or {}
        usage = (att.get("inference_health") or {}).get("usage") or {}
        rows.append({
            "evidence_id": eid,
            "role": corr.get("role"),
            "kind": corr.get("inference_kind"),
            "timing_observed": timing.get("timing_observed"),
            "wall_ms": timing.get("inference_wall_clock_ms"),
            "started_at": timing.get("started_at"),
            "ended_at": timing.get("ended_at"),
            "tokens": usage.get("total_tokens"),
            "recorded_at": att.get("recorded_at"),
        })
    rows.sort(key=lambda r: r.get("started_at") or r.get("recorded_at") or "")
    return rows


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: reconstruct_round_latency.py <hg_session_id> [--operation <id>] [--evidence-root path]")
        return 2
    session_id = argv[0]
    operation_id = None
    evidence_root = DEFAULT_EVIDENCE
    i = 1
    while i < len(argv):
        if argv[i] == "--operation" and i + 1 < len(argv):
            operation_id = argv[i + 1]
            i += 2
        elif argv[i] == "--evidence-root" and i + 1 < len(argv):
            evidence_root = Path(argv[i + 1])
            i += 2
        else:
            i += 1
    index, attempts = load_session(session_id, evidence_root)
    ops = operation_records(attempts)
    print(f"session={session_id} attempts={len(attempts)}")
    print(json.dumps({"timing_index": index.get("timing"), "round_activity": index.get("round_activity")}, indent=2))
    for op_id, rec in sorted(ops.items()):
        if operation_id and op_id != operation_id:
            continue
        began = rec.get("operation_began")
        terminal = rec.get("round_terminal_succeeded") or rec.get("round_terminal_failed")
        w_ms = None
        if began and terminal:
            b = parse_iso(began.get("recorded_at"))
            e = parse_iso(terminal.get("recorded_at"))
            if b and e:
                w_ms = (e - b).total_seconds() * 1000
        print(f"\noperation={op_id} W_ms~={w_ms}")
        for span in rec.get("spans", []):
            ex = span.get("execution") or {}
            print(f"  span {span.get('correlation',{}).get('phase_id')} wall_ms={ex.get('wall_ms')}")
        for row in inference_rows(attempts, operation_id=op_id):
            print(f"  inference {row['kind']} observed={row['timing_observed']} wall_ms={row['wall_ms']} tokens={row['tokens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

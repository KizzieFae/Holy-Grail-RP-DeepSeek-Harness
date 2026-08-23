#!/usr/bin/env python3
"""List Holy Grail V2 execution evidence for a session."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from _repo_paths import EXECUTION_EVIDENCE_DIR, REPO_ROOT  # noqa: E402


def session_evidence_dir(hg_session_id: str) -> Path:
    return EXECUTION_EVIDENCE_DIR / hg_session_id


def load_index(hg_session_id: str) -> dict | None:
    index_path = session_evidence_dir(hg_session_id) / "index.json"
    if not index_path.is_file():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def load_attempt(hg_session_id: str, evidence_id: str) -> dict | None:
    attempt_path = session_evidence_dir(hg_session_id) / "attempts" / f"{evidence_id}.json"
    if not attempt_path.is_file():
        return None
    return json.loads(attempt_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hg_session_id", help="Holy Grail session id")
    parser.add_argument(
        "--round",
        help="Filter to one hg_round_id using index.json rounds map",
    )
    parser.add_argument(
        "--attempt",
        help="Print one attempt record by evidence_id",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a human summary",
    )
    parser.add_argument(
        "--semantic-hard",
        action="store_true",
        help="List evidence_ids indexed with hard semantic findings",
    )
    parser.add_argument(
        "--semantic-soft",
        action="store_true",
        help="List evidence_ids indexed with soft semantic findings",
    )
    parser.add_argument(
        "--dimension",
        help="Filter semantic index by dimension (e.g. R02b, R11)",
    )
    parser.add_argument(
        "--multi-candidate",
        action="store_true",
        help="List inference_ids with multiple character candidates",
    )
    parser.add_argument(
        "--evaluator-failure",
        action="store_true",
        help="List evidence_ids where semantic evaluator infrastructure failed",
    )
    parser.add_argument(
        "--residual-soft",
        action="store_true",
        help="List evidence_ids with recorded residual soft concerns",
    )
    parser.add_argument(
        "--exhausted-hard",
        action="store_true",
        help="List inference_ids where hard correction budget was exhausted",
    )
    args = parser.parse_args()

    root = session_evidence_dir(args.hg_session_id)
    if not root.is_dir():
        print(f"No execution evidence directory: {root}", file=sys.stderr)
        return 1

    if args.attempt:
        attempt = load_attempt(args.hg_session_id, args.attempt)
        if attempt is None:
            print(f"Attempt not found: {args.attempt}", file=sys.stderr)
            return 1
        print(json.dumps(attempt, indent=2, ensure_ascii=False))
        return 0

    index = load_index(args.hg_session_id)
    if index is None:
        print(f"Missing index.json under {root}", file=sys.stderr)
        return 1

    semantic = index.get("semantic") or {}
    if args.semantic_hard:
        for evidence_id in semantic.get("hard_findings") or []:
            print(evidence_id)
        return 0
    if args.semantic_soft:
        for evidence_id in semantic.get("soft_findings") or []:
            print(evidence_id)
        return 0
    if args.dimension:
        for evidence_id in (semantic.get("by_dimension") or {}).get(args.dimension) or []:
            print(evidence_id)
        return 0
    if args.multi_candidate:
        for inference_id in semantic.get("multi_candidate_inferences") or []:
            print(inference_id)
        return 0
    if args.evaluator_failure:
        for evidence_id in semantic.get("evaluator_failures") or []:
            print(evidence_id)
        return 0
    if args.residual_soft:
        for evidence_id in semantic.get("residual_soft") or []:
            print(evidence_id)
        return 0
    if args.exhausted_hard:
        for inference_id in semantic.get("exhausted_hard_loops") or []:
            print(inference_id)
        return 0

    if args.json:
        print(json.dumps(index, indent=2, ensure_ascii=False))
        return 0

    print(f"repo: {REPO_ROOT}")
    print(f"session: {args.hg_session_id}")
    print(f"root: {root}")
    print(f"attempt_count: {len(index.get('attempt_ids') or [])}")
    attempt_ids = list(index.get("attempt_ids") or [])
    if args.round:
        attempt_ids = list((index.get("rounds") or {}).get(args.round) or [])
        print(f"round: {args.round}")
    for evidence_id in attempt_ids:
        attempt = load_attempt(args.hg_session_id, evidence_id)
        if not attempt:
            continue
        correlation = attempt.get("correlation") or {}
        decision = attempt.get("decision") or {}
        print(
            "- "
            f"{evidence_id} "
            f"role={correlation.get('role')} "
            f"attempt={correlation.get('attempt_index')} "
            f"inference={correlation.get('inference_id')} "
            f"outcome={decision.get('outcome')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Unified read-only turn/commit forensic navigator (#101)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from _repo_paths import (  # noqa: E402
    AUDIT_TAGS_DIR,
    DATA_DIR,
    EXECUTION_EVIDENCE_DIR,
    PLOT_COGNITION_FORENSICS_DIR,
)

from investigation._turn_forensics import (  # noqa: E402
    TurnForensicsSession,
    format_human_report,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Navigate durable forensic evidence by commit, round, turn, entry, or tag.",
    )
    parser.add_argument("hg_session_id", help="Holy Grail session id")
    parser.add_argument(
        "view",
        choices=["commit", "round", "turn", "entry", "tag"],
        help="Investigator view / anchor kind",
    )
    parser.add_argument("anchor", help="Anchor value for the selected view")
    parser.add_argument("--json", action="store_true", help="Emit hg_turn_investigator_v1 JSON")
    parser.add_argument("--sessions-root", type=Path, help="Override sessions root")
    parser.add_argument("--evidence-root", type=Path, help="Override execution evidence root")
    parser.add_argument("--tags-root", type=Path, help="Override audit tags root")
    parser.add_argument("--story-knowledge-root", type=Path, help="Override story knowledge root")
    parser.add_argument("--plot-cognition-root", type=Path, help="Override plot cognition forensics root")
    return parser.parse_args(argv)


ANCHOR_TYPES = {
    "commit": "domain_commit_id",
    "round": "hg_round_id",
    "turn": "continuity_turn_index",
    "entry": "entry_id",
    "tag": "tag_id",
}


def run(args: argparse.Namespace) -> dict:
    sessions_root = args.sessions_root or (DATA_DIR / "sessions")
    story_knowledge_root = args.story_knowledge_root or (DATA_DIR / "sessions" / "_story_knowledge")
    session = TurnForensicsSession.open(
        args.hg_session_id,
        sessions_root=sessions_root,
        evidence_root=args.evidence_root or EXECUTION_EVIDENCE_DIR,
        tags_root=args.tags_root or AUDIT_TAGS_DIR,
        story_knowledge_root=story_knowledge_root,
        plot_cognition_root=args.plot_cognition_root or PLOT_COGNITION_FORENSICS_DIR,
    )
    return session.investigate(
        anchor_type=ANCHOR_TYPES[args.view],
        anchor_value=args.anchor,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        envelope = run(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(envelope, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(format_human_report(envelope))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

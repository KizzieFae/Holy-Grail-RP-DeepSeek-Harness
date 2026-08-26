#!/usr/bin/env python3
"""Read-only NI forensic investigation CLI (#46 Package B)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from investigation._ni_forensics import (  # noqa: E402
    NiSession,
    build_envelope,
    format_human_report,
    limitation,
)
from _repo_paths import AUDIT_TAGS_DIR, EXECUTION_EVIDENCE_DIR  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trace NI forensic evidence (read-only; hg_ni_investigator_v1 output).",
    )
    parser.add_argument("hg_session_id", help="Holy Grail session id")
    parser.add_argument(
        "view",
        choices=[
            "tag",
            "round",
            "session",
            "mediation",
            "storyteller",
            "character",
            "s4",
            "lineage",
        ],
        help="Investigator view",
    )
    parser.add_argument("target", nargs="?", help="View target (tag id, round id, commit id, source id)")
    parser.add_argument("--json", action="store_true", help="Emit hg_ni_investigator_v1 JSON")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild index.ni in-memory when absent or unusable (never persisted)",
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="For tag view: re-resolve forensic_scope from current evidence",
    )
    parser.add_argument(
        "--evidence-id",
        help="For mediation view: specific mediation evidence id",
    )
    parser.add_argument("--round", help="For storyteller view: filter by round id")
    parser.add_argument(
        "--parent-inf",
        help="For character view: parent inference id (informational)",
    )
    parser.add_argument(
        "--source-id",
        help="For lineage view: source or candidate id (alternative to positional target)",
    )
    parser.add_argument(
        "--evidence-root",
        type=Path,
        help="Override execution evidence root (for fixtures/tests)",
    )
    parser.add_argument(
        "--tags-root",
        type=Path,
        help="Override audit tags root (for fixtures/tests)",
    )
    parser.add_argument(
        "--excerpt-len",
        type=int,
        default=240,
        help="Bounded excerpt length for human-readable output",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict:
    evidence_root = args.evidence_root or EXECUTION_EVIDENCE_DIR
    tags_root = args.tags_root or AUDIT_TAGS_DIR
    session = NiSession.open(
        args.hg_session_id,
        evidence_root,
        tags_root=tags_root,
        rebuild_index=args.rebuild_index,
    )

    view = args.view
    if view == "tag":
        if not args.target:
            raise SystemExit("tag view requires <tag_id>")
        return session.view_tag(args.target, resolve=args.resolve)
    if view == "round":
        if not args.target:
            raise SystemExit("round view requires <hg_round_id>")
        return session.view_round(args.target)
    if view == "session":
        return session.view_session()
    if view == "mediation":
        return session.view_mediation(args.evidence_id)
    if view == "storyteller":
        return session.view_storyteller(args.round)
    if view == "character":
        return session.view_character(args.parent_inf)
    if view == "s4":
        if not args.target:
            raise SystemExit("s4 view requires <domain_commit_id>")
        return session.view_s4(args.target)
    if view == "lineage":
        source_id = args.source_id or args.target
        if not source_id:
            raise SystemExit("lineage view requires --source-id or positional <source_id>")
        return session.trace_lineage(source_id)
    return build_envelope(
        view=view,
        hg_session_id=args.hg_session_id,
        index_source=session.index_source,
        limitations=[limitation("unknown_view", f"Unknown view: {view}")],
        payload={},
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        envelope = run(args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
    else:
        print(format_human_report(envelope, excerpt_len=args.excerpt_len), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

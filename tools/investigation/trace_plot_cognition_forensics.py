#!/usr/bin/env python3
"""Read-only Plot Cognition Forensic Chronicle investigation CLI (#64)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from investigation._plot_cognition_forensics import (  # noqa: E402
    format_commit_effects,
    format_integrity_gaps,
    format_layer_b_chain,
    format_timeline,
    resolve_scope,
)
from _repo_paths import PLOT_COGNITION_FORENSICS_DIR  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trace Plot Cognition Forensic Chronicle (read-only; investigator tooling).",
    )
    parser.add_argument("plot_cognition_scope_id", help="Plot cognition scope id")
    parser.add_argument(
        "view",
        choices=[
            "timeline",
            "commit",
            "integrity",
            "layer_b",
            "json",
        ],
        help="Investigator view",
    )
    parser.add_argument("target", nargs="?", help="View target (domain commit id or batch id)")
    parser.add_argument("--json", action="store_true", help="Emit JSON envelope")
    parser.add_argument("--forensics-root", type=Path, help="Override chronicle root")
    parser.add_argument("--evidence-root", type=Path, help="Override execution evidence root")
    parser.add_argument("--session", help="Session id for execution-evidence joins")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scope = resolve_scope(
        args.plot_cognition_scope_id,
        forensics_root=args.forensics_root or PLOT_COGNITION_FORENSICS_DIR,
    )
    if scope is None:
        print(f"Chronicle not found for scope {args.plot_cognition_scope_id}", file=sys.stderr)
        return 2

    if args.view == "json" or args.json:
        payload = {
            "schema": "hg_plot_cognition_investigator_v1",
            "plot_cognition_scope_id": scope.plot_cognition_scope_id,
            "manifest": scope.manifest(),
            "index": scope.index(),
            "timeline": scope.timeline(),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.view == "timeline":
        print(format_timeline(scope))
        return 0
    if args.view == "commit":
        if not args.target:
            print("commit view requires domain commit id target", file=sys.stderr)
            return 2
        print(format_commit_effects(scope, args.target))
        return 0
    if args.view == "integrity":
        print(format_integrity_gaps(scope))
        return 0
    if args.view == "layer_b":
        if not args.target:
            print("layer_b view requires batch id target", file=sys.stderr)
            return 2
        print(
            format_layer_b_chain(
                scope,
                batch_id=args.target,
                hg_session_id=args.session,
                evidence_root=args.evidence_root,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""List Holy Grail V2 human audit tags for a session."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from _repo_paths import AUDIT_TAGS_DIR, REPO_ROOT  # noqa: E402

from investigation._ni_forensics import ni_cli_handoff  # noqa: E402


def session_tags_dir(hg_session_id: str) -> Path:
    return AUDIT_TAGS_DIR / hg_session_id


def load_index(hg_session_id: str) -> dict | None:
    index_path = session_tags_dir(hg_session_id) / "index.json"
    if not index_path.is_file():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def load_tag(hg_session_id: str, tag_id: str) -> dict | None:
    tag_path = session_tags_dir(hg_session_id) / "tags" / f"{tag_id}.json"
    if not tag_path.is_file():
        return None
    return json.loads(tag_path.read_text(encoding="utf-8"))


def list_tags(hg_session_id: str) -> list[dict]:
    index = load_index(hg_session_id)
    if index is None:
        return []
    tags = []
    for tag_id in index.get("tag_ids") or []:
        tag = load_tag(hg_session_id, tag_id)
        if tag:
            tags.append(tag)
    tags.sort(key=lambda item: int(item.get("tag_index", 0)))
    return tags


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hg_session_id", help="Holy Grail session id")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a human summary",
    )
    parser.add_argument("--tag", help="Show one tag by tag_id")
    parser.add_argument(
        "--trace",
        action="store_true",
        help="With --tag: hand off to trace_ni_forensics.py tag view",
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="With --trace: re-resolve forensic_scope",
    )
    args = parser.parse_args()

    root = session_tags_dir(args.hg_session_id)
    if not root.is_dir():
        print(f"No audit tag directory: {root}", file=sys.stderr)
        return 1

    if args.tag:
        tag = load_tag(args.hg_session_id, args.tag)
        if tag is None:
            print(f"Tag not found: {args.tag}", file=sys.stderr)
            return 1
        if args.trace:
            cmd = ni_cli_handoff(args.hg_session_id, "tag", args.tag)
            if args.resolve:
                cmd += " --resolve"
            print(cmd)
            return 0
        if args.json:
            print(json.dumps(tag, indent=2, ensure_ascii=False))
            return 0
        anchor = tag.get("anchor") or {}
        scope = tag.get("forensic_scope") or {}
        print(f"tag_id: {tag.get('tag_id')}")
        print(f"anchor.entry_id: {anchor.get('entry_id')}")
        print(f"anchor.hg_round_id: {anchor.get('hg_round_id')}")
        print(f"anchor.domain_commit_id: {anchor.get('domain_commit_id')}")
        print(f"forensic_scope.resolution_status: {scope.get('resolution_status', 'n/a')}")
        print(
            f"ni_trace: python tools/investigation/trace_ni_forensics.py "
            f"{args.hg_session_id} tag {args.tag}"
        )
        return 0

    tags = list_tags(args.hg_session_id)

    if args.json:
        print(json.dumps({"hg_session_id": args.hg_session_id, "tags": tags}, indent=2, ensure_ascii=False))
        return 0

    print(f"repo: {REPO_ROOT}")
    print(f"session: {args.hg_session_id}")
    print(f"root: {root}")
    print(f"tag_count: {len(tags)}")
    for tag in tags:
        anchor = tag.get("anchor") or {}
        comment = tag.get("comment")
        comment_suffix = f' comment="{comment}"' if comment else ""
        print(
            "- "
            f"{tag.get('tag_id')} "
            f"index={tag.get('tag_index')} "
            f"entry_id={anchor.get('entry_id')} "
            f"speaker={anchor.get('speaker')} "
            f"role={anchor.get('transcript_role')} "
            f"round={anchor.get('hg_round_id')} "
            f"commit={anchor.get('domain_commit_id')}"
            f"{comment_suffix}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

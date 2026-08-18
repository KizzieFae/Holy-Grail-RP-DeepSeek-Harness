#!/usr/bin/env python3
"""Operator CLI for user callout review index and issue links (GitHub #125).

Run from ``autogen_rp/python`` (see AUDIT_DOCUMENTATION.md §7–8). Non-runtime; does
not start Streamlit. Callout *creation* remains in the Streamlit sidebar (Issue #55).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from legacy.v1_orchestration.bootstrap import ensure_v1_orchestration_paths

ensure_v1_orchestration_paths()

from user_callout_review_store import (  # noqa: E402
    UserCalloutReviewStoreError,
    dismiss_callout,
    find_raw_record,
    find_user_callouts_path_for_callout,
    get_issue_link_for_callout,
    list_unresolved,
    load_issue_links,
    issue_links_path,
    record_issue_promotion,
    rebuild_review_state,
    resolve_default_audit_base_dir,
)


def _add_base(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        help="rp_audits root (default: autogen_rp/python/rp_app/data/rp_audits)",
    )


def _parse_base(ns: argparse.Namespace) -> Path:
    return resolve_default_audit_base_dir(ns.base_dir)


def _validate_uuid(s: str) -> str:
    try:
        return str(UUID(s))
    except ValueError:
        print("error: --callout-id must be a valid UUID", file=sys.stderr)
        raise SystemExit(1) from None


def _cmd_list(ns: argparse.Namespace) -> int:
    base = _parse_base(ns)
    rows = list_unresolved(base_dir=base)
    if ns.json:
        out = [
            {
                "callout_id": cid,
                "review_row": row,
            }
            for cid, row in rows
        ]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    if not rows:
        print("No unresolved callouts (not dismissed, not promoted).")
        return 0
    for cid, row in rows:
        print(
            f"{cid}\t"
            f"session {row.get('audit_session_number')}\t"
            f"{row.get('created_at_utc', '')}\t"
            f"R{row.get('audit_round_number')}T{row.get('audit_turn_number')}\t"
            f"{row.get('session_path_hint', '')}"
        )
    return 0


def _cmd_show(ns: argparse.Namespace) -> int:
    base = _parse_base(ns)
    cid = _validate_uuid(ns.callout_id)
    raw = find_raw_record(base_dir=base, callout_id=cid)
    if raw is None:
        print(f"Callout {cid!r} not found in any session user_callouts_v1.json.", file=sys.stderr)
        return 1
    raw_path = find_user_callouts_path_for_callout(base_dir=base, callout_id=cid)
    rel = str(raw_path) if raw_path is not None else "unknown"
    link = get_issue_link_for_callout(base_dir=base, callout_id=cid)
    if ns.json:
        payload: dict[str, Any] = {
            "user_callouts_file": str(raw_path) if raw_path is not None else None,
            "raw_record": raw,
            "issue_link": link,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"user_callouts_v1 path: {rel}")
    print()
    print("raw_record (full):")
    print(json.dumps(raw, indent=2, ensure_ascii=False))
    print()
    if link:
        print("issue_link (promoted):")
        print(json.dumps(link, indent=2, ensure_ascii=False))
    else:
        print("issue_link: (none)")
    return 0


def _cmd_dismiss(ns: argparse.Namespace) -> int:
    base = _parse_base(ns)
    cid = _validate_uuid(ns.callout_id)
    try:
        dismiss_callout(base_dir=base, callout_id=cid)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    except (OSError, UserCalloutReviewStoreError) as e:
        print(e, file=sys.stderr)
        return 2
    print(f"Dismissed {cid!r} in review index.")
    return 0


def _cmd_promote(ns: argparse.Namespace) -> int:
    base = _parse_base(ns)
    cid = _validate_uuid(ns.callout_id)
    url = str(ns.issue_url or "").strip()
    if not url:
        print("--issue-url is required and must be non-empty.", file=sys.stderr)
        return 1
    try:
        record_issue_promotion(
            base_dir=base,
            callout_id=cid,
            issue_number=int(ns.issue_number),
            issue_url=url,
            replace=bool(getattr(ns, "replace", False)),
        )
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    except (OSError, UserCalloutReviewStoreError) as e:
        print(e, file=sys.stderr)
        return 2
    print(f"Recorded issue link for {cid!r}.")
    return 0


def _cmd_rebuild(ns: argparse.Namespace) -> int:
    base = _parse_base(ns)
    try:
        r = rebuild_review_state(base_dir=base)
    except (OSError, UserCalloutReviewStoreError) as e:
        print(e, file=sys.stderr)
        return 2
    if ns.json:
        print(
            json.dumps(
                {
                    "review_rows_written": r.review_rows_written,
                    "link_keys": r.link_keys,
                    "orphan_index_ids": r.orphan_index_ids,
                    "orphan_link_ids": r.orphan_link_ids,
                    "inconsistency_dismissed_with_link": r.inconsistency_dismissed_with_link,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    print(f"index rows: {r.review_rows_written}  issue link keys: {r.link_keys}")
    if r.orphan_index_ids:
        print("orphan index ids (not in raw):", ", ".join(r.orphan_index_ids))
    if r.orphan_link_ids:
        print("orphan link ids (no raw callout):", ", ".join(r.orphan_link_ids))
    if r.inconsistency_dismissed_with_link:
        print("cleared dismissed+link for:", ", ".join(r.inconsistency_dismissed_with_link))
    return 0


def _cmd_links(ns: argparse.Namespace) -> int:
    base = _parse_base(ns)
    try:
        ldata = load_issue_links(issue_links_path(base_dir=base))
    except UserCalloutReviewStoreError as e:
        print(e, file=sys.stderr)
        return 2
    links = ldata.get("links") or {}
    if ns.json:
        print(json.dumps(links, indent=2, ensure_ascii=False))
        return 0
    if not links:
        print("No issue links (no promoted callouts).")
        return 0
    for cid, obj in sorted(links.items(), key=lambda x: (x[1].get("issue_number", 0), x[0])):
        print(
            f"{cid}\t#{obj.get('issue_number')}\t{obj.get('issue_url', '')}\t{obj.get('linked_at_utc', '')}"
        )
    return 0


def main() -> int:
    root = argparse.ArgumentParser(
        description=__doc__,
    )
    sub = root.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List unresolved callouts (not promoted, not dismissed)")
    p_list.add_argument("--json", action="store_true", help="JSON output")
    _add_base(p_list)
    p_list.set_defaults(func=_cmd_list)

    p_show = sub.add_parser("show", help="Show full raw record and optional issue link")
    p_show.add_argument("--callout-id", required=True, help="User callout UUID")
    p_show.add_argument("--json", action="store_true", help="JSON output")
    _add_base(p_show)
    p_show.set_defaults(func=_cmd_show)

    p_dismiss = sub.add_parser("dismiss", help="Set review_disposition to dismissed (not if promoted)")
    p_dismiss.add_argument("--callout-id", required=True)
    _add_base(p_dismiss)
    p_dismiss.set_defaults(func=_cmd_dismiss)

    p_pro = sub.add_parser("promote", help="Record GitHub issue link for a callout")
    p_pro.add_argument("--callout-id", required=True)
    p_pro.add_argument("--issue-number", type=int, required=True)
    p_pro.add_argument("--issue-url", required=True)
    p_pro.add_argument(
        "--replace",
        action="store_true",
        help="Overwrite an existing issue link for this callout (reconciliation; default: reject duplicate)",
    )
    _add_base(p_pro)
    p_pro.set_defaults(func=_cmd_promote)

    p_reb = sub.add_parser("rebuild", help="Rebuild review index from raw + link map (maintenance)")
    p_reb.add_argument("--json", action="store_true", help="JSON report")
    _add_base(p_reb)
    p_reb.set_defaults(func=_cmd_rebuild)

    p_ln = sub.add_parser("links", help="List all promoted callout -> issue link entries")
    p_ln.add_argument("--json", action="store_true", help="JSON output")
    _add_base(p_ln)
    p_ln.set_defaults(func=_cmd_links)

    ns = root.parse_args()
    return int(ns.func(ns))


if __name__ == "__main__":
    raise SystemExit(main())

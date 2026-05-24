#!/usr/bin/env python3
"""Extract cohesion-slate matrix from audited session artifacts (#227)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from cohesion_slate_extract import extract_session, summarize_cohesion_rows  # noqa: E402
from emission_map_extract import write_csv, write_jsonl  # noqa: E402


def _resolve_session_dir(args: argparse.Namespace) -> Path:
    if args.session_dir:
        return Path(args.session_dir)
    if args.audit_session_number is not None:
        return _PY_ROOT / "rp_app" / "data" / "rp_audits" / f"session_{args.audit_session_number:03d}"
    raise SystemExit("Provide --session-dir or --audit-session-number")


def main() -> None:
    p = argparse.ArgumentParser(description="Extract cohesion slate matrix from audited sessions.")
    p.add_argument("--session-dir", type=Path)
    p.add_argument("--audit-session-number", type=int, metavar="NNN")
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out-jsonl", type=Path, required=True)
    p.add_argument("--out-csv", type=Path, default=None)
    p.add_argument("--summary-out", type=Path, default=None)
    args = p.parse_args()

    session_dir = _resolve_session_dir(args)
    if not session_dir.is_dir():
        raise SystemExit(f"Session directory not found: {session_dir}")
    if not args.manifest.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest}")

    manifest_data = json.loads(args.manifest.read_text(encoding="utf-8"))
    default_actor = str(manifest_data.get("probe_target_actor") or "").strip()
    if not default_actor:
        raise SystemExit("Manifest missing probe_target_actor")

    rows = extract_session(
        session_dir,
        probe_manifest_path=args.manifest,
        default_probe_actor=default_actor,
        audit_session_number=args.audit_session_number,
    )
    write_jsonl(rows, args.out_jsonl)
    if args.out_csv:
        write_csv(rows, args.out_csv)
    summary = summarize_cohesion_rows(rows)
    summary["session_dir"] = str(session_dir)
    summary["manifest"] = str(args.manifest)
    summary["archetype_id"] = manifest_data.get("archetype_id")
    summary["audit_session_number"] = args.audit_session_number
    summary["row_count"] = len(rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(f"wrote {len(rows)} rows -> {args.out_jsonl}", file=sys.stderr)


if __name__ == "__main__":
    main()

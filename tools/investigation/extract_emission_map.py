#!/usr/bin/env python3
"""Extract deterministic emission-map matrix from audited session artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _repo_paths import DATA_DIR, FIXTURES_DIR, INVESTIGATION_DIR, LEGACY_RP_APP, REPO_ROOT, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir

_PY_ROOT = REPO_ROOT
_RP_APP = LEGACY_RP_APP
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from emission_map_extract import (  # noqa: E402
    extract_session,
    summarize_rows,
    write_csv,
    write_jsonl,
)


def _default_manifest() -> Path:
    return FIXTURES_DIR / "issue240" / "i240_emission_probe_manifest_v1.json"


def _resolve_session_dir(args: argparse.Namespace) -> Path:
    if args.session_dir:
        return Path(args.session_dir)
    if args.audit_session_number is not None:
        return resolve_rp_audits_dir() / f"session_{args.audit_session_number:03d}"
    raise SystemExit("Provide --session-dir or --audit-session-number")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Extract emission_map_v1 matrix from audited character turn artifacts."
    )
    p.add_argument(
        "--session-dir",
        type=Path,
        help="Path to rp_audits/session_NNN directory",
    )
    p.add_argument(
        "--audit-session-number",
        type=int,
        metavar="NNN",
        help="Audit session number (resolves rp_app/data/rp_audits/session_NNN)",
    )
    p.add_argument(
        "--manifest",
        type=Path,
        default=_default_manifest(),
        help="Probe manifest JSON (default: data/issue240/i240_emission_probe_manifest_v1.json)",
    )
    p.add_argument(
        "--out-jsonl",
        type=Path,
        default=VALIDATION_RUNS_ARCHIVE / "emission_map_v1.jsonl",
        help="Output JSONL path",
    )
    p.add_argument(
        "--out-csv",
        type=Path,
        default=None,
        help="Optional CSV output path",
    )
    p.add_argument(
        "--summary-out",
        type=Path,
        default=None,
        help="Optional JSON summary path",
    )
    args = p.parse_args()

    session_dir = _resolve_session_dir(args)
    if not session_dir.is_dir():
        raise SystemExit(f"Session directory not found: {session_dir}")

    manifest = args.manifest if args.manifest.is_file() else None
    rows = extract_session(
        session_dir,
        probe_manifest_path=manifest,
        audit_session_number=args.audit_session_number,
    )
    write_jsonl(rows, args.out_jsonl)
    if args.out_csv:
        write_csv(rows, args.out_csv)
    summary = summarize_rows(rows)
    summary["session_dir"] = str(session_dir)
    summary["manifest"] = str(manifest) if manifest else None
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

#!/usr/bin/env python3
"""Offline fact-track / failure_classification over an existing audit session (GitHub #58).

Reads character ``*_full.json`` under ``--session-dir`` and a ``fact_spec.v1`` JSON file.
Prints one JSON object to stdout (deterministic; suitable for golden tests).
"""

from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE
import argparse
import json
import sys
from pathlib import Path

_PY_ROOT = REPO_ROOT
_RP_APP = LEGACY_RP_APP
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from audit_fact_tracking import analyze_fact_tracking  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--session-dir",
        type=Path,
        required=True,
        help="Audit session directory (e.g. .../rp_audits/session_NNN)",
    )
    p.add_argument(
        "--fact-spec",
        type=Path,
        required=True,
        help="JSON file with schema_version fact_spec.v1",
    )
    args = p.parse_args()
    session_dir = args.session_dir.resolve()
    if not session_dir.is_dir():
        print(f"not a directory: {session_dir}", file=sys.stderr)
        sys.exit(1)
    spec_path = args.fact_spec.resolve()
    if not spec_path.is_file():
        print(f"not a file: {spec_path}", file=sys.stderr)
        sys.exit(1)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"failed to read fact spec: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(spec, dict):
        print("fact spec must be a JSON object", file=sys.stderr)
        sys.exit(1)
    out = analyze_fact_tracking(session_dir, spec)
    print(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

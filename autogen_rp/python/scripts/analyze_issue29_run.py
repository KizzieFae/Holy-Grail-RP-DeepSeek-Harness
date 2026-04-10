#!/usr/bin/env python3
"""Analyze an audited session for Issue #29 machine lane (deterministic)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from issue29_investigation import analyze_issue29_session  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session-dir", type=Path, required=True)
    p.add_argument("--scenario-id", type=str, required=True)
    args = p.parse_args()
    out = analyze_issue29_session(args.session_dir, args.scenario_id)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

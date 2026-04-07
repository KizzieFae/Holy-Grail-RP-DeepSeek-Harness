#!/usr/bin/env python3
"""CLI: run Progression Stress Audit replay on an existing audit session + structured_eval."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo layout: scripts/ -> rp_app as sibling
_SCRIPT_DIR = Path(__file__).resolve().parent
_RP_APP = _SCRIPT_DIR.parent / "rp_app"
if _RP_APP.is_dir():
    sys.path.insert(0, str(_RP_APP))

from progression_stress_audit_replay import (  # noqa: E402
    run_progression_stress_audit_replay,
    write_replay_outputs,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--session-dir",
        type=Path,
        required=True,
        help="Audit session directory (e.g. rp_app/data/rp_audits/session_042)",
    )
    p.add_argument(
        "--structured-eval",
        type=Path,
        default=None,
        help="structured_eval JSON from --metrics-out (for sim_progression_metrics_events)",
    )
    p.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Captured stdout/stderr containing [beat_shift] lines",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: session-dir / progression_stress_replay)",
    )
    p.add_argument(
        "--ctk-consume-override",
        type=int,
        default=None,
        help="Override CTK index for beat-shift consume (optional)",
    )
    args = p.parse_args()
    out = args.out_dir or (args.session_dir / "progression_stress_replay")
    result = run_progression_stress_audit_replay(
        session_dir=args.session_dir,
        structured_eval_path=args.structured_eval,
        log_path=args.log,
        ctk_consume_override=args.ctk_consume_override,
    )
    turn_path, sum_path = write_replay_outputs(result, out)
    print(f"Wrote {turn_path}")
    print(f"Wrote {sum_path}")


if __name__ == "__main__":
    main()

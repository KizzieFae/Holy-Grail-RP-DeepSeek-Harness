#!/usr/bin/env python3
"""Compile manifest-driven authored sources into retrieval index JSON (schema v2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PY_ROOT = Path(__file__).resolve().parents[1]
_RP_APP = _PY_ROOT / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from authored_index_compile import compile_authored_index  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True, help="Path to manifest.json")
    p.add_argument("--output", type=Path, required=True, help="Output compiled index path")
    args = p.parse_args()
    stats = compile_authored_index(args.manifest.resolve(), args.output.resolve())
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read runs/arch_quality_r2/**/*.json and print run matrix + summaries."""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

_PY = Path(__file__).resolve().parents[1]
_ROOT = _PY / "runs" / "arch_quality_r2"


def load_metrics(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("metrics") or {}


def chain_key_str(summary: dict) -> str:
    counts = summary.get("attribution_chain_counts") or {}
    if not counts:
        return "{}"
    return "; ".join(f"{k}={v}" for k, v in sorted(counts.items()))


def main() -> None:
    if not _ROOT.is_dir():
        print("No", _ROOT)
        return
    for comp_dir in sorted(_ROOT.iterdir()):
        if not comp_dir.is_dir():
            continue
        print("###", comp_dir.name)
        rows: list[tuple] = []
        for p in sorted(comp_dir.glob("*.json")):
            m = load_metrics(p)
            sa = m.get("selection_attribution_summary") or {}
            rows.append(
                (
                    p.name,
                    m.get("arch_quality_variant"),
                    m.get("accepted_character_turns"),
                    m.get("progression_retries_triggered"),
                    m.get("failed_progression_attempts"),
                    sa.get("progression_override_applied_count"),
                    sa.get("hard_route_events"),
                    sa.get("fairness_rotation_count"),
                    chain_key_str(sa),
                )
            )
        for r in rows:
            print(" | ".join(str(x) for x in r))
        print()


if __name__ == "__main__":
    main()

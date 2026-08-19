"""Roll up Issue #242 topology manifests across baseline sessions."""
from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE
import argparse
import json
import sys
from pathlib import Path
from typing import Any

_RP_APP = REPO_ROOT  # patched M13.6 / "rp_app"
sys.path.insert(0, str(_RP_APP))

from prompt_topology_manifest import aggregate_topology_manifest_rows  # noqa: E402


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"manifest must be object: {path}")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Roll up TOPOLOGY_MANIFEST_*.json files")
    ap.add_argument(
        "--manifest-dir",
        required=True,
        help="Directory containing TOPOLOGY_MANIFEST_*.json files",
    )
    ap.add_argument("--out", required=True, help="Output rollup JSON path")
    args = ap.parse_args()

    manifest_dir = Path(args.manifest_dir)
    manifests = sorted(manifest_dir.glob("TOPOLOGY_MANIFEST_*.json"))
    if not manifests:
        print(f"No manifests found in {manifest_dir}", file=sys.stderr)
        return 1

    per_session: list[dict[str, Any]] = []
    all_topology_rows: list[dict[str, Any]] = []
    index_path = manifest_dir / "INDEX.json"
    index_rows: list[dict[str, Any]] = []
    if index_path.is_file():
        index_rows = json.loads(index_path.read_text(encoding="utf-8"))

    for mp in manifests:
        manifest = _load_manifest(mp)
        per_session.append(
            {
                "session_id": manifest.get("session_id"),
                "scenario_id": manifest.get("scenario_id"),
                "turn_count": manifest.get("turn_count"),
                "aggregate": manifest.get("aggregate"),
                "manifest_path": str(mp),
            }
        )
        session_id = str(manifest.get("session_id") or "")
        for row in index_rows:
            if str(row.get("session") or "") == session_id:
                topo = row.get("topology_manifest")
                if isinstance(topo, dict):
                    all_topology_rows.append(topo)

    rollup = {
        "schema_version": "issue242_topology_rollup_v1",
        "issue": 242,
        "session_count": len(per_session),
        "sessions": per_session,
        "aggregate_all_sessions": aggregate_topology_manifest_rows(all_topology_rows),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rollup, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote rollup for {len(manifests)} sessions to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

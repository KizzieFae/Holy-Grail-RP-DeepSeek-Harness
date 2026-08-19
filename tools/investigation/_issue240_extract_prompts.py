"""Extract character prompt metrics from #240 V1 matrix audit sessions."""
from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE
import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from _issue240_audit_classifier import classify_turn, _overlay_demands_proposals, _actor_aligned

import sys

_RP_APP = REPO_ROOT  # patched M13.6 / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from prompt_topology_manifest import (  # noqa: E402
    aggregate_topology_manifest_rows,
    extract_topology_manifest,
)

AUDITS = REPO_ROOT  # patched M13.6 / "rp_app" / "data" / "rp_audits"
SEMANTIC_HEADER = "FOR THIS BEAT — SEMANTIC SELF-REPORT"


def _system_prompt_text(data: dict[str, Any]) -> str:
    for msg in data.get("input_messages") or []:
        if msg.get("role") == "system":
            return str(msg.get("content") or "")
    return ""


def _structural_summary(data: dict[str, Any]) -> dict[str, Any]:
    sys_c = _system_prompt_text(data)
    out_rules_idx = sys_c.find("OUTPUT RULES:")
    trig_idx = sys_c.find("TRIGGER FOR THIS BEAT:")
    sem_idx = sys_c.find(SEMANTIC_HEADER)
    out_len = len(sys_c) - out_rules_idx if out_rules_idx >= 0 else None
    return {
        "system_chars": len(sys_c),
        "trigger_in_system_offset": trig_idx if trig_idx >= 0 else None,
        "trigger_in_system_pct": round(100 * trig_idx / len(sys_c), 1) if trig_idx >= 0 and sys_c else None,
        "semantic_self_report_offset": sem_idx if sem_idx >= 0 else None,
        "semantic_self_report_pct": round(100 * sem_idx / len(sys_c), 1) if sem_idx >= 0 and sys_c else None,
        "output_rules_offset": out_rules_idx if out_rules_idx >= 0 else None,
        "output_rules_chars": out_len,
        "output_rules_pct_from_end": round(100 * out_len / len(sys_c), 1) if out_len and sys_c else None,
        "has_v1_opening": "Act primarily as this character" in sys_c,
        "has_doctrine_phrase": "not compliance theater" in sys_c,
    }


def _topology_env() -> str | None:
    raw = os.environ.get("RP_ISSUE240_PROMPT_TOPOLOGY", "").strip()
    return raw or None


def _semantic_decision_label(data: dict[str, Any]) -> str:
    po = data.get("parsed_output") or {}
    if not isinstance(po, dict):
        return "invalid"
    ev = po.get("semantic_evaluation")
    if isinstance(ev, dict):
        decision = str(ev.get("decision") or "").strip()
        if decision in {"covered_change", "no_covered_change"}:
            return decision
    raw = str(data.get("raw_response") or "")
    if '"semantic_proposals": []' in raw or po.get("semantic_proposals") == []:
        return "empty_array"
    sp = po.get("semantic_proposals")
    if isinstance(sp, list) and sp:
        return "legacy_proposal_emit"
    return "omission"


def extract_session(
    session_dir: Path,
    out_dir: Path,
    *,
    emit_topology_manifest: bool = False,
    scenario_id: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    topology_rows: list[dict[str, Any]] = []
    for fp in sorted(session_dir.rglob("*_full.json")):
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("bot_type") != "character":
            continue
        primary, secondary = classify_turn(data)
        summary = _structural_summary(data)
        sys_c = _system_prompt_text(data)
        topology = extract_topology_manifest(sys_c)
        row = {
            "session": session_dir.name,
            "file": fp.name,
            "turn": data.get("turn_number"),
            "bot": data.get("bot_name"),
            "overlay_targeted": _overlay_demands_proposals(data),
            "actor_aligned": _actor_aligned(data),
            "classification": primary,
            "secondary": secondary,
            "semantic_decision": _semantic_decision_label(data),
            "topology_env": _topology_env(),
            "topology": topology.get("topology_inferred"),
            **summary,
            "topology_manifest": topology,
        }
        rows.append(row)
        topology_rows.append(topology)
        slug = f"{session_dir.name}_turn{int(data.get('turn_number') or 0):02d}_{data.get('bot_name', 'unknown')}"
        (out_dir / f"{slug}.json").write_text(json.dumps(row, indent=2), encoding="utf-8")

    if emit_topology_manifest and rows:
        manifest = {
            "schema_version": "issue242_topology_manifest_v1",
            "issue": 242,
            "capture_phase": "pre_consolidation_baseline",
            "capture_source": "audit_character_full_json.input_messages[role=system]",
            "topology_env": _topology_env(),
            "session_id": session_dir.name,
            "scenario_id": scenario_id,
            "turn_count": len(rows),
            "aggregate": aggregate_topology_manifest_rows(topology_rows),
            "turns": [
                {
                    "turn": r.get("turn"),
                    "bot": r.get("bot"),
                    "semantic_decision": r.get("semantic_decision"),
                    "classification": r.get("classification"),
                    "topology_fingerprint": (r.get("topology_manifest") or {}).get(
                        "topology_fingerprint"
                    ),
                    "profile_match": (r.get("topology_manifest") or {}).get("profile_match"),
                    "profile_deviations": (r.get("topology_manifest") or {}).get(
                        "profile_deviations"
                    ),
                }
                for r in rows
            ],
        }
        manifest_path = out_dir / f"TOPOLOGY_MANIFEST_{session_dir.name}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--out-dir", default=str(DATA_DIR / "issue240_runs/prompt_extractions"))
    ap.add_argument(
        "--topology-manifest",
        action="store_true",
        help="Emit TOPOLOGY_MANIFEST_<session>.json per session",
    )
    ap.add_argument(
        "--scenario-id",
        default="",
        help="Optional scenario id recorded on topology manifests",
    )
    args = ap.parse_args()
    out_dir = REPO_ROOT  # patched M13.6 / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    scenario_id = str(args.scenario_id or "").strip() or None
    for s in args.sessions:
        sess_dir = AUDITS / (s if s.startswith("session_") else f"session_{s}")
        if sess_dir.is_dir():
            all_rows.extend(
                extract_session(
                    sess_dir,
                    out_dir,
                    emit_topology_manifest=args.topology_manifest,
                    scenario_id=scenario_id,
                )
            )
    index = out_dir / "INDEX.json"
    index.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_rows)} rows to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

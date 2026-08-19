"""Build Issue #240 final viability adjudication corpus from corrected scorer output."""
from __future__ import annotations

from _repo_paths import DATA_DIR, INVESTIGATION_DIR, REPO_ROOT, VALIDATION_RUNS_ARCHIVE
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _issue240_corrected_scorer import analyze_session  # noqa: E402
from _issue240_audit_classifier import _proposals  # noqa: E402

KEEP_CATEGORIES = {
    "true semantic miss",
    "ambiguous ontology threshold",
}


def _load_audit_row(session_dir: Path, turn: int, bot: str) -> dict | None:
    for fp in session_dir.rglob("*_full.json"):
        if fp.name.endswith("_validation_full.json"):
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        if data.get("bot_type") != "character":
            continue
        if data.get("turn_number") != turn:
            continue
        b = str(data.get("bot_name") or "")
        if bot.replace("_", " ").lower() not in b.replace("_", " ").lower():
            continue
        po = data.get("parsed_output") or {}
        ev = po.get("semantic_evaluation") if isinstance(po.get("semantic_evaluation"), dict) else {}
        return {
            "beats": po.get("beats") or [],
            "beats_text": __import__("_issue240_audit_classifier", fromlist=["_beats_text"])._beats_text(data),
            "semantic_evaluation": ev,
            "trigger_context": str(data.get("effective_user_trigger") or "")[:500],
            "proposals": _proposals(data),
        }
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(DATA_DIR / "issue240/final_viability_matrix_v1.json"))
    ap.add_argument("--out", default=str(DATA_DIR / "issue240/adjudication_corpus_final_viability_v1.json"))
    args = ap.parse_args()
    root = REPO_ROOT  # patched M13.6
    manifest = json.loads((root / args.manifest).read_text(encoding="utf-8"))
    audits = root / "rp_app" / "data" / "rp_audits"
    cases: list[dict] = []
    for run in manifest.get("runs", []):
        sid = run.get("session")
        if not sid:
            continue
        must_remain = run.get("scenario") == "audit_i225_willow_must_remain_v2_offstage_cycles"
        analysis = analyze_session(audits / sid, must_remain=must_remain)
        for row in analysis["rows"]:
            if row["corrected_category"] not in KEEP_CATEGORIES:
                continue
            audit = _load_audit_row(audits / sid, int(row["turn"]), str(row["bot"]))
            case_id = f"{sid.replace('session_', '')}_t{row['turn']}_{str(row['bot']).lower().replace(' ', '_')}"
            cases.append(
                {
                    "case_id": case_id,
                    "session_id": sid,
                    "turn_index": row["turn"],
                    "scenario_id": run.get("scenario"),
                    "matrix_id": run.get("matrix_id"),
                    "rep": run.get("rep"),
                    "actor": row["bot"],
                    "topology": "v1_next7",
                    "overlay_applied": row["overlay_applied"],
                    "semantic_decision": row["semantic_decision"],
                    "proposals_emitted": row["proposals"],
                    "corrected_category": row["corrected_category"],
                    "corrected_rationale": row["corrected_rationale"],
                    "legal_alternatives": row["legal_alternatives"],
                    "boundary_signals": row["boundary_signals"],
                    "beats_text": audit["beats_text"] if audit else row["beats_snip"],
                    "trigger_context": audit["trigger_context"] if audit else "",
                    "semantic_evaluation": audit["semantic_evaluation"] if audit else {},
                }
            )
    corpus = {
        "schema_version": "issue240_final_viability_corpus_v1",
        "purpose": "evaluation_only — surviving misses and ambiguities only",
        "topology": "v1_next7",
        "case_count": len(cases),
        "cases": cases,
    }
    out_path = root / args.out
    out_path.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

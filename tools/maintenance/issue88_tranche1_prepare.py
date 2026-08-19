#!/usr/bin/env python3
"""Issue #88 Tranche 1 prep: registry snapshot + allow-list (read-only on rp_audits except no writes there).

Writes JSON artifacts under tools/maintenance/ only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from _repo_paths import MAINTENANCE_DIR, REPO_ROOT, resolve_rp_audits_dir

RP_AUDITS = resolve_rp_audits_dir()
TOOLS = MAINTENANCE_DIR

SCENARIOS = [
    "arrival_setup",
    "emotional_loop_2char",
    "conflict_3char",
    "strong_user_steer",
    "passive_observer",
    "long_session",
    "recovery_derail",
    "memory_public_propagation",
    "memory_private_directed",
    "memory_duplicate_retry",
    "memory_fallback_director",
    "memory_long_session",
    "memory_forced_speaker",
    "willow_dorm_binding_stress",
    "arkham_multi_character_stress",
    "arkham_multi_character_stress_long",
    "headless_template_retrieval_smoke",
    "parity_opening_trigger_smoke",
    "operational_baseline_3char_cafeteria",
]

ON_SCENARIOS = frozenset(
    {"headless_template_retrieval_smoke", "operational_baseline_3char_cafeteria"}
)


def session_num(name: str) -> int:
    m = re.match(r"session_(\d+)", name, re.I)
    return int(m.group(1)) if m else -1


def load_referenced_sessions() -> set[int]:
    out: set[int] = set()
    try:
        r = subprocess.run(
            ["git", "grep", "-o", "-E", r"session_[0-9]+", "--", "."],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=240,
        )
        if r.stdout:
            for line in r.stdout.splitlines():
                m = re.search(r"session_(\d+)", line)
                if m:
                    out.add(int(m.group(1)))
    except (OSError, subprocess.TimeoutExpired):
        pass
    return out


def is_narrator_full(p: Path) -> bool:
    return "_narrator_" in p.name and p.name.endswith("_full.json")


def is_director_full(p: Path) -> bool:
    return "_director_" in p.name and p.name.endswith("_full.json")


def character_fulls(session_dir: Path) -> list[Path]:
    out: list[Path] = []
    for p in session_dir.rglob("*_full.json"):
        if not p.is_file():
            continue
        if is_narrator_full(p) or is_director_full(p):
            continue
        out.append(p)
    return out


def narrator_fulls(session_dir: Path) -> list[Path]:
    return [p for p in session_dir.rglob("*_full.json") if p.is_file() and is_narrator_full(p)]


def narrator_meaningful(session_dir: Path) -> bool:
    """At least one narrator *_full.json parses as JSON object with non-trivial size."""
    for p in narrator_fulls(session_dir):
        try:
            raw = p.read_text(encoding="utf-8")
            if len(raw.strip()) < 20:
                continue
            o = json.loads(raw)
            if isinstance(o, dict) and len(o) > 0:
                return True
        except (OSError, json.JSONDecodeError):
            continue
    return False


def audit_summary_valid(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return False
        o = json.loads(raw)
        return isinstance(o, dict) and len(o) > 0
    except (OSError, json.JSONDecodeError, UnicodeError):
        return False


def load_rows() -> list[dict]:
    rows: list[dict] = []
    for d in sorted(RP_AUDITS.iterdir(), key=lambda p: p.name):
        if not d.is_dir() or not d.name.startswith("session_"):
            continue
        ap = d / "_audit_summary.json"
        if not ap.is_file():
            rows.append(
                {
                    "session_folder": d.name,
                    "session_number": session_num(d.name),
                    "session_owner": None,
                    "retrieval_mode": None,
                    "has_79_summary": False,
                    "summary_valid": False,
                }
            )
            continue
        try:
            summ = json.loads(ap.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            rows.append(
                {
                    "session_folder": d.name,
                    "session_number": session_num(d.name),
                    "session_owner": None,
                    "retrieval_mode": None,
                    "has_79_summary": False,
                    "summary_valid": False,
                }
            )
            continue
        if not isinstance(summ, dict) or not summ:
            rows.append(
                {
                    "session_folder": d.name,
                    "session_number": session_num(d.name),
                    "session_owner": None,
                    "retrieval_mode": None,
                    "has_79_summary": False,
                    "summary_valid": False,
                }
            )
            continue
        owner = summ.get("session_owner")
        if not isinstance(owner, str) or not owner.strip():
            owner = None
        rs = summ.get("retrieval_session")
        mode: str | None = None
        if isinstance(rs, dict):
            m = rs.get("retrieval_mode")
            if isinstance(m, str) and m.lower() in ("on", "off"):
                mode = m.lower()
        cos = summ.get("continuity_observability_summary_v1")
        post79 = isinstance(cos, dict) and bool(cos)
        rows.append(
            {
                "session_folder": d.name,
                "session_number": session_num(d.name),
                "session_owner": owner,
                "retrieval_mode": mode,
                "has_79_summary": post79,
                "summary_valid": True,
            }
        )
    return rows


def build_registry(rows: list[dict], refs: set[int]) -> dict:
    by_owner: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("session_owner"):
            by_owner[r["session_owner"]].append(r)

    def pick(cands: list[dict]) -> dict | None:
        if not cands:
            return None
        scored = []
        for c in cands:
            ref = 1 if c["session_number"] in refs else 0
            gen = c.get("generated_at") if "generated_at" in c else ""
            scored.append((ref, gen, c["session_number"], c))
        scored.sort(key=lambda x: (-x[0], x[1], -x[2]))
        return scored[0][3]

    out_rows = []
    protected_sessions: set[int] = set()

    for sid in SCENARIOS:
        pool = by_owner.get(sid, [])
        off_pool = [c for c in pool if c.get("retrieval_mode") == "off"]
        on_pool = [c for c in pool if c.get("retrieval_mode") == "on"]
        post_pool = [c for c in pool if c.get("has_79_summary")]

        off_p = pick(off_pool) if off_pool else None
        on_p = pick(on_pool) if on_pool else None
        post_p = pick(post_pool) if post_pool else None

        if sid in ON_SCENARIOS:
            on_path = on_p["session_folder"] if on_p else None
        else:
            on_path = None
        off_path = off_p["session_folder"] if off_p else None
        post_path = post_p["session_folder"] if post_p else None

        for p in (off_p, on_p, post_p):
            if p is not None:
                protected_sessions.add(p["session_number"])

        out_rows.append(
            {
                "scenario_id": sid,
                "OFF_session": off_path,
                "ON_session": on_path,
                "post_contract_session": post_path,
            }
        )

    return {
        "schema": "issue88_baseline_registry_snapshot_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_relative_root": "data/rp_audits",
        "scenarios": out_rows,
        "protected_session_numbers_union": sorted(protected_sessions),
    }


def sole_slot_protections(rows: list[dict]) -> set[int]:
    """Sessions that are the only candidate for a scenario slot."""
    by_owner: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if not r.get("session_owner"):
            continue
        by_owner[r["session_owner"]].append(r)

    protect: set[int] = set()
    for sid in SCENARIOS:
        pool = by_owner.get(sid, [])
        off = [c for c in pool if c.get("retrieval_mode") == "off"]
        post = [c for c in pool if c.get("has_79_summary")]
        on = [c for c in pool if c.get("retrieval_mode") == "on"]
        if len(off) == 1:
            protect.add(off[0]["session_number"])
        if len(post) == 1:
            protect.add(post[0]["session_number"])
        if sid in ON_SCENARIOS and len(on) == 1:
            protect.add(on[0]["session_number"])
    return protect


def tranche1_structural(session_dir: Path) -> tuple[bool, list[str]]:
    """Returns (eligible, reason_codes)."""
    reasons: list[str] = []
    ap = session_dir / "_audit_summary.json"
    if audit_summary_valid(ap):
        return False, ["valid_audit_summary_present"]

    if not ap.is_file():
        reasons.append("missing_audit_summary")
    else:
        reasons.append("invalid_or_empty_audit_summary")

    if character_fulls(session_dir):
        return False, reasons + ["has_character_full_json"]

    if narrator_meaningful(session_dir):
        return False, reasons + ["has_meaningful_narrator_audit"]

    reasons.append("no_usable_audit_signal")
    return True, reasons


def main() -> int:
    refs = load_referenced_sessions()
    rows = load_rows()
    # attach generated_at for pick — need from file for rows with valid summary
    for r in rows:
        if not r.get("summary_valid"):
            r["generated_at"] = None
            continue
        p = RP_AUDITS / r["session_folder"] / "_audit_summary.json"
        try:
            summ = json.loads(p.read_text(encoding="utf-8"))
            r["generated_at"] = summ.get("generated_at") if isinstance(summ, dict) else None
        except (OSError, json.JSONDecodeError):
            r["generated_at"] = None

    snapshot = build_registry(rows, refs)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    snap_path = TOOLS / f"issue88_baseline_registry_snapshot_{ts}.json"
    TOOLS.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {snap_path}")

    protected_registry = set(snapshot["protected_session_numbers_union"])
    sole = sole_slot_protections(rows)

    candidates: list[dict] = []
    for d in sorted(RP_AUDITS.iterdir(), key=lambda p: p.name):
        if not d.is_dir() or not d.name.startswith("session_"):
            continue
        n = session_num(d.name)
        ok, reasons = tranche1_structural(d)
        if not ok:
            continue
        candidates.append(
            {
                "session_id": d.name,
                "session_number": n,
                "repo_relative_path": f"data/rp_audits/{d.name}",
                "structural_reasons": reasons,
            }
        )

    allow: list[dict] = []
    for c in candidates:
        n = c["session_number"]
        ref = n in refs
        in_reg = n in protected_registry
        sole_p = n in sole
        excluded = ref or in_reg or sole_p
        allow.append(
            {
                **c,
                "verification": {
                    "referenced_in_tracked_repo_git_grep": ref,
                    "in_baseline_registry_snapshot": in_reg,
                    "sole_slot_protection": sole_p,
                    "allow_delete": not excluded,
                },
            }
        )

    final = [x for x in allow if x["verification"]["allow_delete"]]

    allow_path = TOOLS / f"issue88_tranche1_allowlist_{ts}.json"
    allow_path.write_text(
        json.dumps(
            {
                "schema": "issue88_tranche1_allowlist_v1",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "registry_snapshot_file": str(snap_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "reference_method": "git grep -o -E session_[0-9]+ on tracked files (repo root)",
                "structural_criteria": {
                    "audit_summary": "missing OR invalid/empty",
                    "and": [
                        "no character *_full.json (excl narrator/director)",
                        "no meaningful narrator *_full.json (parseable non-empty JSON object)",
                    ],
                },
                "counts": {
                    "session_dirs_total": len(
                        [p for p in RP_AUDITS.iterdir() if p.is_dir() and p.name.startswith("session_")]
                    ),
                    "structural_candidates": len(candidates),
                    "after_baseline_reference_sole_filters": len(final),
                },
                "candidates_structural_only": candidates,
                "allow_list": final,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {allow_path}")
    print(json.dumps(allow_path.read_text(encoding="utf-8")[:500]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

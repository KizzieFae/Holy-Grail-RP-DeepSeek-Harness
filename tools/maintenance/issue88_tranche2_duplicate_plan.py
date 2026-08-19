#!/usr/bin/env python3
"""Issue #88 Tranche 2: duplicate equivalence classes + keep/delete plan (read-only rp_audits).

Writes JSON under tools/maintenance/. Does not delete or modify rp_audits/.
"""
from __future__ import annotations

import hashlib
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


def canonical_json_blob(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def intent_fingerprint(summ: dict) -> str:
    """Structured-only intent class; missing blocks => separate fingerprints."""
    manifest = summ.get("manifest")
    st = summ.get("scene_template")
    ov = summ.get("overview")
    blob: dict = {}
    if isinstance(manifest, dict):
        blob["manifest"] = manifest
    else:
        blob["manifest"] = None
    if isinstance(st, dict):
        blob["scene_template"] = st
    else:
        blob["scene_template"] = None
    if isinstance(ov, dict):
        blob["overview"] = {
            "total_rounds": ov.get("total_rounds"),
            "total_turns": ov.get("total_turns"),
        }
    else:
        blob["overview"] = None
    s = canonical_json_blob(blob)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]


def retrieval_mode(summ: dict) -> str:
    rs = summ.get("retrieval_session")
    if not isinstance(rs, dict):
        return "unknown"
    m = rs.get("retrieval_mode")
    if isinstance(m, str) and m.lower() in ("on", "off"):
        return m.lower()
    return "unknown"


def load_snapshot() -> tuple[dict, set[int]]:
    snaps = sorted(TOOLS.glob("issue88_baseline_registry_snapshot_*.json"), reverse=True)
    if not snaps:
        raise SystemExit("No issue88_baseline_registry_snapshot_*.json in tools/")
    data = json.loads(snaps[0].read_text(encoding="utf-8"))
    protected = set(data.get("protected_session_numbers_union") or [])
    return data, protected


def sole_slot_protections(rows: list[dict]) -> set[int]:
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


def parse_iso(ts: str | None) -> float:
    if not ts or not isinstance(ts, str):
        return 0.0
    try:
        t = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(t).timestamp()
    except ValueError:
        return 0.0


def keep_sort_key(
    sn: int,
    summ: dict,
    *,
    registry: set[int],
    refs: set[int],
) -> tuple:
    has79 = isinstance(summ.get("continuity_observability_summary_v1"), dict) and bool(
        summ.get("continuity_observability_summary_v1")
    )
    gen = parse_iso(summ.get("generated_at") if isinstance(summ.get("generated_at"), str) else None)
    return (
        0 if sn in registry else 1,
        0 if sn in refs else 1,
        0 if has79 else 1,
        -gen,
        -sn,
    )


def main() -> int:
    refs = load_referenced_sessions()
    snap, registry = load_snapshot()
    snap_path = sorted(TOOLS.glob("issue88_baseline_registry_snapshot_*.json"), reverse=True)[0]

    rows: list[dict] = []
    sessions_data: dict[int, dict] = {}
    sn_to_folder: dict[int, str] = {}

    for d in sorted(RP_AUDITS.iterdir(), key=lambda p: p.name):
        if not d.is_dir() or not d.name.startswith("session_"):
            continue
        ap = d / "_audit_summary.json"
        if not ap.is_file():
            continue
        try:
            summ = json.loads(ap.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            continue
        if not isinstance(summ, dict) or not summ:
            continue
        owner = summ.get("session_owner")
        if not isinstance(owner, str) or not owner.strip():
            continue
        sn = session_num(d.name)
        mode = retrieval_mode(summ)
        cos = summ.get("continuity_observability_summary_v1")
        has79 = isinstance(cos, dict) and bool(cos)
        ifp = intent_fingerprint(summ)
        rows.append(
            {
                "session_folder": d.name,
                "session_number": sn,
                "session_owner": owner.strip(),
                "retrieval_mode": mode,
                "has_79_summary": has79,
                "intent_fingerprint": ifp,
            }
        )
        sessions_data[sn] = summ
        sn_to_folder[sn] = d.name

    sole = sole_slot_protections(rows)

    # Group: (owner, mode, intent_fp) — unknown owner sessions skipped (none)
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for r in rows:
        key = (r["session_owner"], r["retrieval_mode"], r["intent_fingerprint"])
        groups[key].append(r["session_number"])

    classes_out: list[dict] = []
    ambiguous: list[dict] = []
    total_delete_candidates = 0

    for key, sns in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        owner, mode, ifp = key
        sns_sorted = sorted(set(sns))
        if len(sns_sorted) < 2:
            continue

        class_id = f"{owner}|{mode}|{ifp}"

        # Sort sessions for keep: best first
        ranked = sorted(
            sns_sorted,
            key=lambda sn: keep_sort_key(
                sn, sessions_data[sn], registry=registry, refs=refs
            ),
        )
        keep = ranked[0]
        delete_cands = ranked[1:]

        keep_reason_parts = []
        if keep in registry:
            keep_reason_parts.append("baseline_registry_union")
        if keep in refs:
            keep_reason_parts.append("referenced_git_grep")
        if isinstance(
            sessions_data[keep].get("continuity_observability_summary_v1"), dict
        ) and bool(sessions_data[keep].get("continuity_observability_summary_v1")):
            keep_reason_parts.append("has_continuity_observability_summary_v1")
        keep_reason_parts.append(f"generated_at={sessions_data[keep].get('generated_at')}")
        keep_reason_parts.append(f"session_number={keep}")

        delete_details: list[dict] = []
        for dc in delete_cands:
            in_reg = dc in registry
            sole_p = dc in sole
            ref_p = dc in refs
            exclude = False
            reasons: list[str] = []
            if in_reg:
                exclude = True
                reasons.append("EXCLUDE: in_baseline_registry_snapshot")
            if sole_p:
                exclude = True
                reasons.append("EXCLUDE: sole_slot_protection")
            if ref_p:
                exclude = True
                reasons.append("EXCLUDE: referenced_tracked_repo_git_grep")
            if not exclude:
                reasons.append(
                    "pending: GitHub Issues/PR search required before deletion (not automated)"
                )
            delete_details.append(
                {
                    "session_number": dc,
                    "session_folder": sn_to_folder.get(dc, f"session_{dc}"),
                    "in_baseline_registry_snapshot": in_reg,
                    "sole_slot_protection": sole_p,
                    "referenced_tracked_repo": ref_p,
                    "exclude_from_delete_list": exclude,
                    "notes": reasons,
                }
            )

        effective_deletes = [d for d in delete_details if not d["exclude_from_delete_list"]]
        total_delete_candidates += len(effective_deletes)

        classes_out.append(
            {
                "class_id": class_id,
                "session_owner": owner,
                "retrieval_mode": mode,
                "intent_fingerprint": ifp,
                "matching_sessions": [sn_to_folder.get(n, f"session_{n}") for n in sns_sorted],
                "keep_session": sn_to_folder.get(keep, f"session_{keep}"),
                "keep_reason": "; ".join(keep_reason_parts),
                "delete_candidates": [sn_to_folder.get(n, f"session_{n}") for n in delete_cands],
                "delete_candidate_details": delete_details,
                "effective_delete_count_after_protection_filters": len(effective_deletes),
            }
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out_path = TOOLS / f"issue88_tranche2_duplicate_plan_{ts}.json"
    artifact = {
        "schema": "issue88_tranche2_duplicate_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_snapshot_source": str(snap_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "reference_method_tracked_repo": "git grep -o -E session_[0-9]+",
        "intent_fingerprint_method": "sha256[:24] of canonical_json(manifest, scene_template, overview totals)",
        "keep_order": [
            "baseline_registry_entry (protected_session_numbers_union)",
            "referenced session (git grep)",
            "continuity_observability_summary_v1 present",
            "newest generated_at",
            "highest session_number",
        ],
        "counts": {
            "equivalence_classes_size_ge_2": len(classes_out),
            "total_delete_candidates_before_manual_github_search": total_delete_candidates,
        },
        "ambiguous_classes_excluded": ambiguous,
        "equivalence_classes": classes_out,
    }
    out_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"classes={len(classes_out)} effective_deletes={total_delete_candidates}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

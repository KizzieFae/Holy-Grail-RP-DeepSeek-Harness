"""Check legacy autogen_rp/python/data vs canonical HG data (M14.2).

Default: dry-run report only. Use --migrate for a final idempotent copy of any
still-empty canonical categories (never deletes legacy source).

Exit 0 when compatibility retirement is safe (all legacy session ids present in
canonical; no legacy-only required data except historical rp_audits).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "v2") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "v2"))

from domain.paths import holy_grail_data_dir  # noqa: E402

MIGRATION_MARKER_NAME = ".hg_data_migration_v1.json"
MIGRATION_VERSION = 1
LEGACY_DATA_DIR = REPO_ROOT / "autogen_rp" / "python" / "data"

MIGRATION_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("characters", "autogen_characters"),
    ("scene_templates", "scene_templates"),
    ("retrieval", "retrieval"),
    ("fixtures/evaluation", "evaluation"),
    ("fixtures/issue227", "issue227"),
    ("fixtures/issue240", "issue240"),
    ("fixtures/issue29_investigation_schedules", "issue29_investigation_schedules"),
    ("fixtures/progression_simulation_scenarios", "progression_simulation_scenarios"),
    ("sessions", "sessions"),
)

LEGACY_ONLY_CATEGORIES = (
    ("rp_audits", "rp_audits"),
    ("_cross_scope_memory", "_cross_scope_memory"),
    ("_scope_knowledge", "_scope_knowledge"),
)


def legacy_data_dir() -> Path:
    return LEGACY_DATA_DIR


def _has_entries(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    try:
        return any(path.iterdir())
    except OSError:
        return False


def _copy_tree(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and _has_entries(dst):
        for item in src.rglob("*"):
            if item.is_dir():
                continue
            rel = item.relative_to(src)
            target = dst / rel
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def run_data_migration(*, canonical: Path | None = None) -> dict[str, Any]:
    """Final maintenance migration into canonical ``data/`` (idempotent)."""
    canonical = canonical or holy_grail_data_dir()
    legacy = legacy_data_dir()
    marker = canonical / MIGRATION_MARKER_NAME

    if marker.exists():
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
            if int(payload.get("version", 0)) >= MIGRATION_VERSION:
                return payload
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    canonical.mkdir(parents=True, exist_ok=True)
    migrated: list[str] = []
    skipped: list[str] = []

    for canonical_rel, legacy_rel in MIGRATION_CATEGORIES:
        src = legacy / legacy_rel
        dst = canonical / canonical_rel
        if not _has_entries(src):
            skipped.append(canonical_rel)
            continue
        if _has_entries(dst):
            skipped.append(canonical_rel)
            continue
        _copy_tree(src, dst)
        migrated.append(canonical_rel)

    payload = {
        "version": MIGRATION_VERSION,
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_root": str(canonical),
        "legacy_root": str(legacy),
        "migrated_categories": migrated,
        "skipped_categories": skipped,
    }
    marker.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files_under(base: Path) -> dict[str, Path]:
    if not base.exists():
        return {}
    return {
        str(p.relative_to(base)).replace("\\", "/"): p
        for p in base.rglob("*")
        if p.is_file()
    }


def _session_ids(sessions_dir: Path) -> set[str]:
    if not sessions_dir.exists():
        return set()
    ids: set[str] = set()
    for pattern in ("hg-session-*.json", "session_*.json"):
        for p in sessions_dir.glob(pattern):
            ids.add(p.stem)
    return ids


def _compare_pair(legacy_rel: str, canonical_rel: str, *, legacy: Path, canonical: Path) -> dict:
    leg_base = legacy / legacy_rel
    can_base = canonical / canonical_rel
    leg_files = _files_under(leg_base)
    can_files = _files_under(can_base)
    leg_only = sorted(set(leg_files) - set(can_files))
    can_only = sorted(set(can_files) - set(leg_files))
    mismatches = [
        rel
        for rel in set(leg_files) & set(can_files)
        if _sha256(leg_files[rel]) != _sha256(can_files[rel])
    ]
    return {
        "legacy_rel": legacy_rel,
        "canonical_rel": canonical_rel,
        "legacy_count": len(leg_files),
        "canonical_count": len(can_files),
        "legacy_only_count": len(leg_only),
        "canonical_only_count": len(can_only),
        "hash_mismatch_count": len(mismatches),
        "legacy_only_sample": leg_only[:5],
        "hash_mismatch_sample": sorted(mismatches)[:5],
    }


def build_report(*, canonical: Path | None = None, legacy: Path | None = None) -> dict:
    canonical = canonical or holy_grail_data_dir()
    legacy = legacy or legacy_data_dir()
    marker_path = canonical / MIGRATION_MARKER_NAME
    marker = None
    if marker_path.is_file():
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            marker = {"error": "unreadable marker"}

    categories = []
    blockers: list[str] = []
    notes: list[str] = []

    for canonical_rel, legacy_rel in MIGRATION_CATEGORIES:
        row = _compare_pair(legacy_rel, canonical_rel, legacy=legacy, canonical=canonical)
        categories.append(row)
        if row["legacy_only_count"]:
            blockers.append(
                f"{canonical_rel}: {row['legacy_only_count']} legacy-only file(s)"
            )
        for rel in row["hash_mismatch_sample"]:
            if rel == "_session_index.json" and row["canonical_count"] >= row["legacy_count"]:
                notes.append(
                    f"{canonical_rel}: _session_index.json differs (canonical index newer)"
                )
            elif rel != "_session_index.json":
                blockers.append(f"{canonical_rel}: hash mismatch on {rel}")

    for legacy_rel, canonical_rel in LEGACY_ONLY_CATEGORIES:
        row = _compare_pair(legacy_rel, canonical_rel, legacy=legacy, canonical=canonical)
        row["note"] = "not auto-migrated by M13.1"
        categories.append(row)
        if row["legacy_only_count"] and legacy_rel in ("_cross_scope_memory", "_scope_knowledge"):
            blockers.append(
                f"{legacy_rel}: {row['legacy_only_count']} legacy-only file(s)"
            )
        if row["legacy_only_count"] and legacy_rel == "rp_audits":
            notes.append(
                f"rp_audits: {row['legacy_only_count']} legacy-only audit files (historical)"
            )

    leg_sess = _session_ids(legacy / "sessions")
    can_sess = _session_ids(canonical / "sessions")
    missing_sessions = sorted(leg_sess - can_sess)

    if missing_sessions:
        blockers.append(
            f"sessions: {len(missing_sessions)} legacy session id(s) absent from canonical"
        )

    safe = not blockers and not missing_sessions

    return {
        "canonical_root": str(canonical),
        "legacy_root": str(legacy),
        "legacy_exists": legacy.is_dir(),
        "marker": marker,
        "categories": categories,
        "sessions": {
            "legacy_ids": len(leg_sess),
            "canonical_ids": len(can_sess),
            "legacy_missing_in_canonical": len(missing_sessions),
            "legacy_missing_sample": missing_sessions[:10],
            "canonical_only": len(can_sess - leg_sess),
        },
        "blockers": blockers,
        "notes": notes,
        "compatibility_retirement_safe": safe,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Print migration status (default)")
    parser.add_argument("--migrate", action="store_true", help="Run final idempotent migration")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args(argv)
    if not args.check and not args.migrate:
        args.check = True

    if args.migrate:
        payload = run_data_migration()
        if not args.json:
            print("Migration completed:")
            print(json.dumps(payload, indent=2))

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.check or args.migrate:
        print("=== HG data migration check ===")
        print(f"canonical: {report['canonical_root']}")
        print(f"legacy:    {report['legacy_root']} (exists={report['legacy_exists']})")
        if report["marker"]:
            print(f"marker version: {report['marker'].get('version')}")
        print()
        print(
            f"{'category':<42} {'legacy':>7} {'canonical':>9} "
            f"{'leg_only':>9} {'mismatch':>9}"
        )
        for row in report["categories"]:
            print(
                f"{row['canonical_rel']:<42} "
                f"{row['legacy_count']:>7} {row['canonical_count']:>9} "
                f"{row['legacy_only_count']:>9} {row['hash_mismatch_count']:>9}"
            )
        sess = report["sessions"]
        print()
        print(
            f"sessions: legacy={sess['legacy_ids']} canonical={sess['canonical_ids']} "
            f"missing_in_canonical={sess['legacy_missing_in_canonical']} "
            f"canonical_only={sess['canonical_only']}"
        )
        if report["notes"]:
            print("\nNotes:")
            for note in report["notes"]:
                print(f"  - {note}")
        if report["blockers"]:
            print("\nBlockers:")
            for blocker in report["blockers"]:
                print(f"  - {blocker}")
        print()
        print("compatibility_retirement_safe:", report["compatibility_retirement_safe"])

    return 0 if report["compatibility_retirement_safe"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

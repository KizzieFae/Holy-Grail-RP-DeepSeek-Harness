"""One-time migration from legacy ``autogen_rp/python/data`` to ``data/``."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domain.paths import (
    MIGRATION_MARKER_NAME,
    holy_grail_data_dir,
    legacy_data_dir,
)

MIGRATION_VERSION = 1

# (canonical relative path, legacy relative path under legacy_data_dir)
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


def run_data_migration() -> dict[str, Any]:
    """Migrate legacy local data into the canonical root when needed."""
    canonical = holy_grail_data_dir()
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

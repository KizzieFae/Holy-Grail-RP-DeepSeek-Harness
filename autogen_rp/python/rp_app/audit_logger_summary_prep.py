"""Pre-pass helpers before ``_audit_summary.json`` assembly (Issue #154 Slice C)."""

from pathlib import Path
from typing import Any

from audit_instrumentation import (
    audit_instrumentation_enabled,
    log_audit_warning,
)
from audit_logger_summary_output_continuity import count_indexed_turns


def should_backfill_manifest(manifest: dict[str, Any]) -> bool:
    cast = manifest.get("cast")
    if isinstance(cast, list) and len(cast) > 0:
        return False
    st = manifest.get("scene_template") or {}
    if str(st.get("template_id", "") or "").strip():
        return False
    if str(st.get("premise", "") or "").strip():
        return False
    if st.get("role_assignments"):
        return False
    return True


def backfill_manifest_from_narrative_if_needed(
    *,
    manifest: dict[str, Any],
    narrative: dict[str, Any],
    normalize_scene_template_metadata,
) -> None:
    if not should_backfill_manifest(manifest):
        return
    nst = normalize_scene_template_metadata(narrative.get("scene_template") or {})
    mst = normalize_scene_template_metadata(manifest.get("scene_template") or {})
    if any(
        [
            nst.get("template_id"),
            nst.get("premise"),
            nst.get("role_assignments"),
        ]
    ):
        manifest["scene_template"] = nst
    elif mst.get("template_id") or mst.get("role_assignments"):
        manifest["scene_template"] = mst

    cast: list[str] = []
    for name in (narrative.get("character_stats") or {}).keys():
        s = str(name or "").strip()
        if s and s not in cast:
            cast.append(s)
    if not cast:
        for t in narrative.get("turns") or []:
            c = str(t.get("character", "") or "").strip()
            if c and c not in cast:
                cast.append(c)
    manifest["cast"] = cast
    manifest["total_characters"] = len(cast)
    if not str(manifest.get("opening_description", "") or "").strip():
        cn = str(narrative.get("complete_narrative", "") or "").strip()
        if cn:
            manifest["opening_description"] = (
                cn[:500] + ("..." if len(cn) > 500 else "")
            )


def backfill_manifest_cast_from_index_if_needed(
    manifest: dict[str, Any],
    index: dict[str, Any],
) -> None:
    cast = manifest.get("cast")
    if isinstance(cast, list) and len(cast) > 0:
        return
    seen: list[str] = []
    for re in index.get("rounds", []):
        for t in re.get("turns", []) or []:
            if not isinstance(t, dict):
                continue
            c = str(t.get("acting_character", "") or "").strip()
            if c and c not in seen:
                seen.append(c)
    if seen:
        manifest["cast"] = seen
        manifest["total_characters"] = len(seen)


def scan_audit_artifact_gaps(
    session_path: Path,
    index: dict[str, Any],
    narrative: dict[str, Any],
) -> None:
    if not audit_instrumentation_enabled():
        return
    idx_turns = count_indexed_turns(index.get("rounds", []))
    narr_turns = len(narrative.get("turns") or [])
    if idx_turns > 0 and narr_turns == 0:
        log_audit_warning(
            f"audit: {session_path.name}: _round_index has {idx_turns} indexed turn(s) "
            "but _narrative.json has no turns (_narrative.json may not have been written)."
        )
    for re in index.get("rounds", []):
        try:
            rn = int(re.get("round_number", 0) or 0)
        except (TypeError, ValueError):
            continue
        if rn <= 0:
            continue
        rdir = session_path / f"round_{rn:03d}"
        if not rdir.is_dir():
            log_audit_warning(
                f"audit: {session_path.name}: missing {rdir.name} "
                "(indexed rounds but no per-turn audit directory)."
            )
            continue
        if not list(rdir.glob("*_full.json")):
            log_audit_warning(
                f"audit: {session_path.name}: {rdir.name} contains no *_full.json files."
            )

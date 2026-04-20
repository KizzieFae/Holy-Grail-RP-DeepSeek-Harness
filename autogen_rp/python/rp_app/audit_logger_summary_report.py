import json
from pathlib import Path
from typing import Any

from audit_instrumentation import (
    audit_instrumentation_enabled,
    log_audit_warning,
)
from audit_logger_summary_output import (
    add_spotlight_anomaly,
    build_regression_checks,
    build_report,
    build_role_coverage,
    build_spotlight,
    count_indexed_turns,
)
from audit_logger_summary_rounds import (
    build_round_summaries,
    initialize_rounds_map,
    load_json,
    process_audit_files,
)
from continuity_observability_summary import (
    CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED,
    build_continuity_observability_status_v1_unavailable,
    build_continuity_observability_summary_v1,
)


def _enforce_continuity_observability_exclusivity(report: dict[str, Any]) -> None:
    """``continuity_observability_summary_v1`` and ``continuity_observability_status_v1`` are mutually exclusive."""
    has_summary = "continuity_observability_summary_v1" in report
    has_status = "continuity_observability_status_v1" in report
    if has_summary and has_status:
        raise RuntimeError(
            "audit invariant violated: continuity_observability_summary_v1 and "
            "continuity_observability_status_v1 must not both be present on _audit_summary.json"
        )


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    return load_json(path, default)


def _initialize_rounds_map(
    index: dict[str, Any], turns: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    return initialize_rounds_map(index, turns)


def _process_audit_files(
    *,
    session_path: Path,
    rounds_map: dict[int, dict[str, Any]],
    issue_categories: dict[str, dict[str, Any]],
    heuristic_issue_categories: dict[str, dict[str, Any]],
    summary_block_visibility: dict[str, Any],
    categorize_issue_text,
    record_issue_category,
    normalize_summary_block_metadata,
    prompt_reference,
    append_limited,
) -> None:
    process_audit_files(
        session_path=session_path,
        rounds_map=rounds_map,
        issue_categories=issue_categories,
        heuristic_issue_categories=heuristic_issue_categories,
        summary_block_visibility=summary_block_visibility,
        categorize_issue_text=categorize_issue_text,
        record_issue_category=record_issue_category,
        normalize_summary_block_metadata=normalize_summary_block_metadata,
        prompt_reference=prompt_reference,
        append_limited=append_limited,
    )


def _build_round_summaries(
    *,
    rounds_map: dict[int, dict[str, Any]],
    issue_categories: dict[str, dict[str, Any]],
    record_issue_category,
) -> tuple[list[dict[str, Any]], list[str]]:
    return build_round_summaries(
        rounds_map=rounds_map,
        issue_categories=issue_categories,
        record_issue_category=record_issue_category,
    )


def _should_backfill_manifest(manifest: dict[str, Any]) -> bool:
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


def _backfill_manifest_from_narrative_if_needed(
    *,
    manifest: dict[str, Any],
    narrative: dict[str, Any],
    normalize_scene_template_metadata,
) -> None:
    if not _should_backfill_manifest(manifest):
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


def _backfill_manifest_cast_from_index_if_needed(
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


def _scan_audit_artifact_gaps(
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


def write_summary_report(
    *,
    session_path: Path,
    session_owner: str,
    session_number: int,
    normalize_scene_template_metadata,
    empty_issue_categories,
    empty_summary_block_visibility,
    categorize_issue_text,
    record_issue_category,
    normalize_summary_block_metadata,
    prompt_reference,
    append_limited,
    utc_timestamp,
    continuity_manager: Any | None = None,
) -> str:
    manifest = _load_json(session_path / "_manifest.json", {})
    index = _load_json(session_path / "_round_index.json", {"rounds": []})
    narrative = _load_json(
        session_path / "_narrative.json",
        {"turns": [], "character_stats": {}},
    )
    report_path = session_path / "_audit_summary.json"

    _backfill_manifest_from_narrative_if_needed(
        manifest=manifest,
        narrative=narrative,
        normalize_scene_template_metadata=normalize_scene_template_metadata,
    )
    _backfill_manifest_cast_from_index_if_needed(manifest, index)
    _scan_audit_artifact_gaps(session_path, index, narrative)

    turns = narrative.get("turns", [])
    character_stats = narrative.get("character_stats", {})
    scene_template = normalize_scene_template_metadata(
        manifest.get("scene_template") or narrative.get("scene_template") or {}
    )
    rounds_map = _initialize_rounds_map(index, turns)
    issue_categories = empty_issue_categories()
    heuristic_issue_categories = empty_issue_categories()
    summary_block_visibility = empty_summary_block_visibility()

    _process_audit_files(
        session_path=session_path,
        rounds_map=rounds_map,
        issue_categories=issue_categories,
        heuristic_issue_categories=heuristic_issue_categories,
        summary_block_visibility=summary_block_visibility,
        categorize_issue_text=categorize_issue_text,
        record_issue_category=record_issue_category,
        normalize_summary_block_metadata=normalize_summary_block_metadata,
        prompt_reference=prompt_reference,
        append_limited=append_limited,
    )
    round_summaries, anomalies = _build_round_summaries(
        rounds_map=rounds_map,
        issue_categories=issue_categories,
        record_issue_category=record_issue_category,
    )

    spotlight = build_spotlight(character_stats)
    role_coverage = build_role_coverage(
        manifest=manifest,
        scene_template=scene_template,
        character_stats=character_stats,
    )
    add_spotlight_anomaly(
        spotlight=spotlight,
        turns=turns,
        anomalies=anomalies,
        issue_categories=issue_categories,
        record_issue_category=record_issue_category,
    )
    regression_checks = build_regression_checks(issue_categories)
    report = build_report(
        session_owner=session_owner,
        session_number=session_number,
        manifest=manifest,
        narrative=narrative,
        scene_template=scene_template,
        spotlight=spotlight,
        role_coverage=role_coverage,
        round_summaries=round_summaries,
        summary_block_visibility=summary_block_visibility,
        anomalies=anomalies,
        issue_categories=issue_categories,
        heuristic_issue_categories=heuristic_issue_categories,
        regression_checks=regression_checks,
        utc_timestamp=utc_timestamp,
        index_rounds=index.get("rounds", []),
    )
    if continuity_manager is not None:
        # Replace-only block for Issue #79 Slice 4 (no merge with prior file contents).
        report.pop("continuity_observability_status_v1", None)
        report["continuity_observability_summary_v1"] = (
            build_continuity_observability_summary_v1(continuity_manager)
        )
    else:
        # Explicit availability marker — do not emit empty or zero-filled summary rollup.
        report.pop("continuity_observability_summary_v1", None)
        report["continuity_observability_status_v1"] = (
            build_continuity_observability_status_v1_unavailable(
                reason=CONTINUITY_OBSERVABILITY_STATUS_REASON_CONTINUITY_MANAGER_NOT_PROVIDED,
            )
        )
    _enforce_continuity_observability_exclusivity(report)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    return str(report_path)

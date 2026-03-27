import json
from pathlib import Path
from typing import Any
from audit_logger_summary_output import (
    add_spotlight_anomaly,
    build_regression_checks,
    build_report,
    build_role_coverage,
    build_spotlight,
)
from audit_logger_summary_rounds import (
    build_round_summaries,
    initialize_rounds_map,
    load_json,
    process_audit_files,
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
) -> str:
    manifest = _load_json(session_path / "_manifest.json", {})
    index = _load_json(session_path / "_round_index.json", {"rounds": []})
    narrative = _load_json(
        session_path / "_narrative.json",
        {"turns": [], "character_stats": {}, "total_rounds": 0},
    )
    report_path = session_path / "_audit_summary.json"

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
    )
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    return str(report_path)

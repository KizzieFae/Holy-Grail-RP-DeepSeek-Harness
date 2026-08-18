from typing import Any

from audit_logger_summary_output_continuity import (
    continuity_overview_from_narrative_turns,
    continuity_overview_from_round_index,
    continuity_overview_is_effectively_empty,
    count_indexed_turns,
    index_rounds_non_empty,
)
from audit_logger_summary_output_report_core import assemble_audit_summary_report_dict

# Re-export continuity helpers for callers that imported from this module historically.
__all__ = [
    "add_spotlight_anomaly",
    "assemble_audit_summary_report_dict",
    "build_regression_checks",
    "build_report",
    "build_role_coverage",
    "build_spotlight",
    "continuity_overview_from_narrative_turns",
    "continuity_overview_from_round_index",
    "continuity_overview_is_effectively_empty",
    "count_indexed_turns",
    "index_rounds_non_empty",
]


def build_spotlight(character_stats: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "character": char_name,
                "turns": stats.get("turns", 0),
                "dialogue_count": stats.get("dialogue_count", 0),
                "avg_response_length": stats.get("avg_response_length", 0),
                "spotlight_percentage": stats.get("spotlight_percentage", 0),
            }
            for char_name, stats in character_stats.items()
        ],
        key=lambda item: item.get("turns", 0),
        reverse=True,
    )


def build_role_coverage(
    *,
    manifest: dict[str, Any],
    scene_template: dict[str, Any],
    character_stats: dict[str, Any],
) -> list[dict[str, Any]]:
    role_coverage: list[dict[str, Any]] = []
    characters_for_role_coverage = list(
        dict.fromkeys(
            [
                str(item or "").strip()
                for item in manifest.get("cast", [])
                if str(item or "").strip()
            ]
            + list(scene_template["role_assignments"].keys())
        )
    )
    for character in characters_for_role_coverage:
        stats = character_stats.get(character, {})
        role_coverage.append(
            {
                "character": character,
                "role": scene_template["role_assignments"].get(character, ""),
                "presence_constraint": scene_template[
                    "character_presence_constraints"
                ].get(character, ""),
                "authority_label": scene_template["character_authority_labels"].get(
                    character, ""
                ),
                "turns": int(stats.get("turns", 0) or 0),
                "spotlight_percentage": stats.get("spotlight_percentage", 0),
            }
        )
    return role_coverage


def build_regression_checks(
    issue_categories: dict[str, dict[str, Any]],
) -> dict[str, bool]:
    return {
        "character_drift": issue_categories["character_drift"]["count"] == 0,
        "memory_drift": issue_categories["memory_drift"]["count"] == 0,
        "turn_selection_mistakes": issue_categories["turn_selection_mistakes"]["count"]
        == 0,
        "repetitive_phrasing": issue_categories["repetitive_phrasing"]["count"] == 0,
        "continuity_signal_gaps": issue_categories["continuity_signal_gaps"]["count"]
        == 0,
        "issue_lifecycle_gaps": issue_categories["issue_lifecycle_gaps"]["count"] == 0,
    }


def add_spotlight_anomaly(
    *,
    spotlight: list[dict[str, Any]],
    turns: list[dict[str, Any]],
    anomalies: list[str],
    issue_categories: dict[str, dict[str, Any]],
    record_issue_category,
) -> None:
    if (
        spotlight
        and len(turns) >= 4
        and spotlight[0].get("spotlight_percentage", 0) >= 70
    ):
        anomaly = f"Spotlight imbalance detected: {spotlight[0]['character']} has {spotlight[0]['spotlight_percentage']}% of turns"
        anomalies.append(anomaly)
        record_issue_category(issue_categories, "turn_selection_mistakes", anomaly)


def build_report(
    *,
    session_owner: str,
    session_number: int,
    manifest: dict[str, Any],
    narrative: dict[str, Any],
    scene_template: dict[str, Any],
    spotlight: list[dict[str, Any]],
    role_coverage: list[dict[str, Any]],
    round_summaries: list[dict[str, Any]],
    summary_block_visibility: dict[str, Any],
    anomalies: list[str],
    issue_categories: dict[str, dict[str, Any]],
    heuristic_issue_categories: dict[str, dict[str, Any]],
    regression_checks: dict[str, bool],
    utc_timestamp,
    index_rounds: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble deterministic ``_audit_summary.json`` payload (delegates to report core)."""
    return assemble_audit_summary_report_dict(
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
        index_rounds=index_rounds,
    )

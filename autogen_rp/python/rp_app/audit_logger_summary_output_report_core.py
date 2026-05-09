"""Assembly of the ``_audit_summary.json`` overview payload (Issue #154 Slice E)."""

from typing import Any

from audit_logger_summary_output_continuity import (
    continuity_overview_from_narrative_turns,
    continuity_overview_from_round_index,
    continuity_overview_is_effectively_empty,
    count_indexed_turns,
    index_rounds_non_empty,
)


def assemble_audit_summary_report_dict(
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
    must_remain_assigned_characters = [
        item["character"]
        for item in role_coverage
        if item.get("presence_constraint") == "must_remain"
    ]
    must_remain_characters_with_zero_turns = [
        item["character"]
        for item in role_coverage
        if item.get("presence_constraint") == "must_remain"
        and int(item.get("turns", 0) or 0) == 0
    ]
    turns = narrative.get("turns") or []
    idx_rounds = index_rounds if index_rounds is not None else []
    idx_turn_total = count_indexed_turns(idx_rounds)
    idx_nonempty = index_rounds_non_empty(idx_rounds)

    manifest_tt_raw = manifest.get("total_turns")
    if manifest_tt_raw is None:
        manifest_tt = len(turns) if turns else 0
    else:
        manifest_tt = int(manifest_tt_raw) if manifest_tt_raw else 0
    total_turns = max(manifest_tt, len(turns), idx_turn_total)

    cov_narr = continuity_overview_from_narrative_turns(turns)
    cov_idx = (
        continuity_overview_from_round_index(idx_rounds) if idx_nonempty else None
    )

    if not turns and idx_nonempty and cov_idx is not None:
        continuity_overview = cov_idx
        continuity_overview_source = "index"
    elif turns and idx_nonempty and cov_idx is not None:
        if continuity_overview_is_effectively_empty(
            cov_narr
        ) and not continuity_overview_is_effectively_empty(cov_idx):
            continuity_overview = cov_idx
            continuity_overview_source = "mixed"
        else:
            continuity_overview = cov_narr
            continuity_overview_source = "narrative"
    else:
        continuity_overview = cov_narr
        continuity_overview_source = "narrative"

    narrative_tr = narrative.get("total_rounds")
    if narrative_tr is None:
        narrative_tr_eff = 0
    else:
        narrative_tr_eff = int(narrative_tr) if narrative_tr else 0
    total_rounds = max(len(round_summaries), narrative_tr_eff)
    prompt_evaluations = int(summary_block_visibility.get("prompt_evaluations", 0) or 0)
    summary_block_quality = {
        "prompt_evaluations": prompt_evaluations,
        "prompts_with_summary_available": int(
            summary_block_visibility.get("prompt_evaluations_with_summary_available", 0)
            or 0
        ),
        "prompts_with_summary_injection": int(
            summary_block_visibility.get("prompt_evaluations_with_summary_injection", 0)
            or 0
        ),
        "prompts_with_available_but_unused_summary": len(
            summary_block_visibility.get(
                "prompt_evaluations_where_summary_was_available_but_not_used", []
            )
        ),
        "fallback_selection_count": len(
            summary_block_visibility.get(
                "prompt_evaluations_with_fallback_selection", []
            )
        ),
        "summary_injection_rate": (
            round(
                int(
                    summary_block_visibility.get(
                        "prompt_evaluations_with_summary_injection", 0
                    )
                    or 0
                )
                / prompt_evaluations,
                3,
            )
            if prompt_evaluations > 0
            else 0
        ),
        "summary_availability_rate": (
            round(
                int(
                    summary_block_visibility.get(
                        "prompt_evaluations_with_summary_available", 0
                    )
                    or 0
                )
                / prompt_evaluations,
                3,
            )
            if prompt_evaluations > 0
            else 0
        ),
    }
    return {
        "session_owner": session_owner,
        "session_number": session_number,
        "generated_at": utc_timestamp(),
        "manifest": {
            "cast": manifest.get("cast", []),
            "user_name": manifest.get("user_name"),
            "opening_description": manifest.get("opening_description"),
            "total_characters": int(manifest.get("total_characters", 0) or 0)
            or len(manifest.get("cast") or []),
            "scene_template": scene_template,
        },
        "scene_template": {
            **scene_template,
            "role_coverage": role_coverage,
            "must_remain": {
                "assigned_characters": must_remain_assigned_characters,
                "characters_with_zero_turns": must_remain_characters_with_zero_turns,
            },
        },
        "overview": {
            "total_rounds": total_rounds,
            "total_turns": total_turns,
            "total_logged_rounds": len(round_summaries),
            "latest_round": (
                round_summaries[-1]["round_number"] if round_summaries else 0
            ),
            "last_updated": narrative.get("last_updated") or manifest.get("timestamp"),
        },
        "continuity_overview": continuity_overview,
        "continuity_overview_source": continuity_overview_source,
        "spotlight": spotlight,
        "recent_rounds": round_summaries[-5:],
        "round_summaries": round_summaries,
        "summary_block_visibility": summary_block_visibility,
        "summary_block_quality": summary_block_quality,
        "anomalies": anomalies,
        "issue_categories": issue_categories,
        "heuristic_issue_categories": heuristic_issue_categories,
        "regression_checks": regression_checks,
    }

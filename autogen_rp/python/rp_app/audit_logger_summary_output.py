from typing import Any


def _flatten_index_turns(index_rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for re in index_rounds or []:
        for t in re.get("turns", []) or []:
            if isinstance(t, dict):
                out.append(t)
    return out


def count_indexed_turns(index_rounds: list[dict[str, Any]]) -> int:
    return len(_flatten_index_turns(index_rounds))


def index_rounds_non_empty(index_rounds: list[dict[str, Any]]) -> bool:
    return count_indexed_turns(index_rounds) > 0


def continuity_overview_from_narrative_turns(
    turns: list[dict[str, Any]],
) -> dict[str, Any]:
    total_state_changes = sum(
        len([item for item in turn.get("state_changes", []) if str(item).strip()])
        for turn in turns
    )
    total_actionable_implications = sum(
        len(
            [
                item
                for item in turn.get("actionable_implications", [])
                if str(item).strip()
            ]
        )
        for turn in turns
    )
    turns_with_state_change = sum(
        1
        for turn in turns
        if any(str(item).strip() for item in turn.get("state_changes", []))
    )
    turns_with_issue_update = sum(
        1
        for turn in turns
        if any(isinstance(item, dict) for item in turn.get("issue_updates", []))
    )
    turns_without_material_change = sum(
        1
        for turn in turns
        if not any(str(item).strip() for item in turn.get("state_changes", []))
        and not any(isinstance(item, dict) for item in turn.get("issue_updates", []))
        and not str(turn.get("environment_event", "") or "").strip()
    )
    presence_transitions = [
        change
        for turn in turns
        for change in turn.get("presence_changes", [])
        if isinstance(change, dict)
    ]
    issue_updates_flat = [
        update
        for turn in turns
        for update in turn.get("issue_updates", [])
        if isinstance(update, dict)
    ]
    return {
        "turns_with_state_change": turns_with_state_change,
        "turns_with_issue_update": turns_with_issue_update,
        "turns_without_material_change": turns_without_material_change,
        "total_state_changes": total_state_changes,
        "total_actionable_implications": total_actionable_implications,
        "presence_transition_count": len(presence_transitions),
        "issue_update_count": len(issue_updates_flat),
        "resolved_issue_updates": sum(
            1
            for update in issue_updates_flat
            if str(update.get("status", "") or "").strip().lower() == "resolved"
        ),
        "stalled_issue_updates": sum(
            1
            for update in issue_updates_flat
            if str(update.get("status", "") or "").strip().lower() == "stalled"
        ),
        "decision_or_revelation_turns": sum(
            1
            for turn in turns
            if str(turn.get("continuity_event_type", "") or "").strip()
            in {"decision", "revelation"}
        ),
    }


def continuity_overview_from_round_index(
    index_rounds: list[dict[str, Any]],
) -> dict[str, Any]:
    flat = _flatten_index_turns(index_rounds)
    turns_with_state_change = sum(
        1 for t in flat if int(t.get("state_change_count", 0) or 0) > 0
    )
    turns_with_issue_update = sum(
        1 for t in flat if int(t.get("issue_update_count", 0) or 0) > 0
    )
    turns_without_material_change = sum(
        1
        for t in flat
        if int(t.get("state_change_count", 0) or 0) == 0
        and int(t.get("issue_update_count", 0) or 0) == 0
        and int(t.get("presence_change_count", 0) or 0) == 0
    )
    total_state_changes = sum(int(t.get("state_change_count", 0) or 0) for t in flat)
    presence_transition_count = sum(
        int(t.get("presence_change_count", 0) or 0) for t in flat
    )
    issue_update_count = sum(int(t.get("issue_update_count", 0) or 0) for t in flat)
    decision_or_revelation_turns = sum(
        1
        for t in flat
        if str(t.get("continuity_event_type", "") or "").strip().lower()
        in {"decision", "revelation"}
    )
    return {
        "turns_with_state_change": turns_with_state_change,
        "turns_with_issue_update": turns_with_issue_update,
        "turns_without_material_change": turns_without_material_change,
        "total_state_changes": total_state_changes,
        "total_actionable_implications": 0,
        "presence_transition_count": presence_transition_count,
        "issue_update_count": issue_update_count,
        "resolved_issue_updates": 0,
        "stalled_issue_updates": 0,
        "decision_or_revelation_turns": decision_or_revelation_turns,
    }


def continuity_overview_is_effectively_empty(cov: dict[str, Any]) -> bool:
    return (
        int(cov.get("total_state_changes", 0) or 0) == 0
        and int(cov.get("turns_with_state_change", 0) or 0) == 0
        and int(cov.get("turns_with_issue_update", 0) or 0) == 0
        and int(cov.get("issue_update_count", 0) or 0) == 0
    )


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

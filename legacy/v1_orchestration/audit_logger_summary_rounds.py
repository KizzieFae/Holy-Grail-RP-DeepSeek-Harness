import json
from pathlib import Path
from typing import Any


ROUND_TEMPLATE = {
    "round_number": 0,
    "indexed_turns": [],
    "narrative_turns": [],
    "summary_block_audits": [],
}


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def empty_round(round_number: int) -> dict[str, Any]:
    return {
        **ROUND_TEMPLATE,
        "round_number": round_number,
        "indexed_turns": [],
        "narrative_turns": [],
        "summary_block_audits": [],
    }


def initialize_rounds_map(
    index: dict[str, Any], turns: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    rounds_map: dict[int, dict[str, Any]] = {}
    for round_entry in index.get("rounds", []):
        try:
            round_number = int(round_entry.get("round_number", 0))
        except (TypeError, ValueError):
            continue
        rounds_map[round_number] = {
            "round_number": round_number,
            "indexed_turns": round_entry.get("turns", []),
            "narrative_turns": [],
            "summary_block_audits": [],
        }

    for turn in turns:
        try:
            round_number = int(turn.get("round", 0))
        except (TypeError, ValueError):
            continue
        rounds_map.setdefault(round_number, empty_round(round_number))[
            "narrative_turns"
        ].append(turn)
    return rounds_map


def process_audit_files(
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
    for round_dir in sorted(session_path.glob("round_*")):
        if not round_dir.is_dir():
            continue
        for audit_file in round_dir.glob("*_full.json"):
            try:
                with open(audit_file, "r", encoding="utf-8") as handle:
                    audit_entry = json.load(handle)
            except (json.JSONDecodeError, IOError):
                continue

            metadata = audit_entry.get("metadata", {})
            parsed_output = audit_entry.get("parsed_output", {})
            raw_response = str(audit_entry.get("raw_response", "") or "")
            try:
                round_number = int(audit_entry.get("round_number", 0) or 0)
            except (TypeError, ValueError):
                round_number = 0
            try:
                turn_number = int(audit_entry.get("turn_number", 0) or 0)
            except (TypeError, ValueError):
                turn_number = 0
            bot_name = str(audit_entry.get("bot_name", "") or "")

            for turn_issue in metadata.get("turn_selection_issues", []):
                record_issue_category(
                    issue_categories, "turn_selection_mistakes", str(turn_issue)
                )

            for candidate in [metadata.get("parse_error") or ""]:
                category = categorize_issue_text(str(candidate))
                record_issue_category(issue_categories, category, str(candidate))

            for candidate in [parsed_output.get("reason", ""), raw_response[:300]]:
                category = categorize_issue_text(str(candidate))
                record_issue_category(
                    heuristic_issue_categories, category, str(candidate)
                )

            summary_metadata = normalize_summary_block_metadata(
                metadata.get("summary_blocks")
            )
            if summary_metadata is None:
                continue

            rounds_map.setdefault(round_number, empty_round(round_number))[
                "summary_block_audits"
            ].append(
                {
                    "turn_number": turn_number,
                    "bot_name": bot_name,
                    **summary_metadata,
                }
            )

            prompt_ref = prompt_reference(round_number, turn_number, bot_name)
            summary_block_visibility["prompt_evaluations"] += 1
            if summary_metadata["summary_generation_eligible"]:
                summary_block_visibility["prompt_evaluations_generation_eligible"] += 1
            summary_block_visibility["summary_blocks_generated_total_max"] = max(
                summary_block_visibility["summary_blocks_generated_total_max"],
                summary_metadata["summary_blocks_generated_total"],
            )
            summary_block_visibility["summary_blocks_used_total"] += summary_metadata[
                "summary_blocks_selected_count"
            ]
            if summary_metadata["summary_blocks_available_count"] > 0:
                summary_block_visibility[
                    "prompt_evaluations_with_summary_available"
                ] += 1
            if summary_metadata["summary_blocks_selected_count"] > 0:
                summary_block_visibility[
                    "prompt_evaluations_with_summary_injection"
                ] += 1
                if summary_block_visibility["first_prompt_with_summary_block"] is None:
                    summary_block_visibility["first_prompt_with_summary_block"] = (
                        prompt_ref
                    )
            if (
                summary_metadata["summary_blocks_available_count"] > 0
                and summary_metadata["summary_blocks_selected_count"] == 0
            ):
                append_limited(
                    summary_block_visibility[
                        "prompt_evaluations_where_summary_was_available_but_not_used"
                    ],
                    prompt_ref,
                )
            if summary_metadata["fallback_used"]:
                append_limited(
                    summary_block_visibility[
                        "prompt_evaluations_with_fallback_selection"
                    ],
                    prompt_ref,
                )


def build_round_summaries(
    *,
    rounds_map: dict[int, dict[str, Any]],
    issue_categories: dict[str, dict[str, Any]],
    record_issue_category,
) -> tuple[list[dict[str, Any]], list[str]]:
    round_summaries: list[dict[str, Any]] = []
    anomalies: list[str] = []

    for round_number in sorted(rounds_map):
        round_data = rounds_map[round_number]
        indexed_turns = round_data.get("indexed_turns", [])
        narrative_turns = sorted(
            round_data.get("narrative_turns", []), key=lambda item: item.get("turn", 0)
        )
        summary_block_audits = sorted(
            round_data.get("summary_block_audits", []),
            key=lambda item: (
                int(item.get("turn_number", 0) or 0),
                str(item.get("bot_name", "") or ""),
            ),
        )

        acting_characters: list[str] = []
        director_reasons: list[str] = []
        turn_roles: list[dict[str, Any]] = []
        tension_shifts: list[str] = []
        environment_events: list[str] = []
        rendered_segments: list[str] = []
        turn_numbers: list[int] = []
        continuity_event_types: list[str] = []
        state_changes: list[str] = []
        actionable_implications: list[str] = []
        issue_updates: list[dict[str, Any]] = []
        presence_changes: list[dict[str, Any]] = []
        scene_recent_deltas: list[str] = []
        turns_with_state_change = 0
        turns_with_issue_update = 0
        turns_without_material_change = 0

        for item in narrative_turns:
            character = str(item.get("character", "") or "").strip()
            if character and character not in acting_characters:
                acting_characters.append(character)

            role = str(item.get("character_role", "") or "").strip()
            presence_constraint = str(
                item.get("character_presence_constraint", "") or ""
            ).strip()
            authority_label = str(
                item.get("character_authority_label", "") or ""
            ).strip()
            if any([character, role, presence_constraint, authority_label]):
                turn_roles.append(
                    {
                        "turn_number": int(item.get("turn", 0) or 0),
                        "character": character,
                        "role": role,
                        "presence_constraint": presence_constraint,
                        "authority_label": authority_label,
                    }
                )

            reason = str(item.get("director_reason", "") or "").strip()
            if reason and reason not in director_reasons:
                director_reasons.append(reason)

            try:
                turn_number = int(item.get("turn", 0))
            except (TypeError, ValueError):
                turn_number = 0
            if turn_number:
                turn_numbers.append(turn_number)

            tension_shift = str(item.get("tension_shift", "") or "").strip()
            if tension_shift and tension_shift not in tension_shifts:
                tension_shifts.append(tension_shift)
            environment_event = str(item.get("environment_event", "") or "").strip()
            if environment_event and environment_event not in environment_events:
                environment_events.append(environment_event)
            rendered_output = str(item.get("rendered_output", "") or "").strip()
            if rendered_output:
                rendered_segments.append(rendered_output)

            continuity_event_type = str(
                item.get("continuity_event_type", "") or ""
            ).strip()
            if (
                continuity_event_type
                and continuity_event_type not in continuity_event_types
            ):
                continuity_event_types.append(continuity_event_type)

            turn_state_changes = [
                str(change)
                for change in item.get("state_changes", [])
                if str(change).strip()
            ]
            if turn_state_changes:
                turns_with_state_change += 1
            for change in turn_state_changes:
                if change not in state_changes:
                    state_changes.append(change)

            turn_actionable_implications = [
                str(change)
                for change in item.get("actionable_implications", [])
                if str(change).strip()
            ]
            for implication in turn_actionable_implications:
                if implication not in actionable_implications:
                    actionable_implications.append(implication)

            turn_issue_updates = [
                dict(update)
                for update in item.get("issue_updates", [])
                if isinstance(update, dict)
            ]
            if turn_issue_updates:
                turns_with_issue_update += 1
            for update in turn_issue_updates:
                if update not in issue_updates:
                    issue_updates.append(update)

            turn_presence_changes = [
                dict(change)
                for change in item.get("presence_changes", [])
                if isinstance(change, dict)
            ]
            for change in turn_presence_changes:
                if change not in presence_changes:
                    presence_changes.append(change)

            scene_recent_delta = str(item.get("scene_recent_delta", "") or "").strip()
            if scene_recent_delta and scene_recent_delta not in scene_recent_deltas:
                scene_recent_deltas.append(scene_recent_delta)

            if (
                not turn_state_changes
                and not turn_issue_updates
                and not environment_event
            ):
                turns_without_material_change += 1

        for item in indexed_turns:
            reason = str(item.get("director_reason", "") or "").strip()
            if reason and reason not in director_reasons:
                director_reasons.append(reason)

        expected_turns = list(range(1, len(turn_numbers) + 1)) if turn_numbers else []
        if turn_numbers and turn_numbers != expected_turns:
            anomaly = f"Round {round_number:03d} has non-sequential turn numbering: {turn_numbers}"
            anomalies.append(anomaly)
            record_issue_category(issue_categories, "turn_selection_mistakes", anomaly)

        acting_sequence = [
            str(item.get("character", "") or "").strip() for item in narrative_turns
        ]
        for idx in range(1, len(acting_sequence)):
            if (
                acting_sequence[idx]
                and acting_sequence[idx] == acting_sequence[idx - 1]
            ):
                anomaly = f"Round {round_number:03d} repeats acting character consecutively: {acting_sequence[idx]}"
                anomalies.append(anomaly)
                record_issue_category(
                    issue_categories, "turn_selection_mistakes", anomaly
                )
                break

        if (
            indexed_turns
            and narrative_turns
            and len(indexed_turns) != len(narrative_turns)
        ):
            anomaly = f"Round {round_number:03d} mismatch: index has {len(indexed_turns)} turns, narrative has {len(narrative_turns)}"
            anomalies.append(anomaly)
            record_issue_category(issue_categories, "turn_selection_mistakes", anomaly)

        excerpt = "\n\n".join(rendered_segments).strip()
        if len(excerpt) > 500:
            excerpt = excerpt[:500] + "..."

        lowered_segments = [segment.lower() for segment in rendered_segments if segment]
        if len(lowered_segments) >= 2 and len(set(lowered_segments)) < len(
            lowered_segments
        ):
            anomaly = f"Round {round_number:03d} contains repeated rendered phrasing"
            anomalies.append(anomaly)
            record_issue_category(issue_categories, "repetitive_phrasing", anomaly)

        if (
            len(narrative_turns) >= 2
            and not state_changes
            and not issue_updates
            and not environment_events
        ):
            anomaly = f"Round {round_number:03d} produced no material continuity change signals"
            anomalies.append(anomaly)
            record_issue_category(issue_categories, "continuity_signal_gaps", anomaly)

        if (
            any(item.get("active_issue_ids_after", []) for item in narrative_turns)
            and not issue_updates
            and not state_changes
        ):
            anomaly = f"Round {round_number:03d} left active issues in place without progression or resolution signals"
            anomalies.append(anomaly)
            record_issue_category(issue_categories, "issue_lifecycle_gaps", anomaly)

        issue_status_counts: dict[str, int] = {}
        for update in issue_updates:
            status = str(update.get("status", "") or "").strip()
            if not status:
                continue
            issue_status_counts[status] = issue_status_counts.get(status, 0) + 1

        round_summaries.append(
            {
                "round_number": round_number,
                "turn_count": len(narrative_turns) or len(indexed_turns),
                "acting_characters": acting_characters,
                "turn_roles": turn_roles,
                "director_reasons": director_reasons,
                "tension_shifts": tension_shifts,
                "environment_events": environment_events,
                "continuity_event_types": continuity_event_types,
                "state_change_count": len(state_changes),
                "state_changes": state_changes,
                "actionable_implication_count": len(actionable_implications),
                "actionable_implications": actionable_implications,
                "issue_update_count": len(issue_updates),
                "issue_status_counts": issue_status_counts,
                "issue_updates": issue_updates,
                "presence_change_count": len(presence_changes),
                "presence_changes": presence_changes,
                "scene_recent_deltas": scene_recent_deltas,
                "turns_with_state_change": turns_with_state_change,
                "turns_with_issue_update": turns_with_issue_update,
                "turns_without_material_change": turns_without_material_change,
                "turn_numbers": turn_numbers,
                "summary_block_usage": build_round_summary_block_usage(
                    summary_block_audits
                ),
                "narrative_excerpt": excerpt,
                "last_timestamp": (
                    narrative_turns[-1].get("timestamp") if narrative_turns else None
                ),
            }
        )

    return round_summaries, anomalies


def build_round_summary_block_usage(
    summary_block_audits: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "prompt_evaluations": len(summary_block_audits),
        "generated_total_max": max(
            (
                int(item.get("summary_blocks_generated_total", 0) or 0)
                for item in summary_block_audits
            ),
            default=0,
        ),
        "available_count_max": max(
            (
                int(item.get("summary_blocks_available_count", 0) or 0)
                for item in summary_block_audits
            ),
            default=0,
        ),
        "selected_count_total": sum(
            int(item.get("summary_blocks_selected_count", 0) or 0)
            for item in summary_block_audits
        ),
        "selected_summary_block_ids": list(
            dict.fromkeys(
                summary_id
                for item in summary_block_audits
                for summary_id in item.get("selected_summary_block_ids", [])
                if str(summary_id).strip()
            )
        ),
        "fallback_used": any(
            bool(item.get("fallback_used", False)) for item in summary_block_audits
        ),
        "prompt_details": [
            {
                "turn_number": int(item.get("turn_number", 0) or 0),
                "bot_name": str(item.get("bot_name", "") or ""),
                "summary_blocks_available_count": int(
                    item.get("summary_blocks_available_count", 0) or 0
                ),
                "summary_blocks_selected_count": int(
                    item.get("summary_blocks_selected_count", 0) or 0
                ),
                "selected_summary_block_ids": item.get(
                    "selected_summary_block_ids", []
                ),
                "selection_reason": str(item.get("selection_reason", "") or ""),
                "skipped_reason": str(item.get("skipped_reason", "") or ""),
                "fallback_used": bool(item.get("fallback_used", False)),
            }
            for item in summary_block_audits
        ],
    }

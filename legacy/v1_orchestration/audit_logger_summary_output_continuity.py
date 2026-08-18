"""Continuity overview metrics for audit summary output (extracted for Issue #154 Slice E)."""

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

"""Continuity → orchestration_state mirror (Issue #164)."""

from typing import Any, Callable


def sync_orchestration_state_from_continuity(
    *,
    orchestration_state: dict[str, Any],
    continuity_manager: Any,
    enforce_must_remain_presence_fn: Callable[[], None],
) -> dict[str, Any]:
    if (
        continuity_manager is None
        or getattr(continuity_manager, "scene_state", None) is None
    ):
        return orchestration_state

    enforce_must_remain_presence_fn()

    continuity_context = continuity_manager.get_orchestration_context(
        active_issue_limit=4,
        recent_event_limit=6,
        summary_limit=3,
    )
    scene_state = continuity_manager.scene_state
    orchestration_scene = orchestration_state.setdefault("scene_state", {})
    orchestration_scene["location"] = scene_state.location or ""
    orchestration_scene["time_of_day"] = scene_state.time_of_day or ""
    orchestration_scene["environment_description"] = (
        scene_state.environment_description or ""
    )
    orchestration_scene["scene_template_id"] = scene_state.scene_template_id or ""
    orchestration_scene["scene_premise"] = scene_state.scene_premise or ""
    orchestration_scene["role_assignments"] = scene_state.role_assignments.copy()
    orchestration_scene["character_presence_constraints"] = (
        scene_state.character_presence_constraints.copy()
    )
    orchestration_scene["character_authority_labels"] = (
        scene_state.character_authority_labels.copy()
    )
    orchestration_scene["location_entry_slots"] = list(
        getattr(scene_state, "location_entry_slots", []) or []
    )
    orchestration_scene["present_characters"] = scene_state.present_characters[:]
    orchestration_scene["offstage_characters"] = list(
        getattr(scene_state, "offstage_characters", []) or []
    )
    orchestration_scene["scene_phase"] = getattr(
        scene_state.phase, "value", str(scene_state.phase)
    )
    orchestration_scene["current_tension_level"] = scene_state.current_tension_level
    orchestration_scene["recent_delta"] = scene_state.recent_delta
    orchestration_scene["opening_description"] = scene_state.opening_description
    orchestration_scene["recent_environment_events"] = (
        scene_state.recent_environment_events[-8:]
    )
    tension_history = orchestration_scene.setdefault("tension_history", [])
    current_tension = str(scene_state.current_tension_level or "")
    if current_tension and (
        not tension_history or tension_history[-1] != current_tension
    ):
        tension_history.append(current_tension)
    orchestration_scene["tension_history"] = tension_history[-8:]
    orchestration_scene["resolved_events"] = continuity_context.get(
        "resolved_events", []
    )[-8:]
    orchestration_state["continuity_active_issues"] = [
        issue.to_dict() for issue in continuity_context.get("active_issues", [])
    ]
    orchestration_state["continuity_recent_public_events"] = [
        event.to_dict() for event in continuity_context.get("recent_public_events", [])
    ]
    orchestration_state["continuity_summary_blocks"] = [
        summary.to_dict() for summary in continuity_context.get("summary_blocks", [])
    ]
    return orchestration_state

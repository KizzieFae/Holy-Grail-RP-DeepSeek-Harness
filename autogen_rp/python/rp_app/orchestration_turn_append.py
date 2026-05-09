"""Append turn to bounded orchestration histories (Issue #164)."""

from __future__ import annotations

from typing import Any


def append_turn_to_orchestration_state(
    *,
    orchestration_state: dict[str, Any],
    next_actor: str,
    move: dict[str, Any],
    decision: dict[str, Any],
    consequences: list[str] | None = None,
    issue_updates: list[dict[str, Any]] | None = None,
    presence_changes: list[dict[str, Any]] | None = None,
    spotlight_history_limit: int,
    structured_move_history_limit: int,
    director_decision_history_limit: int,
    environment_history_limit: int,
    tension_history_limit: int,
) -> dict[str, Any]:
    orchestration_state.setdefault("spotlight_history", []).append(next_actor)
    orchestration_state["spotlight_history"] = orchestration_state["spotlight_history"][
        -spotlight_history_limit:
    ]
    move_entry: dict[str, Any] = {
        "speaker": next_actor,
        "action": move.get("action", ""),
        "dialogue": move.get("dialogue", ""),
        "motivation": move.get("motivation", {}),
        "environment_event": decision.get("environment_event", ""),
        "tension_shift": decision.get("tension_shift", ""),
        "audibility": str(move.get("audibility", "public") or "public"),
        "audience": list(move.get("audience") or []),
    }
    try:
        msv = int(str(move.get("move_schema_version", 0) or 0) or 0)
    except (TypeError, ValueError):
        msv = 0
    if msv == 2:
        move_entry["move_schema_version"] = 2
        raw_beats = move.get("beats")
        if isinstance(raw_beats, list):
            move_entry["beats"] = [
                dict(b) if isinstance(b, dict) else b for b in raw_beats
            ]
    # Persist existing computed outcome signals when available (no new logic).
    if consequences is not None:
        move_entry["consequences"] = list(consequences)
    if issue_updates is not None:
        move_entry["issue_updates"] = list(issue_updates)
    if presence_changes is not None:
        move_entry["presence_changes"] = list(presence_changes)

    orchestration_state.setdefault("recent_structured_moves", []).append(move_entry)
    orchestration_state["recent_structured_moves"] = orchestration_state[
        "recent_structured_moves"
    ][-structured_move_history_limit:]
    orchestration_state.setdefault("director_decisions", []).append(decision)
    orchestration_state["director_decisions"] = orchestration_state[
        "director_decisions"
    ][-director_decision_history_limit:]

    scene_state = orchestration_state.setdefault("scene_state", {})
    scene_state.setdefault("recent_environment_events", [])
    scene_state.setdefault("tension_history", [])
    if decision.get("environment_event"):
        scene_state["recent_environment_events"].append(decision["environment_event"])
        scene_state["recent_environment_events"] = scene_state[
            "recent_environment_events"
        ][-environment_history_limit:]
    if decision.get("tension_shift"):
        scene_state["tension_history"].append(decision["tension_shift"])
        scene_state["tension_history"] = scene_state["tension_history"][
            -tension_history_limit:
        ]
    return orchestration_state

"""Commit-time memory write policy (deterministic; no validation coupling)."""

from __future__ import annotations

from typing import Any, Callable

from perception_audibility import (
    event_knowledge_recipients,
    normalize_move_audibility,
)

from . import storage


def resolve_present_characters(
    *,
    continuity_manager: Any | None,
    char_names: list[str],
) -> list[str]:
    """Canonical present list for perception: scene_state.present_characters if non-empty, else char_names."""
    if continuity_manager is not None:
        scene_state = getattr(continuity_manager, "scene_state", None)
        if scene_state is not None:
            raw = getattr(scene_state, "present_characters", None)
            if isinstance(raw, list):
                out = [str(x).strip() for x in raw if str(x or "").strip()]
                if out:
                    return out
    return list(char_names)


def commit_character_turn_memory(
    *,
    state_manager: Any | None,
    character_names: list[str],
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    present_characters: list[str],
    build_memory_fact_summary_fn: Callable[[str, dict[str, Any]], str],
) -> None:
    if not state_manager or not acting_character:
        return

    move_norm = normalize_move_audibility(
        dict(move), acting_character, present_characters
    )
    motivation = move_norm.get("motivation", {})
    reason = str(director_decision.get("reason", "") or "").strip()
    event_summary = build_memory_fact_summary_fn(acting_character, move_norm)

    interpretation = reason
    if not interpretation and isinstance(motivation, dict):
        goal = str(motivation.get("goal", "") or "").strip()
        tactic = str(motivation.get("tactic", "") or "").strip()
        interpretation = "; ".join(
            part
            for part in [
                f"goal={goal}" if goal else "",
                f"tactic={tactic}" if tactic else "",
            ]
            if part
        )

    storage.append_actor_episodic(
        state_manager,
        acting_character,
        event_summary=event_summary,
        interpretation=interpretation,
    )

    recipients = set(
        event_knowledge_recipients(
            move_norm,
            acting_character=acting_character,
            present_characters=present_characters,
        )
    )
    observed_line = f"Observed: {event_summary}"
    for name in character_names:
        if not name or name == acting_character:
            continue
        if name not in recipients:
            continue
        storage.append_observer_episodic(
            state_manager, name, observed_line=observed_line
        )


def commit_user_message_memory(
    *,
    state_manager: Any | None,
    character_names: list[str],
    user_name: str,
    user_input: str,
    summarize_user_message_fn: Callable[[str, str], str],
) -> None:
    if not state_manager or not user_name:
        return
    summary = summarize_user_message_fn(user_name, user_input)
    for name in character_names:
        state = state_manager.get_state(name)
        if state is None:
            continue
        state.remember_user_interaction(user_name, summary)

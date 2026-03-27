from typing import Any


def record_user_memories(
    *, st_module: Any, user_name: str, user_input: str, summarize_user_message_fn
) -> None:
    state_manager = st_module.session_state.get("character_state_manager")
    if not state_manager or not user_name:
        return
    summary = summarize_user_message_fn(user_name, user_input)
    for character in st_module.session_state.get("characters", []):
        state_manager.get_state(character.name).remember_user_interaction(
            user_name, summary
        )


def record_character_memories(
    *,
    st_module: Any,
    acting_character: str,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    build_memory_fact_summary_fn,
) -> None:
    state_manager = st_module.session_state.get("character_state_manager")
    if not state_manager:
        return

    motivation = move.get("motivation", {})
    reason = str(director_decision.get("reason", "") or "").strip()
    event_summary = build_memory_fact_summary_fn(acting_character, move)

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

    state_manager.remember_event(acting_character, event_summary, interpretation)

    for agent in st_module.session_state.get("characters", []):
        observer = getattr(agent, "name", None)
        if not observer or observer == acting_character:
            continue
        observed_event = f"Observed: {event_summary}"
        state_manager.remember_event(observer, observed_event)

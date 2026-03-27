from typing import Any


def load_cross_session_memories(
    *,
    st_module: Any,
    character_names: list[str],
    user_name: str,
    session_manager_cls: Any,
) -> dict[str, Any]:
    session_manager = session_manager_cls()
    return session_manager.get_cross_session_memories(
        character_names=character_names,
        user_name=user_name,
        exclude_session_id=st_module.session_state.get("session_id"),
    )


def apply_cross_session_memories(
    char_states: dict[str, Any],
    cross_session_memories: dict[str, Any],
    user_name: str,
) -> None:
    relationship_map = cross_session_memories.get("cross_session_relationships", {})
    memory_map = cross_session_memories.get("character_user_memories", {})
    trend_map = cross_session_memories.get("relationship_trends", {})
    for char_name, state in char_states.items():
        relationship = relationship_map.get(char_name, {})
        if isinstance(relationship, dict) and relationship:
            merged_relationship = dict(relationship)
            trend_data = trend_map.get(char_name, {})
            if isinstance(trend_data, dict) and trend_data:
                if trend_data.get("current_trust") is not None:
                    merged_relationship.setdefault(
                        "trust", trend_data.get("current_trust")
                    )
                merged_relationship.setdefault(
                    "trust_history",
                    [
                        int(item)
                        for item in trend_data.get("trust_samples", [])
                        if isinstance(item, int | float)
                    ],
                )
                merged_relationship.setdefault(
                    "relationship_trend",
                    str(trend_data.get("trend", "stable") or "stable"),
                )
            state.relationships[user_name] = merged_relationship
        for summary in memory_map.get(char_name, []):
            relationship_state = state.relationships.setdefault(
                user_name,
                {
                    "entity_type": "user",
                    "history": [],
                    "trust": state.trust_toward_player,
                    "trust_history": [],
                    "interaction_count": 0,
                    "last_summary": "",
                    "relationship_trend": "stable",
                },
            )
            history = [
                str(item).strip()
                for item in relationship_state.get("history", [])
                if str(item).strip()
            ]
            normalized_summary = str(summary).strip()
            if normalized_summary and normalized_summary not in history:
                history.append(normalized_summary)
                relationship_state["history"] = history[-8:]
            if normalized_summary:
                relationship_state["last_summary"] = normalized_summary

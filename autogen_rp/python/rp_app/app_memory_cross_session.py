from typing import Any

from cross_session_memory_policy import (
    append_apply_item,
    empty_cross_session_payload,
    is_cross_session_memory_enabled,
    log_cross_session_report,
    new_injection_report,
)


def load_cross_session_memories(
    *,
    st_module: Any,
    character_names: list[str],
    user_name: str,
    session_manager_cls: Any,
) -> dict[str, Any]:
    session_manager = session_manager_cls()
    exclude_session_id = st_module.session_state.get("session_id")
    indexed_session_count = len(session_manager.list_sessions())

    if not is_cross_session_memory_enabled():
        report = new_injection_report(
            cross_session_memory_enabled=False,
            exclude_session_id=exclude_session_id,
            indexed_session_count=indexed_session_count,
        )
        st_module.session_state["cross_session_injection_report"] = report
        payload = empty_cross_session_payload(character_names)
        payload["indexed_session_count"] = indexed_session_count
        return payload

    report = new_injection_report(
        cross_session_memory_enabled=True,
        exclude_session_id=exclude_session_id,
        indexed_session_count=indexed_session_count,
    )
    st_module.session_state["cross_session_injection_report"] = report

    payload = session_manager.get_cross_session_memories(
        character_names=character_names,
        user_name=user_name,
        exclude_session_id=exclude_session_id,
        injection_report=report,
    )
    report["indexed_session_count"] = payload.get(
        "indexed_session_count", indexed_session_count
    )
    return payload


def apply_cross_session_memories(
    char_states: dict[str, Any],
    cross_session_memories: dict[str, Any],
    user_name: str,
    *,
    st_module: Any | None = None,
) -> None:
    report = (
        st_module.session_state.get("cross_session_injection_report")
        if st_module is not None
        else None
    )
    if not isinstance(report, dict):
        report = None

    if not cross_session_memories.get("_cross_session_enabled", True):
        if report is not None:
            append_apply_item(
                report,
                memory_type="control",
                injection_reason="toggle_disabled_no_apply",
                source_session_id=None,
                target_character=None,
                preview="RP_CROSS_SESSION_MEMORY disabled",
                prompt_destination=[],
            )
            log_cross_session_report(report)
        return

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
            if report is not None:
                append_apply_item(
                    report,
                    memory_type="relationship_snapshot",
                    injection_reason="relationship_snapshot_apply",
                    source_session_id=None,
                    target_character=char_name,
                    preview=(
                        f"merged user relationship trust="
                        f"{merged_relationship.get('trust')}"
                    ),
                    prompt_destination=["PRIVATE STATE"],
                )
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
                if report is not None:
                    append_apply_item(
                        report,
                        memory_type="relationship_history",
                        injection_reason="relationship_history_apply",
                        source_session_id=None,
                        target_character=char_name,
                        preview=normalized_summary,
                        prompt_destination=[
                            "CROSS-SESSION USER MEMORY",
                            "PRIVATE STATE",
                        ],
                    )
            if normalized_summary:
                relationship_state["last_summary"] = normalized_summary

    if report is not None:
        log_cross_session_report(report)

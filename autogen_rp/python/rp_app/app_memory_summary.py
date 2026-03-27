from typing import Any


def build_memory_fact_summary(
    acting_character: str,
    move: dict[str, Any],
) -> str:
    action = str(move.get("action", "") or "").strip()
    dialogue = str(move.get("dialogue", "") or "").strip()
    motivation = (
        move.get("motivation", {}) if isinstance(move.get("motivation"), dict) else {}
    )
    goal = str(motivation.get("goal", "") or "").strip()

    parts: list[str] = []
    if action:
        parts.append(f"{acting_character} {action}")
    else:
        parts.append(f"{acting_character} took a turn in the scene")

    if dialogue:
        parts.append("spoke aloud")

    if goal:
        parts.append(f"while pursuing: {goal}")

    summary = "; ".join(parts).strip()
    if not summary.endswith("."):
        summary += "."
    return summary


def summarize_user_message(user_name: str, user_input: str) -> str:
    content = str(user_input or "").strip()
    if not content:
        return f"{user_name} was present in the scene."
    compact = content[:140] + "..." if len(content) > 140 else content
    return f"{user_name} said or signaled: {compact}"


def extract_user_preferences(
    chat_history: list[dict[str, Any]], user_name: str
) -> list[str]:
    preferences: list[str] = []
    user_name_lower = user_name.lower()
    for message in chat_history:
        if message.get("role") != "user":
            continue
        content = str(message.get("content", "") or "").strip()
        lowered = content.lower()
        if any(
            marker in lowered
            for marker in [
                "i like",
                "i prefer",
                "call me",
                "my name is",
                "i don't like",
                "do not call me",
            ]
        ):
            normalized = content[:160] + "..." if len(content) > 160 else content
            if normalized not in preferences:
                preferences.append(normalized)
    if not preferences and user_name and user_name_lower not in ["you", "traveler"]:
        preferences.append(f"User goes by {user_name}.")
    return preferences[-6:]


def build_memory_buckets(
    *,
    summary: str,
    continuity_manager: Any,
    chat_history: list[dict[str, Any]],
    user_name: str,
) -> dict[str, Any]:
    world_facts: list[str] = []
    if continuity_manager is not None:
        for anchor in continuity_manager.get_scene_canon_anchors(limit=8):
            if getattr(anchor, "category", "") == "world_fact":
                statement = str(getattr(anchor, "statement", "") or "").strip()
                if statement and statement not in world_facts:
                    world_facts.append(statement)
        if continuity_manager.scene_state and continuity_manager.scene_state.location:
            location_fact = (
                f"Recent recurring location: {continuity_manager.scene_state.location}."
            )
            if location_fact not in world_facts:
                world_facts.append(location_fact)

    return {
        "session_summary": summary,
        "persistent_world_facts": world_facts[:8],
        "user_preferences": extract_user_preferences(chat_history, user_name),
    }

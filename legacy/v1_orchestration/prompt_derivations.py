"""Shared derivations for character turn prompts (relationship ordering, priority ladder).

Extracted so `runtime_packets` can reconstruct prompt-input bundles without importing
`app_turn_prompting` (avoids circular imports).
"""

from __future__ import annotations

from typing import Any


def _role_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_scene_holder_role(role_name: str) -> bool:
    role = _role_text(role_name)
    return any(
        token in role
        for token in (
            "protector",
            "dominator",
            "holder",
            "host",
            "captor",
            "interrogator",
            "caretaker",
            "guardian",
            "handler",
            "owner",
            "boss",
            "warden",
        )
    )


def _is_scene_protagonist_role(role_name: str) -> bool:
    role = _role_text(role_name)
    return any(
        token in role
        for token in (
            "protagonist",
            "recovering",
            "patient",
            "guest",
            "subject",
            "captive",
            "ward",
            "charge",
            "outsider",
            "newcomer",
            "supplicant",
            "target",
        )
    )


def select_relationship_prompt_names(
    *,
    char_name: str,
    cast: list[str],
    my_scene_role: dict[str, Any],
    scene_roles: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    role_map = {
        str(item.get("character", "") or "").strip(): item
        for item in scene_roles
        if str(item.get("character", "") or "").strip()
    }
    my_role = _role_text(my_scene_role.get("role", ""))
    my_is_holder = _is_scene_holder_role(my_role)
    my_is_protagonist = _is_scene_protagonist_role(my_role)

    prioritized: list[tuple[tuple[int, int, str], str]] = []
    for index, target_name in enumerate(cast):
        if not target_name or target_name == char_name:
            continue
        target_role_data = role_map.get(target_name, {})
        target_role = _role_text(target_role_data.get("role", ""))
        target_is_holder = _is_scene_holder_role(target_role)
        target_is_protagonist = _is_scene_protagonist_role(target_role)
        target_authority = 0 if _role_text(target_role_data.get("authority", "")) else 1
        target_presence = (
            0
            if _role_text(target_role_data.get("presence_constraint", ""))
            == "must_remain"
            else 1
        )

        base_priority = 6
        if my_is_holder and target_is_protagonist:
            base_priority = 0
        elif my_is_protagonist and target_is_holder:
            base_priority = 0
        elif target_is_holder:
            base_priority = 1
        elif target_is_protagonist:
            base_priority = 2
        elif target_authority == 0:
            base_priority = 3
        elif target_presence == 0:
            base_priority = 4

        prioritized.append(
            ((base_priority, target_authority, f"{index:04d}"), target_name)
        )

    ordered_names = [name for _, name in sorted(prioritized, key=lambda item: item[0])]
    focus_names = ordered_names[:2]
    secondary_names = [
        name for name in cast if name not in focus_names and name != char_name
    ]
    return focus_names, secondary_names


def build_priority_ladder(
    *,
    state: Any,
    active_issues: list[dict[str, Any]],
) -> list[str]:
    ladder: list[str] = []
    seen: set[str] = set()

    persistent_objective = (
        str(getattr(state, "current_objective", "") or "").strip()
        if state is not None
        else ""
    )
    if persistent_objective:
        entry = f"Persistent obligation: {persistent_objective}"
        if entry not in seen:
            ladder.append(entry)
            seen.add(entry)

    persistent_tactic = (
        str(getattr(state, "short_term_tactic", "") or "").strip()
        if state is not None
        else ""
    )
    if persistent_tactic:
        entry = f"Preferred execution stance: {persistent_tactic}"
        if entry not in seen:
            ladder.append(entry)
            seen.add(entry)

    local_task_goal = (
        str(getattr(state, "local_task_goal", "") or "").strip()
        if state is not None
        else ""
    )
    if local_task_goal and local_task_goal != persistent_objective:
        entry = (
            f"Local subtask only if it serves a higher obligation: {local_task_goal}"
        )
        if entry not in seen:
            ladder.append(entry)
            seen.add(entry)

    local_task_tactic = (
        str(getattr(state, "local_task_tactic", "") or "").strip()
        if state is not None
        else ""
    )
    if local_task_tactic and local_task_tactic != persistent_tactic:
        entry = f"Local execution detail: {local_task_tactic}"
        if entry not in seen:
            ladder.append(entry)
            seen.add(entry)

    for issue in active_issues:
        description = str(
            issue.get("description", "") or issue.get("summary", "") or ""
        ).strip()
        if not description:
            continue
        entry = (
            "Active issue pressure only if it materially blocks, invalidates, or supersedes your current line: "
            f"{description}"
        )
        if entry not in seen:
            ladder.append(entry)
            seen.add(entry)

    return ladder

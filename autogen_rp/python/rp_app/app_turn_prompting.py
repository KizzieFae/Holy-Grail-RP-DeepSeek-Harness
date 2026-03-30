import logging
from typing import Any, Callable

from beat_shift_state import build_character_beat_shift_suffix, is_pending_beat_shift_active
from progression_advisory import (
    PROGRESSION_CHARACTER_SUFFIX,
    should_append_progression_character_suffix,
    sync_progression_advisory_for_prompts,
)

_progression_log = logging.getLogger("rp_app.progression_advisory")
from offstage_prompt_filter import (
    filter_dialogue_for_offstage_character,
    filter_structured_moves_for_offstage_character,
)
from scene_grounding import format_character_grounding_section


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


def _select_relationship_prompt_names(
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


def _build_priority_ladder(
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


def build_recent_dialogue_history(
    *,
    chat_history: list[dict[str, Any]],
    get_character_display_name_fn,
    limit: int,
) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for message in chat_history[-limit:]:
        if message.get("role") == "system":
            continue
        raw_speaker = str(message.get("speaker", "Unknown") or "Unknown")
        history.append(
            {
                "role": str(message.get("role", "assistant") or "assistant"),
                "speaker": get_character_display_name_fn(raw_speaker),
                "content": str(message.get("content", "") or ""),
            }
        )
    return history


def build_character_turn_prompt(
    *,
    st_module: Any,
    char_name: str,
    user_name: str,
    trigger_text: str,
    director_decision: dict[str, Any],
    enforce_must_remain_presence_fn,
    get_orchestration_state_fn,
    get_continuity_manager_fn,
    build_recent_dialogue_history_fn,
    serialize_events_for_prompt_fn,
    serialize_canon_anchors_for_prompt_fn,
    serialize_summary_blocks_for_prompt_fn,
    build_summary_block_audit_metadata_fn,
    build_scene_role_prompt_context_fn,
    build_character_turn_prompt_text_fn,
    prompt_structured_move_limit: int,
    get_character_display_name_fn: Callable[[str], str],
):
    enforce_must_remain_presence_fn()
    orchestration_state = get_orchestration_state_fn()
    chat_history = st_module.session_state.get("chat_history", [])
    state_manager = st_module.session_state.get("character_state_manager")
    continuity_manager = get_continuity_manager_fn()
    progression_advisory_snapshot = sync_progression_advisory_for_prompts(
        orchestration_state=orchestration_state,
        continuity_manager=continuity_manager,
    )
    state = state_manager.get_state(char_name) if state_manager else None
    recent_moves = orchestration_state.get("recent_structured_moves", [])[
        -prompt_structured_move_limit:
    ]
    cross_session_memories = st_module.session_state.get("cross_session_memories", {})
    continuity_context = (
        continuity_manager.get_character_context(char_name)
        if continuity_manager is not None
        else None
    )
    scene_state = (
        continuity_context["scene_state"].to_dict()
        if continuity_context is not None
        else orchestration_state.get("scene_state", {})
    )
    recent_dialogue = build_recent_dialogue_history_fn(chat_history)
    offstage_names = [
        str(n)
        for n in (scene_state.get("offstage_characters") or [])
        if str(n or "").strip()
    ]
    if char_name in offstage_names:
        recent_dialogue = filter_dialogue_for_offstage_character(
            recent_dialogue,
            char_name=char_name,
            get_character_display_name_fn=get_character_display_name_fn,
        )
        recent_moves = filter_structured_moves_for_offstage_character(
            recent_moves, char_name
        )
    active_issues = (
        [issue.to_dict() for issue in continuity_context.get("active_issues", [])]
        if continuity_context is not None
        else []
    )
    recent_public_events = (
        serialize_events_for_prompt_fn(
            continuity_context.get("recent_events", []),
            character_name=char_name,
        )
        if continuity_context is not None
        else []
    )
    my_interpretations = (
        [item.to_dict() for item in continuity_context.get("my_interpretations", [])]
        if continuity_context is not None
        else []
    )
    canon_anchors = (
        serialize_canon_anchors_for_prompt_fn(
            continuity_context.get("canon_anchors", [])
        )
        if continuity_context is not None
        else []
    )
    selected_summary_objects = (
        continuity_context.get("summary_blocks", [])
        if continuity_context is not None
        else []
    )
    summary_blocks = (
        serialize_summary_blocks_for_prompt_fn(selected_summary_objects)
        if continuity_context is not None
        else []
    )
    summary_block_audit = build_summary_block_audit_metadata_fn(
        generated_blocks=(
            continuity_manager.summary_blocks[:]
            if continuity_manager is not None
            else []
        ),
        available_blocks=[],
        selected_blocks=selected_summary_objects,
        skipped_reason=(
            "Continuity manager unavailable"
            if continuity_manager is None
            else "No summary blocks generated yet"
        ),
        summary_generation_eligible=(
            continuity_manager is not None
            and continuity_manager.summary_interval > 0
            and continuity_manager.turn_counter >= continuity_manager.summary_interval
        ),
    )
    if continuity_manager is not None and continuity_context is not None:
        relevant_issue_ids = [
            str(issue.issue_id)
            for issue in continuity_context.get("active_issues", [])
            if hasattr(issue, "issue_id")
        ]
        available_summary_objects = continuity_manager.retrieve_summary_blocks(
            participants=[char_name],
            issue_ids=relevant_issue_ids,
            location=(
                continuity_manager.scene_state.location
                if continuity_manager.scene_state is not None
                else None
            ),
            limit=0,
        )
        fallback_used = bool(selected_summary_objects) and not bool(
            available_summary_objects
        )
        summary_block_audit = build_summary_block_audit_metadata_fn(
            generated_blocks=continuity_manager.summary_blocks[:],
            available_blocks=available_summary_objects,
            selected_blocks=selected_summary_objects,
            selection_reason=(
                "fallback to recent summary blocks after filtered retrieval returned none"
                if fallback_used and selected_summary_objects
                else (
                    "deterministic retrieval for character prompt"
                    if selected_summary_objects
                    else ""
                )
            ),
            skipped_reason=(
                "No summary blocks generated yet"
                if not continuity_manager.summary_blocks
                else (
                    "No summary blocks matched character retrieval filters"
                    if not selected_summary_objects
                    else ""
                )
            ),
            fallback_used=fallback_used,
            summary_generation_eligible=(
                continuity_manager.summary_interval > 0
                and continuity_manager.turn_counter
                >= continuity_manager.summary_interval
            ),
        )
    cross_session_user_memories = (
        cross_session_memories.get("character_user_memories", {}).get(char_name, [])
        if isinstance(cross_session_memories, dict)
        else []
    )
    cross_session_world_facts = (
        cross_session_memories.get("persistent_world_facts", [])
        if isinstance(cross_session_memories, dict)
        else []
    )
    user_preferences = (
        cross_session_memories.get("user_preferences", [])
        if isinstance(cross_session_memories, dict)
        else []
    )
    cast = [
        name for name in scene_state.get("present_characters", []) if name != char_name
    ]
    if not cast:
        cast = [
            agent.name
            for agent in st_module.session_state.get("characters", [])
            if agent.name != char_name
        ]
    scene_roles = build_scene_role_prompt_context_fn(
        scene_state,
        [char_name] + cast,
    )
    my_scene_role = next(
        (
            item
            for item in scene_roles
            if str(item.get("character", "") or "").strip() == char_name
        ),
        {},
    )
    scene_template_context = {
        "template_id": str(scene_state.get("scene_template_id", "") or ""),
        "premise": str(scene_state.get("scene_premise", "") or ""),
        "location_entry_slots": [
            str(item)
            for item in scene_state.get("location_entry_slots", [])
            if str(item or "").strip()
        ],
    }
    relationship_focus_names, relationship_secondary_names = (
        _select_relationship_prompt_names(
            char_name=char_name,
            cast=cast,
            my_scene_role=my_scene_role,
            scene_roles=scene_roles,
        )
    )
    actionable_statuses = {"active", "escalating", ""}
    actionable_issues: list[dict[str, Any]] = []
    for issue in active_issues:
        if not isinstance(issue, dict):
            continue
        status = str(issue.get("status", "") or "").strip().lower()
        if status in actionable_statuses:
            actionable_issues.append(issue)
    priority_ladder = _build_priority_ladder(
        state=state,
        active_issues=actionable_issues,
    )
    state_context = (
        state.to_prompt_context(
            relationship_focus_names=relationship_focus_names,
            relationship_secondary_names=relationship_secondary_names,
        )
        if state
        else "No private state available."
    )
    grounding_section = format_character_grounding_section(
        st_module.session_state.get("scene_grounding")
    )
    prompt_text = build_character_turn_prompt_text_fn(
        char_name=char_name,
        user_name=user_name,
        trigger_text=trigger_text,
        director_decision=director_decision,
        scene_state=scene_state,
        scene_template_context=scene_template_context,
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
        recent_moves=recent_moves,
        recent_dialogue=recent_dialogue,
        active_issues=active_issues,
        priority_ladder=priority_ladder,
        summary_blocks=summary_blocks,
        recent_public_events=recent_public_events,
        cross_session_user_memories=cross_session_user_memories,
        cross_session_world_facts=cross_session_world_facts,
        user_preferences=user_preferences,
        my_interpretations=my_interpretations,
        canon_anchors=canon_anchors,
        state_context=state_context,
        cast=cast,
        scene_grounding_section=grounding_section,
    )
    beat_shift_active_here = is_pending_beat_shift_active(orchestration_state)
    if beat_shift_active_here:
        prompt_text += build_character_beat_shift_suffix(trigger_text=trigger_text)
    _pp = str(progression_advisory_snapshot.get("progression_pressure") or "low")
    if should_append_progression_character_suffix(
        progression_pressure=_pp,
        beat_shift_active=beat_shift_active_here,
    ):
        prompt_text += PROGRESSION_CHARACTER_SUFFIX
        _progression_log.info(
            "[progression_advisory] character prompt suffix injected pressure=%s "
            "beat_shift_active=%s",
            _pp,
            beat_shift_active_here,
        )
    return (prompt_text, summary_block_audit)


def build_recent_scene_context(
    *,
    chat_history: list[dict[str, Any]],
    orchestration_state: dict[str, Any],
    get_continuity_manager_fn,
    build_recent_dialogue_history_fn,
    build_recent_scene_context_impl_fn,
    limit: int,
) -> tuple[str, dict[str, Any]]:
    return build_recent_scene_context_impl_fn(
        chat_history=chat_history,
        orchestration_state=orchestration_state,
        continuity_manager=get_continuity_manager_fn(),
        build_recent_dialogue_history_fn=build_recent_dialogue_history_fn,
        limit=limit,
    )

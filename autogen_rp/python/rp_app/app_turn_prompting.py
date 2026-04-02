import logging
import os
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
from perception_audibility import (
    filter_structured_move_for_viewer,
    player_text_for_character_viewer,
)
from memory_layer.retrieval import build_character_state_context_for_prompt
from scene_grounding import format_character_grounding_section

from prompt_derivations import (
    build_priority_ladder,
    select_relationship_prompt_names,
)


def _packet_shadow_compare_enabled() -> bool:
    v = os.environ.get("RP_PACKET_SHADOW_COMPARE", "")
    return v.strip().lower() in ("1", "true", "yes")


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
    prompt_dialogue_history_limit: int,
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
    raw_moves = orchestration_state.get("recent_structured_moves", [])[
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
    present_for_moves = scene_state.get("present_characters") or [
        str(a.name)
        for a in st_module.session_state.get("characters", [])
        if getattr(a, "name", None)
    ]
    recent_moves = [
        filter_structured_move_for_viewer(
            dict(m),
            viewer_character_name=char_name,
            present_characters=list(present_for_moves),
        )
        for m in raw_moves
        if isinstance(m, dict)
    ]
    recent_dialogue = build_recent_dialogue_history_fn(
        chat_history,
        limit=prompt_dialogue_history_limit,
        viewer_character_name=char_name,
    )
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
        select_relationship_prompt_names(
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
    priority_ladder = build_priority_ladder(
        state=state,
        active_issues=actionable_issues,
    )
    # state_context contract: single string from memory_layer + identity; passed unchanged
    # to prompt_builders.build_character_turn_prompt (see autogen_rp/docs/architecture.md).
    state_context = (
        build_character_state_context_for_prompt(
            state=state,
            relationship_focus_names=relationship_focus_names,
            relationship_secondary_names=relationship_secondary_names,
        )
        if state
        else "No private state available."
    )
    grounding_section = format_character_grounding_section(
        st_module.session_state.get("scene_grounding")
    )
    filtered_trigger = player_text_for_character_viewer(
        raw_text=trigger_text,
        viewer_character_name=char_name,
        present_characters=list(present_for_moves),
        user_display_name=user_name,
        get_character_display_name_fn=get_character_display_name_fn,
    )
    if _packet_shadow_compare_enabled():
        from runtime_packets import (
            build_live_character_prompt_input_bundle,
            build_runtime_character_packet,
            build_runtime_scene_packet,
            compare_character_prompt_bundles,
            debug_bundle_mismatch_strings,
            reconstruct_character_prompt_input_bundle,
        )

        session_agent_names = [
            str(getattr(a, "name", "") or "").strip()
            for a in st_module.session_state.get("characters", [])
            if str(getattr(a, "name", "") or "").strip()
        ]
        live_bundle = build_live_character_prompt_input_bundle(
            char_name=char_name,
            user_name=user_name,
            trigger_text=filtered_trigger,
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
        scene_packet = build_runtime_scene_packet(
            scene_state,
            st_module.session_state,
        )
        char_packet = build_runtime_character_packet(
            scene_state=scene_state,
            char_name=char_name,
            user_name=user_name,
            trigger_text=filtered_trigger,
            director_decision=director_decision,
            session_agent_names=session_agent_names,
            recent_moves=recent_moves,
            recent_dialogue=recent_dialogue,
            active_issues=active_issues,
            summary_blocks=summary_blocks,
            recent_public_events=recent_public_events,
            cross_session_user_memories=cross_session_user_memories,
            cross_session_world_facts=cross_session_world_facts,
            user_preferences=user_preferences,
            my_interpretations=my_interpretations,
            canon_anchors=canon_anchors,
            scene_grounding_section=grounding_section,
        )
        recon_bundle = reconstruct_character_prompt_input_bundle(
            scene_packet,
            char_packet,
            state=state,
        )
        ok, detail = compare_character_prompt_bundles(live_bundle, recon_bundle)
        if not ok:
            _plog = logging.getLogger("rp_app.packet_shadow")
            _plog.warning(
                "packet shadow structured mismatch: %s", detail, exc_info=False
            )
            _plog.debug(
                "packet shadow string diff (debug):\n%s",
                debug_bundle_mismatch_strings(live_bundle, recon_bundle),
            )

    prompt_text = build_character_turn_prompt_text_fn(
        char_name=char_name,
        user_name=user_name,
        trigger_text=filtered_trigger,
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
        prompt_text += build_character_beat_shift_suffix(
            trigger_text=filtered_trigger
        )
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

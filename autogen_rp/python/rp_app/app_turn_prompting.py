import logging
import os
from typing import Any, Callable

from arch_quality_variants import arch_quality_b_no_character_progression_suffix
from beat_shift_state import build_character_beat_shift_suffix, is_pending_beat_shift_active
from progression_advisory import (
    PROGRESSION_CHARACTER_SUFFIX,
    should_append_progression_character_suffix,
    sync_progression_advisory_for_prompts,
)

_progression_log = logging.getLogger("rp_app.progression_advisory")
_episodic_merge_log = logging.getLogger("rp_app.episodic_prompt")
from offstage_prompt_filter import (
    filter_dialogue_for_offstage_character,
    filter_structured_moves_for_offstage_character,
)
from perception_audibility import (
    filter_structured_move_for_viewer,
    player_text_for_character_viewer,
)
from memory_layer.retrieval import build_character_state_context_for_prompt
from scene_grounding import (
    format_character_binding_constraints_section,
    format_character_grounding_section,
)

from prompt_derivations import (
    build_priority_ladder,
    select_relationship_prompt_names,
)
from episodic_memory_cache import get_or_compile_episodic_candidate_pool
from episodic_memory_inputs import continuity_sequences_for_episodic
from episodic_memory_prompt import is_episodic_memory_enabled
from episodic_memory_select import select_episodic_items_for_character
from retrieved_context_select import (
    get_index_path_from_env,
    load_authored_retrieval_index,
    log_retrieval_if_active,
    merge_retrieved_context_with_episodic,
    select_retrieved_context_bundle,
    structured_prompt_id_sets_for_episodic_suppression,
)
from runtime_packets import format_retrieved_context_for_prompt


def _prompt_dedup_texts_for_retrieval(
    scene_state: dict[str, Any],
    canon_anchors: list[dict[str, Any]],
    summary_blocks: list[dict[str, Any]],
) -> tuple[str, ...]:
    out: list[str] = []
    for key in ("scene_premise", "opening_description"):
        v = scene_state.get(key)
        if v is not None and str(v).strip():
            out.append(str(v))
    for ca in canon_anchors:
        if isinstance(ca, dict):
            for v in ca.values():
                if isinstance(v, str) and v.strip():
                    out.append(v)
    for sb in summary_blocks:
        if isinstance(sb, dict):
            for v in sb.values():
                if isinstance(v, str) and v.strip():
                    out.append(v)
    return tuple(out)


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
    _sg = st_module.session_state.get("scene_grounding")
    grounding_section = format_character_grounding_section(_sg)
    binding_constraints_section = format_character_binding_constraints_section(_sg)
    filtered_trigger = player_text_for_character_viewer(
        raw_text=trigger_text,
        viewer_character_name=char_name,
        present_characters=list(present_for_moves),
        user_display_name=user_name,
        get_character_display_name_fn=get_character_display_name_fn,
    )
    _retrieval_index = load_authored_retrieval_index(get_index_path_from_env())
    _dedup_texts = _prompt_dedup_texts_for_retrieval(
        scene_state, canon_anchors, summary_blocks
    )
    _tid = str(scene_state.get("scene_template_id", "") or "")
    _rf = tuple(sorted(relationship_focus_names))
    _cast_t = tuple(sorted(cast))
    if is_episodic_memory_enabled() and continuity_manager is not None:
        pe, itp, isu, ca = continuity_sequences_for_episodic(continuity_manager)
        pool = get_or_compile_episodic_candidate_pool(
            st_module.session_state,
            public_events=pe,
            interpretations=itp,
            issues=isu,
            canon_anchors=ca,
        )
        _sup_issue_ids, _sup_evt_ids, _sup_int_ids = (
            structured_prompt_id_sets_for_episodic_suppression(
                active_issues=active_issues,
                recent_public_events=recent_public_events,
                my_interpretations=my_interpretations,
            )
        )
        episodic_selected = select_episodic_items_for_character(
            pool,
            char_name,
            structured_prompt_issue_ids=_sup_issue_ids,
            structured_prompt_public_event_ids=_sup_evt_ids,
            structured_prompt_interpretation_ids=_sup_int_ids,
        )
        retrieved_bundle = merge_retrieved_context_with_episodic(
            index=_retrieval_index,
            char_name=char_name,
            scene_template_id=_tid,
            relationship_focus_names=_rf,
            cast=_cast_t,
            dedup_against_texts=_dedup_texts,
            episodic_items=episodic_selected,
            structured_prompt_issue_ids=_sup_issue_ids,
            structured_prompt_public_event_ids=_sup_evt_ids,
            structured_prompt_interpretation_ids=_sup_int_ids,
        )
        _episodic_merge_log.info(
            "episodic merge char=%s pool_len=%d selected_len=%d bundle_items=%d",
            char_name,
            len(pool),
            len(episodic_selected),
            len(retrieved_bundle.items),
        )
    else:
        retrieved_bundle = select_retrieved_context_bundle(
            index=_retrieval_index,
            char_name=char_name,
            scene_template_id=_tid,
            relationship_focus_names=_rf,
            cast=_cast_t,
            dedup_against_texts=_dedup_texts,
        )
    log_retrieval_if_active(retrieved_bundle, char_name=char_name)
    retrieved_context_section = format_retrieved_context_for_prompt(retrieved_bundle)

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
            scene_binding_constraints_section=binding_constraints_section,
            retrieved_context_section=retrieved_context_section,
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
            scene_binding_constraints_section=binding_constraints_section,
            retrieved=retrieved_bundle,
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
        scene_binding_constraints_section=binding_constraints_section,
        retrieved_context_section=retrieved_context_section,
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
    ) and not arch_quality_b_no_character_progression_suffix(st_module):
        prompt_text += PROGRESSION_CHARACTER_SUFFIX
        _progression_log.info(
            "[progression_advisory] character prompt suffix injected pressure=%s "
            "beat_shift_active=%s",
            _pp,
            beat_shift_active_here,
        )
    prompt_layer_audit: dict[str, Any] = {
        **summary_block_audit,
        "has_binding_constraints": bool(
            str(binding_constraints_section or "").strip()
        ),
        "scene_binding_constraints_section": binding_constraints_section or "",
    }
    return (prompt_text, prompt_layer_audit)


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

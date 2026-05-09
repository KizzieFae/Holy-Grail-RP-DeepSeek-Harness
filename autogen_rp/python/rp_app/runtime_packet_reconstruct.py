"""Reconstruct live prompt bundle from packets + CharacterState (Issue #166)."""

from __future__ import annotations

from typing import Any, Callable

from memory_layer.retrieval import build_character_state_context_for_prompt
from prompt_builders import (
    build_cast_and_scene_role_participants,
    build_scene_role_prompt_context,
)
from prompt_derivations import build_priority_ladder, select_relationship_prompt_names
from runtime_packet_formatting import format_retrieved_context_for_prompt
from runtime_packet_prompt_bundle import build_live_character_prompt_input_bundle
from runtime_packet_scene_split import merge_scene_state_from_packets
from runtime_packet_types import RuntimeCharacterPacket, RuntimeScenePacket


def reconstruct_character_prompt_input_bundle(
    scene_packet: RuntimeScenePacket,
    char_packet: RuntimeCharacterPacket,
    *,
    state: Any,
    get_character_display_name_fn: Callable[[str], str],
) -> dict[str, Any]:
    """Rebuild the live prompt-input bundle from packets + authoritative character state."""
    char_name = char_packet.character_name
    proj = char_packet.projection
    merged = merge_scene_state_from_packets(scene_packet, proj)

    present_for_moves = merged.get("present_characters") or proj.session_agent_names
    present_list = [
        str(x).strip()
        for x in (merged.get("present_characters") or [])
        if str(x or "").strip()
    ]
    session_names = [
        str(x).strip() for x in (proj.session_agent_names or []) if str(x or "").strip()
    ]
    cast, role_participants = build_cast_and_scene_role_participants(
        char_name,
        present_list if present_list else None,
        session_names,
        get_character_display_name_fn,
    )

    scene_template_context = {
        "template_id": str(merged.get("scene_template_id", "") or ""),
        "premise": str(merged.get("scene_premise", "") or ""),
        "location_entry_slots": [
            str(item)
            for item in merged.get("location_entry_slots", [])
            if str(item or "").strip()
        ],
    }
    scene_roles = build_scene_role_prompt_context(
        merged,
        role_participants,
    )
    my_scene_role = next(
        (
            item
            for item in scene_roles
            if str(item.get("character", "") or "").strip() == char_name
        ),
        {},
    )
    actionable_statuses = {"active", "escalating", ""}
    actionable_issues: list[dict[str, Any]] = []
    for issue in proj.active_issues:
        if not isinstance(issue, dict):
            continue
        status = str(issue.get("status", "") or "").strip().lower()
        if status in actionable_statuses:
            actionable_issues.append(issue)
    priority_ladder = build_priority_ladder(
        state=state,
        active_issues=actionable_issues,
    )
    relationship_focus_names, relationship_secondary_names = (
        select_relationship_prompt_names(
            char_name=char_name,
            cast=cast,
            my_scene_role=my_scene_role,
            scene_roles=scene_roles,
        )
    )
    state_context = (
        build_character_state_context_for_prompt(
            state=state,
            relationship_focus_names=relationship_focus_names,
            relationship_secondary_names=relationship_secondary_names,
        )
        if state
        else "No private state available."
    )

    return build_live_character_prompt_input_bundle(
        char_name=char_name,
        user_name=proj.user_name,
        trigger_text=proj.trigger_text,
        director_decision=proj.director_decision,
        scene_state=merged,
        scene_template_context=scene_template_context,
        my_scene_role=my_scene_role,
        scene_roles=scene_roles,
        recent_moves=proj.recent_moves,
        recent_dialogue=proj.recent_dialogue,
        active_issues=proj.active_issues,
        priority_ladder=priority_ladder,
        summary_blocks=proj.summary_blocks,
        recent_public_events=proj.recent_public_events,
        cross_session_user_memories=proj.cross_session_user_memories,
        cross_session_world_facts=proj.cross_session_world_facts,
        user_preferences=proj.user_preferences,
        my_interpretations=proj.my_interpretations,
        canon_anchors=proj.canon_anchors,
        state_context=state_context,
        cast=cast,
        scene_grounding_section=proj.scene_grounding_section,
        scene_binding_constraints_section=proj.scene_binding_constraints_section,
        retrieved_context_section=format_retrieved_context_for_prompt(char_packet.retrieved),
    )

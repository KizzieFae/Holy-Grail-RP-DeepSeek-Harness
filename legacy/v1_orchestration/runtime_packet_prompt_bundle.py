"""Live prompt kwargs / assembly bridges (Issue #166)."""

from __future__ import annotations

from typing import Any

from runtime_packet_build import (
    build_runtime_character_packet,
    build_runtime_scene_packet,
)
from runtime_packet_formatting import format_retrieved_context_for_prompt
from runtime_packet_types import (
    CharacterPromptInputAssembly,
    RuntimeCharacterPacket,
    RuntimeScenePacket,
)


def build_live_character_prompt_input_bundle(
    *,
    char_name: str,
    user_name: str,
    trigger_text: str,
    director_decision: dict[str, Any],
    scene_state: dict[str, Any],
    scene_template_context: dict[str, Any],
    my_scene_role: dict[str, Any],
    scene_roles: list[dict[str, Any]],
    recent_moves: list[dict[str, Any]],
    recent_dialogue: list[dict[str, Any]],
    active_issues: list[dict[str, Any]],
    priority_ladder: list[str],
    summary_blocks: list[dict[str, Any]],
    recent_public_events: list[dict[str, Any]],
    cross_session_user_memories: list[Any],
    cross_session_world_facts: list[Any],
    user_preferences: list[Any],
    my_interpretations: list[dict[str, Any]],
    canon_anchors: list[dict[str, Any]],
    state_context: str,
    cast: list[str],
    scene_grounding_section: str = "",
    scene_binding_constraints_section: str = "",
    retrieved_context_section: str = "",
) -> dict[str, Any]:
    """Normalized kwargs dict for `prompt_builders.build_character_turn_prompt` (structured compare)."""
    return {
        "char_name": char_name,
        "user_name": user_name,
        "trigger_text": trigger_text,
        "director_decision": dict(director_decision),
        "scene_state": dict(scene_state),
        "scene_template_context": dict(scene_template_context),
        "my_scene_role": dict(my_scene_role),
        "scene_roles": [dict(x) if isinstance(x, dict) else x for x in scene_roles],
        "recent_moves": list(recent_moves),
        "recent_dialogue": list(recent_dialogue),
        "active_issues": list(active_issues),
        "priority_ladder": list(priority_ladder),
        "summary_blocks": list(summary_blocks),
        "recent_public_events": list(recent_public_events),
        "cross_session_user_memories": list(cross_session_user_memories),
        "cross_session_world_facts": list(cross_session_world_facts),
        "user_preferences": list(user_preferences),
        "my_interpretations": list(my_interpretations),
        "canon_anchors": list(canon_anchors),
        "state_context": str(state_context),
        "cast": list(cast),
        "scene_grounding_section": str(scene_grounding_section or ""),
        "scene_binding_constraints_section": str(
            scene_binding_constraints_section or ""
        ),
        "retrieved_context_section": str(retrieved_context_section or ""),
    }


def live_bundle_from_character_prompt_assembly(
    asm: CharacterPromptInputAssembly,
) -> dict[str, Any]:
    """Kwargs dict for ``build_character_turn_prompt`` / bundle compare (from assembly only)."""
    return build_live_character_prompt_input_bundle(
        char_name=asm.char_name,
        user_name=asm.user_name,
        trigger_text=asm.trigger_text,
        director_decision=asm.director_decision,
        scene_state=asm.scene_state,
        scene_template_context=asm.scene_template_context,
        my_scene_role=asm.my_scene_role,
        scene_roles=asm.scene_roles,
        recent_moves=asm.recent_moves,
        recent_dialogue=asm.recent_dialogue,
        active_issues=asm.active_issues,
        priority_ladder=asm.priority_ladder,
        summary_blocks=asm.summary_blocks,
        recent_public_events=asm.recent_public_events,
        cross_session_user_memories=asm.cross_session_user_memories,
        cross_session_world_facts=asm.cross_session_world_facts,
        user_preferences=asm.user_preferences,
        my_interpretations=asm.my_interpretations,
        canon_anchors=asm.canon_anchors,
        state_context=asm.state_context,
        cast=asm.cast,
        scene_grounding_section=asm.scene_grounding_section,
        scene_binding_constraints_section=asm.scene_binding_constraints_section,
        retrieved_context_section=format_retrieved_context_for_prompt(asm.retrieved_bundle),
    )


def runtime_packets_from_character_prompt_assembly(
    asm: CharacterPromptInputAssembly,
) -> tuple[RuntimeScenePacket, RuntimeCharacterPacket]:
    """Build scene + character packets from the same assembly as the live bundle."""
    scene_packet = build_runtime_scene_packet(asm.scene_state, asm.session_state)
    char_packet = build_runtime_character_packet(
        scene_state=asm.scene_state,
        char_name=asm.char_name,
        user_name=asm.user_name,
        trigger_text=asm.trigger_text,
        director_decision=asm.director_decision,
        session_agent_names=asm.session_agent_names,
        recent_moves=asm.recent_moves,
        recent_dialogue=asm.recent_dialogue,
        active_issues=asm.active_issues,
        summary_blocks=asm.summary_blocks,
        recent_public_events=asm.recent_public_events,
        cross_session_user_memories=asm.cross_session_user_memories,
        cross_session_world_facts=asm.cross_session_world_facts,
        user_preferences=asm.user_preferences,
        my_interpretations=asm.my_interpretations,
        canon_anchors=asm.canon_anchors,
        scene_grounding_section=asm.scene_grounding_section,
        scene_binding_constraints_section=asm.scene_binding_constraints_section,
        retrieved=asm.retrieved_bundle,
    )
    return scene_packet, char_packet

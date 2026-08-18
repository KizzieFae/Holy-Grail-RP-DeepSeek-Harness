"""Character turn: `CharacterPromptInputAssembly`, live kwargs bundle, optional packet shadow compare (logging only)."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

from runtime_packets import (
    CharacterPromptInputAssembly,
    RetrievedContextBundle,
    compare_character_prompt_bundles,
    debug_bundle_mismatch_strings,
    live_bundle_from_character_prompt_assembly,
    reconstruct_character_prompt_input_bundle,
    runtime_packets_from_character_prompt_assembly,
)


def _packet_shadow_compare_enabled() -> bool:
    v = os.environ.get("RP_PACKET_SHADOW_COMPARE", "")
    return v.strip().lower() in ("1", "true", "yes")


def build_character_prompt_kwargs_and_assembly(
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
    scene_grounding_section: str,
    scene_binding_constraints_section: str,
    retrieved_bundle: RetrievedContextBundle,
    session_agent_names: list[str],
    session_state: Any,
) -> tuple[dict[str, Any], CharacterPromptInputAssembly]:
    assembly = CharacterPromptInputAssembly(
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
        scene_grounding_section=scene_grounding_section,
        scene_binding_constraints_section=scene_binding_constraints_section,
        retrieved_bundle=retrieved_bundle,
        session_agent_names=session_agent_names,
        session_state=session_state,
    )
    character_prompt_kwargs = live_bundle_from_character_prompt_assembly(assembly)
    return character_prompt_kwargs, assembly


def run_packet_shadow_compare_if_enabled(
    *,
    character_prompt_kwargs: dict[str, Any],
    assembly: CharacterPromptInputAssembly,
    state: Any,
    get_character_display_name_fn: Callable[[str], str],
    build_character_turn_prompt_text_fn: Callable[..., Any],
) -> None:
    if not _packet_shadow_compare_enabled():
        return
    scene_packet, char_packet = runtime_packets_from_character_prompt_assembly(assembly)
    recon_bundle = reconstruct_character_prompt_input_bundle(
        scene_packet,
        char_packet,
        state=state,
        get_character_display_name_fn=get_character_display_name_fn,
    )
    ok, detail = compare_character_prompt_bundles(character_prompt_kwargs, recon_bundle)
    _plog = logging.getLogger("rp_app.packet_shadow")
    if not ok:
        _plog.warning("packet shadow structured mismatch: %s", detail, exc_info=False)
        _plog.debug(
            "packet shadow string diff (debug):\n%s",
            debug_bundle_mismatch_strings(character_prompt_kwargs, recon_bundle),
        )
    else:
        core_live = build_character_turn_prompt_text_fn(**character_prompt_kwargs)
        core_recon = build_character_turn_prompt_text_fn(**recon_bundle)
        if core_live != core_recon:
            _plog.debug(
                "packet shadow core prompt text mismatch (bundle matched); "
                "len live=%d recon=%d",
                len(core_live),
                len(core_recon),
            )

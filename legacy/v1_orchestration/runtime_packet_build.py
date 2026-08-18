"""Build RuntimeScenePacket / RuntimeCharacterPacket (Issue #166)."""

from __future__ import annotations

from typing import Any

from runtime_packet_scene_split import split_scene_state
from runtime_packet_types import (
    CharacterRuntimePromptProjection,
    RetrievedContextBundle,
    RuntimeCharacterPacket,
    RuntimeScenePacket,
)


def _session_str(session_state: Any, key: str) -> str:
    if session_state is None:
        return ""
    getter = getattr(session_state, "get", None)
    if callable(getter):
        return str(getter(key, "") or "")
    return ""


def build_runtime_scene_packet(
    scene_state: dict[str, Any],
    session_state: Any | None,
) -> RuntimeScenePacket:
    stable, _ = split_scene_state(scene_state)
    return RuntimeScenePacket(
        stable_scene_state=stable,
        session_selected_scene_template_id=_session_str(
            session_state, "selected_scene_template_id"
        ),
        session_scene_owner=_session_str(session_state, "scene_owner"),
        session_opening_mode=_session_str(session_state, "opening_mode"),
        session_initial_message_label=_session_str(
            session_state, "scene_initial_message_label"
        ),
        session_initial_message_prose=_session_str(
            session_state, "scene_initial_message_prose"
        ),
    )


def build_runtime_character_packet(
    *,
    scene_state: dict[str, Any],
    char_name: str,
    user_name: str,
    trigger_text: str,
    director_decision: dict[str, Any],
    session_agent_names: list[str],
    recent_moves: list[dict[str, Any]],
    recent_dialogue: list[dict[str, Any]],
    active_issues: list[dict[str, Any]],
    summary_blocks: list[dict[str, Any]],
    recent_public_events: list[dict[str, Any]],
    cross_session_user_memories: list[Any],
    cross_session_world_facts: list[Any],
    user_preferences: list[Any],
    my_interpretations: list[dict[str, Any]],
    canon_anchors: list[dict[str, Any]],
    scene_grounding_section: str = "",
    scene_binding_constraints_section: str = "",
    retrieved: RetrievedContextBundle | None = None,
) -> RuntimeCharacterPacket:
    _, dynamic = split_scene_state(scene_state)
    bundle = retrieved if retrieved is not None else RetrievedContextBundle()
    return RuntimeCharacterPacket(
        character_name=char_name,
        retrieved=bundle,
        projection=CharacterRuntimePromptProjection(
            dynamic_scene_state=dynamic,
            session_agent_names=list(session_agent_names),
            user_name=user_name,
            trigger_text=trigger_text,
            director_decision=dict(director_decision),
            recent_moves=list(recent_moves),
            recent_dialogue=list(recent_dialogue),
            active_issues=list(active_issues),
            summary_blocks=list(summary_blocks),
            recent_public_events=list(recent_public_events),
            cross_session_user_memories=list(cross_session_user_memories),
            cross_session_world_facts=list(cross_session_world_facts),
            user_preferences=list(user_preferences),
            my_interpretations=list(my_interpretations),
            canon_anchors=list(canon_anchors),
            scene_grounding_section=str(scene_grounding_section or ""),
            scene_binding_constraints_section=str(
                scene_binding_constraints_section or ""
            ),
        ),
    )

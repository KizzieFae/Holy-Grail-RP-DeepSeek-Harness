"""Runtime packet datatypes (Issue #166 split from runtime_packets)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

# Mirrors `SceneState.to_dict` keys in continuity_state.py — stable vs live/dynamic.
STABLE_SCENE_STATE_KEYS = frozenset(
    {
        "location",
        "time_of_day",
        "environment_description",
        "scene_template_id",
        "scene_premise",
        "role_assignments",
        "character_presence_constraints",
        "character_authority_labels",
        "sleeping_surface_slots",
        "location_entry_slots",
        "opening_description",
    }
)


@dataclass(frozen=True)
class RetrievedItem:
    """Single authored retrieval snippet (non-authoritative). Phase 2: index only."""

    text: str
    source_kind: str
    source_ref: str
    scope: str
    relevance_tags: frozenset[str]
    priority: int
    non_authoritative: Literal[True]
    from_other_character: str | None = None


@dataclass(frozen=True)
class RetrievedContextBundle:
    """Bounded per-turn context from authored index (Phase 2); not continuity truth."""

    items: tuple[RetrievedItem, ...] = ()


@dataclass
class RuntimeScenePacket:
    """Authored + scene-start-stable inputs only (no live transcript or trigger text).

    ``session_scene_owner`` mirrors ``session_state["scene_owner"]`` (Issue #107) for
    UI/narrator context only — not audit identity; use ``audit_session_owner`` for audits
    (Issue #106).
    """

    stable_scene_state: dict[str, Any]
    session_selected_scene_template_id: str = ""
    session_scene_owner: str = ""  # same conceptual label as st.session_state["scene_owner"]
    session_opening_mode: str = ""
    session_initial_message_label: str = ""
    session_initial_message_prose: str = ""


@dataclass
class CharacterRuntimePromptProjection:
    """Derived runtime context slice paired with RuntimeCharacterPacket (not continuity truth)."""

    dynamic_scene_state: dict[str, Any]
    session_agent_names: list[str]
    user_name: str
    trigger_text: str
    director_decision: dict[str, Any]
    recent_moves: list[dict[str, Any]]
    recent_dialogue: list[dict[str, Any]]
    active_issues: list[dict[str, Any]]
    summary_blocks: list[dict[str, Any]]
    recent_public_events: list[dict[str, Any]]
    cross_session_user_memories: list[Any]
    cross_session_world_facts: list[Any]
    user_preferences: list[Any]
    my_interpretations: list[dict[str, Any]]
    canon_anchors: list[dict[str, Any]]
    scene_grounding_section: str = ""
    scene_binding_constraints_section: str = ""


@dataclass
class RuntimeCharacterPacket:
    character_name: str
    retrieved: RetrievedContextBundle
    projection: CharacterRuntimePromptProjection


@dataclass(frozen=True)
class CharacterPromptInputAssembly:
    """Single source of truth for character prompt inputs (Phase 0.5 seam boundary).

    Holds everything required to call ``prompt_builders.build_character_turn_prompt`` and
    to build ``RuntimeScenePacket`` / ``RuntimeCharacterPacket``. Populated once per turn;
    live bundle and packets are derived only from this object — no dual derivation.
    """

    char_name: str
    user_name: str
    trigger_text: str
    director_decision: dict[str, Any]
    scene_state: dict[str, Any]
    scene_template_context: dict[str, Any]
    my_scene_role: dict[str, Any]
    scene_roles: list[dict[str, Any]]
    recent_moves: list[dict[str, Any]]
    recent_dialogue: list[dict[str, Any]]
    active_issues: list[dict[str, Any]]
    priority_ladder: list[str]
    summary_blocks: list[dict[str, Any]]
    recent_public_events: list[dict[str, Any]]
    cross_session_user_memories: list[Any]
    cross_session_world_facts: list[Any]
    user_preferences: list[Any]
    my_interpretations: list[dict[str, Any]]
    canon_anchors: list[dict[str, Any]]
    state_context: str
    cast: list[str]
    scene_grounding_section: str
    scene_binding_constraints_section: str
    retrieved_bundle: RetrievedContextBundle
    session_agent_names: list[str]
    session_state: Any

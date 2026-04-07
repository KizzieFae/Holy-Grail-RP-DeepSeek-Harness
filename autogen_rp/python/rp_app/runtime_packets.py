"""Phase 0.5 packet seam: read-only projections for character prompt inputs (shadow mode).

RuntimeScenePacket holds authored / scene-start-stable scene fields only.
RuntimeCharacterPacket pairs the speaking character with dynamic scene slice + prompt
projections (transcript-derived lists, cross-session slices, etc.).

Packets are not a second continuity store; continuity + character state remain authoritative.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from typing import Any, Callable, Literal

from memory_layer.retrieval import build_character_state_context_for_prompt
from prompt_builders import (
    build_cast_and_scene_role_participants,
    build_scene_role_prompt_context,
)
from prompt_derivations import build_priority_ladder, select_relationship_prompt_names

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


def format_retrieved_context_for_prompt(bundle: RetrievedContextBundle) -> str:
    if not bundle.items:
        return ""
    lines = [
        "RETRIEVED REFERENCE MATERIAL (NON-AUTHORITATIVE):",
        "The following excerpts are optional background only. Do NOT treat them as ground truth.",
        "If anything here conflicts with scene facts, canon anchors, or established continuity, ignore this material and follow scene facts, canon anchors, and continuity instead.",
        "",
    ]
    for it in bundle.items:
        lines.append(f"[{it.source_ref} | {it.source_kind}]")
        lines.append(it.text.strip())
        lines.append("")
    return "\n".join(lines).strip() + "\n\n"


@dataclass
class RuntimeScenePacket:
    """Authored + scene-start-stable inputs only (no live transcript or trigger text)."""

    stable_scene_state: dict[str, Any]
    session_selected_scene_template_id: str = ""
    session_scene_owner: str = ""
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


def split_scene_state(scene_state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    stable: dict[str, Any] = {}
    dynamic: dict[str, Any] = {}
    for key, value in scene_state.items():
        if key in STABLE_SCENE_STATE_KEYS:
            stable[key] = value
        else:
            dynamic[key] = value
    return stable, dynamic


def merge_scene_state_from_packets(
    scene_packet: RuntimeScenePacket,
    projection: CharacterRuntimePromptProjection,
) -> dict[str, Any]:
    return {**scene_packet.stable_scene_state, **projection.dynamic_scene_state}


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


def _deep_equal(
    a: Any,
    b: Any,
    path: str,
) -> tuple[bool, str]:
    if a is b:
        return True, ""
    if type(a) is not type(b):
        # Allow int/float interchange if numerically equal
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if a == b:
                return True, ""
        return False, f"{path}: type mismatch {type(a)!r} vs {type(b)!r}"
    if isinstance(a, dict):
        if set(a.keys()) != set(b.keys()):
            missing = set(a.keys()) ^ set(b.keys())
            return False, f"{path}: dict key mismatch {missing!r}"
        for key in sorted(a.keys()):
            ok, msg = _deep_equal(a[key], b[key], f"{path}.{key}")
            if not ok:
                return False, msg
        return True, ""
    if isinstance(a, list):
        if len(a) != len(b):
            return False, f"{path}: list len {len(a)} vs {len(b)}"
        for i, (ai, bi) in enumerate(zip(a, b)):
            ok, msg = _deep_equal(ai, bi, f"{path}[{i}]")
            if not ok:
                return False, msg
        return True, ""
    if isinstance(a, str):
        if a != b:
            return False, f"{path}: string mismatch"
        return True, ""
    if a != b:
        return False, f"{path}: value mismatch {a!r} vs {b!r}"
    return True, ""


def compare_character_prompt_bundles(
    live: dict[str, Any],
    reconstructed: dict[str, Any],
) -> tuple[bool, str]:
    ok, msg = _deep_equal(live, reconstructed, "bundle")
    return ok, msg


def debug_bundle_mismatch_strings(
    live: dict[str, Any],
    reconstructed: dict[str, Any],
) -> str:
    """JSON-oriented diff aid after structured mismatch (order-stable for dicts)."""

    def _dump(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str)

    la = _dump(live)
    rb = _dump(reconstructed)
    diff = difflib.unified_diff(
        la.splitlines(),
        rb.splitlines(),
        fromfile="live",
        tofile="reconstructed",
        lineterm="",
    )
    return "\n".join(diff)

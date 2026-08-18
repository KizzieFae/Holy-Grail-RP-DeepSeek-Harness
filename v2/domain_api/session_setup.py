"""Authoritative session creation from production character cards and scene templates."""

from __future__ import annotations

import copy
import sys
import uuid
from pathlib import Path
from typing import Any

_RP_APP = Path(__file__).resolve().parents[2] / "autogen_rp" / "python" / "rp_app"
_V2 = Path(__file__).resolve().parents[1]
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.character_cards import (  # noqa: E402
    CharacterCardLoader,
    normalize_relationships,
)
from app_state_scene import (  # noqa: E402
    apply_scene_setup_to_scene_state,
    build_initial_scene_issues,
)
from character_state_model import CharacterState  # noqa: E402
from continuity_manager import ContinuityManager  # noqa: E402
from continuity_setup_seam_v77 import finalize_continuity_setup_seam  # noqa: E402
from scene_opener import OpenerManager  # noqa: E402
from scene_template import (  # noqa: E402
    SceneTemplateManager,
    normalize_role_assignments,
    validate_role_assignments,
)
from scene_template_cohesion import resolve_effective_presence_constraint  # noqa: E402

from .memory_scope import resolve_memory_scope_id  # noqa: E402
from .session_history import append_history_entry  # noqa: E402
from .session_state import LiveSession  # noqa: E402


def create_character_state_from_card(card: dict[str, Any]) -> CharacterState:
    char_name = str(card.get("name", "Unknown"))
    return CharacterState(
        name=char_name,
        description=str(card.get("description", "")),
        personality=str(card.get("personality", "")),
        long_term_goal=str(card.get("goals", "")),
        medium_term_goal=str(card.get("medium_term_goal", "")),
        core_goals=list(card.get("core_goals", []) or []),
        voice_profile=dict(card.get("voice_profile", {}) or {}),
        reaction_profile=dict(card.get("reaction_profile", {}) or {}),
        speech_fingerprint=dict(card.get("speech_fingerprint", {}) or {}),
        relationships=normalize_relationships(card.get("relationships", {})),
    )


def _resolve_scene_setup(
    *,
    template_id: str | None,
    character_files: list[str],
    role_assignments_by_file: dict[str, str],
    names_by_file: dict[str, str],
) -> tuple[dict[str, Any] | None, str]:
    if not template_id:
        return None, ""

    manager = SceneTemplateManager()
    template = manager.load_template(str(template_id))
    raw_assignments = normalize_role_assignments(role_assignments_by_file)
    issues = validate_role_assignments(
        template,
        character_files,
        raw_assignments,
    )
    if issues:
        return None, "; ".join(issues)

    role_assignments: dict[str, str] = {}
    character_presence_constraints: dict[str, str] = {}
    character_authority_labels: dict[str, str] = {}

    for char_file in character_files:
        character_name = names_by_file.get(char_file, char_file)
        role_name = raw_assignments.get(char_file, "")
        slot = template.get_role_slot(role_name)
        if slot is None:
            continue
        role_assignments[character_name] = slot.role_name
        character_presence_constraints[character_name] = resolve_effective_presence_constraint(
            template, slot
        )
        if slot.authority:
            character_authority_labels[character_name] = slot.authority

    return {
        "template_id": template.template_id,
        "premise": template.premise,
        "opening_text": template.opening_text,
        "anchor_role_name": template.anchor_role_name,
        "role_assignments": role_assignments,
        "character_presence_constraints": character_presence_constraints,
        "character_authority_labels": character_authority_labels,
        "sleeping_surface_slots": list(template.sleeping_surface_slots),
        "location_entry_slots": list(template.location_entry_slots),
    }, ""


def _resolve_opening_text(
    *,
    opening: dict[str, Any] | None,
    template_id: str | None,
    scene_setup: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    opening = opening or {}
    mode = str(opening.get("mode", "minimal") or "minimal").strip().lower()
    metadata: dict[str, Any] = {"mode": mode}

    if mode == "custom":
        text = str(opening.get("text", "") or "").strip()
        metadata["text"] = text
        return text, metadata

    if mode == "template" and template_id:
        opener_id = str(opening.get("opener_id", "default") or "default")
        manager = OpenerManager()
        for opener in manager.get_template_openers(template_id):
            if opener.id == opener_id:
                metadata["opener_id"] = opener_id
                metadata["label"] = opener.label
                return str(opener.text).strip(), metadata
        return "", {**metadata, "error": f"unknown opener_id: {opener_id}"}

    premise = ""
    if scene_setup:
        premise = str(scene_setup.get("premise", "") or "").strip()
    metadata["source"] = "premise"
    return premise, metadata


def create_live_session_from_setup(
    *,
    character_files: list[str],
    scene_template_id: str | None = None,
    role_assignments: dict[str, str] | None = None,
    opening: dict[str, Any] | None = None,
    location: str | None = None,
    hg_session_id: str | None = None,
    characters_dir: str | Path | None = None,
    memory_scope_id: str | None = None,
) -> LiveSession:
    if not character_files:
        raise ValueError("at least one character file id is required")

    loader = CharacterCardLoader(characters_dir)
    cards: dict[str, dict[str, Any]] = {}
    names_by_file: dict[str, str] = {}
    character_states: dict[str, CharacterState] = {}
    cast: list[str] = []
    secrets: dict[str, str] = {}

    for file_id in character_files:
        card = loader.load_character_card(file_id)
        cards[file_id] = copy.deepcopy(card)
        display_name = str(card.get("name", file_id))
        names_by_file[file_id] = display_name
        cast.append(display_name)
        state = create_character_state_from_card(card)
        character_states[display_name] = state
        if state.private_memories:
            secrets[display_name] = str(state.private_memories[0])

    scene_setup, setup_error = _resolve_scene_setup(
        template_id=scene_template_id,
        character_files=list(character_files),
        role_assignments_by_file=dict(role_assignments or {}),
        names_by_file=names_by_file,
    )
    if setup_error:
        raise ValueError(setup_error)

    opening_text, opening_metadata = _resolve_opening_text(
        opening=opening,
        template_id=scene_template_id,
        scene_setup=scene_setup,
    )
    opening_description = opening_text or (
        str(scene_setup.get("premise", "") if scene_setup else "")
        or "A Holy Grail roleplay session begins."
    )
    resolved_location = (
        location
        or str(opening.get("location", "") if opening else "")
        or "Scene"
    )

    session_id = hg_session_id or f"hg-session-{uuid.uuid4()}"
    mgr = ContinuityManager()
    mgr.initialize_scene(
        location=resolved_location,
        opening_description=opening_description,
        present_characters=list(cast),
    )
    assert mgr.scene_state is not None

    if scene_setup:
        apply_scene_setup_to_scene_state(
            scene_state=mgr.scene_state,
            scene_setup=scene_setup,
            get_must_remain_characters_fn=lambda _state: [
                name
                for name, constraint in scene_setup.get(
                    "character_presence_constraints", {}
                ).items()
                if constraint == "must_remain"
            ],
            continuity_manager=mgr,
        )
        for issue in build_initial_scene_issues(scene_setup):
            mgr.issues[issue.issue_id] = issue
    elif role_assignments:
        mgr.scene_state.role_assignments = {
            names_by_file.get(file_id, file_id): str(role)
            for file_id, role in role_assignments.items()
        }

    finalize_continuity_setup_seam(mgr, cast=list(cast))

    template_snapshot = None
    if scene_template_id:
        template_snapshot = SceneTemplateManager().load_template(scene_template_id).to_dict()

    resolved_scope = resolve_memory_scope_id(memory_scope_id)

    setup_snapshot = {
        "character_files": list(character_files),
        "character_cards": cards,
        "names_by_file": names_by_file,
        "scene_template_id": scene_template_id,
        "scene_template": template_snapshot,
        "role_assignments_by_file": dict(role_assignments or {}),
        "opening": opening_metadata,
        "location": resolved_location,
        "memory_scope_id": resolved_scope,
    }

    rp_history: list[dict[str, Any]] = []
    if opening_text:
        append_history_entry(
            rp_history,
            kind="opening",
            content=opening_text,
            metadata={"opening": True, **opening_metadata},
        )

    return LiveSession(
        hg_session_id=session_id,
        hg_scene_id=session_id,
        manager=mgr,
        cast=list(cast),
        character_states=character_states,
        character_private_secrets=secrets,
        rp_history=rp_history,
        setup_snapshot=setup_snapshot,
        character_file_ids={names_by_file[f]: f for f in character_files},
        memory_scope_id=resolved_scope,
    )


def setup_provenance_for_ui(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return UI-safe setup provenance without private card material."""
    if not snapshot:
        return {}
    names_by_file = dict(snapshot.get("names_by_file") or {})
    return {
        "character_ids": list(snapshot.get("character_files") or []),
        "character_display_names": list(names_by_file.values()),
        "scene_template_id": snapshot.get("scene_template_id"),
        "role_assignments_by_file": dict(snapshot.get("role_assignments_by_file") or {}),
        "opening": dict(snapshot.get("opening") or {}),
        "location": snapshot.get("location"),
        "memory_scope_id": snapshot.get("memory_scope_id"),
    }

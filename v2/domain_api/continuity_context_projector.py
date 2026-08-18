"""Authoritative continuity/scene context projection for ContextAssembly (M11.3)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

_RP_APP = Path(__file__).resolve().parents[2] / "autogen_rp" / "python" / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from scene_grounding import (  # noqa: E402
    format_character_binding_constraints_section,
    format_character_grounding_section,
    format_grounding_prompt_prefix,
    rebuild_scene_grounding_from_continuity,
)

from .session_state import LiveSession

ContextRole = Literal["character", "director", "narrator"]

DEFAULT_CANON_LIMIT_CHARACTER = 6
DEFAULT_CANON_LIMIT_SCENE = 10


@dataclass(frozen=True)
class AuthoritativeContextContribution:
    source_kind: str
    content: str
    authority_class: str
    knowledge_ids: tuple[str, ...]
    provenance: dict[str, Any]
    priority: int


def _presence_labels(fixture: LiveSession) -> tuple[list[str], list[str], list[str]]:
    mgr = fixture.manager
    assert mgr.scene_state is not None
    present = list(getattr(mgr.scene_state, "present_characters", None) or fixture.cast)
    offstage = list(getattr(mgr.scene_state, "offstage_characters", None) or [])
    absent = list(getattr(mgr.scene_state, "absent_but_relevant", None) or [])
    return present, offstage, absent


def _format_canon_anchor_lines(anchors: list[Any]) -> str:
    lines: list[str] = []
    for anchor in anchors:
        category = str(getattr(anchor, "category", "") or "").strip()
        subject = str(getattr(anchor, "subject", "") or "").strip()
        statement = str(getattr(anchor, "statement", "") or "").strip()
        if not statement:
            continue
        label = f"[{category}] {subject}: " if category else ""
        lines.append(f"- {label}{statement}")
    return "\n".join(lines)


def _select_canon_anchors(
    fixture: LiveSession,
    *,
    role: ContextRole,
    character_id: str | None,
) -> list[Any]:
    mgr = fixture.manager
    present, _, _ = _presence_labels(fixture)
    if role == "character":
        if not character_id:
            return []
        return list(
            mgr.get_relevant_canon_anchors(
                character_id,
                participants=present,
                limit=DEFAULT_CANON_LIMIT_CHARACTER,
            )
        )
    return list(mgr.get_scene_canon_anchors(limit=DEFAULT_CANON_LIMIT_SCENE))


def project_scene_state(
    fixture: LiveSession,
    *,
    role: ContextRole,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int = 0,
    continuity_turn_index: int | None = None,
    actors_used_this_round: list[str] | None = None,
    eligible_actors: list[str] | None = None,
) -> AuthoritativeContextContribution | None:
    mgr = fixture.manager
    assert mgr.scene_state is not None
    present, offstage, absent = _presence_labels(fixture)
    location = str(mgr.scene_state.location or "unknown")
    opening = str(getattr(mgr.scene_state, "opening_description", "") or "").strip()
    turn_counter = (
        continuity_turn_index if continuity_turn_index is not None else mgr.turn_counter
    )

    parts = [
        f"Scene location: {location}.",
        f"Present characters: {', '.join(present) if present else 'none'}.",
    ]
    if offstage:
        parts.append(f"Offstage characters: {', '.join(offstage)}.")
    if absent:
        parts.append(f"Absent but relevant: {', '.join(absent)}.")
    if opening:
        parts.append(f"Scene premise: {opening}")
    parts.append(f"Continuity turn counter: {turn_counter}.")
    if role == "director":
        used = actors_used_this_round or []
        eligible = eligible_actors or []
        parts.append(
            f"Actors already used this round: {', '.join(used) if used else 'none'}."
        )
        parts.append(
            f"Eligible actors: {', '.join(eligible) if eligible else 'none'}."
        )

    return AuthoritativeContextContribution(
        source_kind="scene_state",
        content=" ".join(parts),
        authority_class="authoritative",
        knowledge_ids=(f"scene:{hg_scene_id}",),
        provenance={
            "hg_scene_id": hg_scene_id,
            "hg_round_id": hg_round_id,
            "turn_index": turn_index,
            "continuity_turn_index": turn_counter,
            "continuity_version": fixture.continuity_version,
            "projection_kind": "live_scene_state",
            "present_characters": present,
            "offstage_characters": offstage,
            "absent_but_relevant": absent,
        },
        priority=10,
    )


def project_continuity_canon(
    fixture: LiveSession,
    *,
    role: ContextRole,
    character_id: str | None,
    hg_scene_id: str,
    hg_round_id: str,
) -> AuthoritativeContextContribution | None:
    anchors = _select_canon_anchors(fixture, role=role, character_id=character_id)
    body = _format_canon_anchor_lines(anchors)
    if not body:
        return None
    visibility = "character_scoped" if role == "character" else "scene_orchestration"
    return AuthoritativeContextContribution(
        source_kind="continuity_canon",
        content=(
            "Canon anchors (authoritative current continuity; not reference material):\n"
            + body
        ),
        authority_class="authoritative",
        knowledge_ids=tuple(
            f"canon:{getattr(anchor, 'anchor_id', '')}"
            for anchor in anchors
            if getattr(anchor, "anchor_id", "")
        ),
        provenance={
            "hg_scene_id": hg_scene_id,
            "hg_round_id": hg_round_id,
            "projection_kind": "live_canon_anchors",
            "visibility": visibility,
            "character_id": character_id,
            "anchor_ids": [
                str(getattr(anchor, "anchor_id", ""))
                for anchor in anchors
                if getattr(anchor, "anchor_id", "")
            ],
            "continuity_version": fixture.continuity_version,
            "authority_note": "live_continuity_projection_not_knowledge_store",
        },
        priority=11,
    )


def project_scene_grounding(
    fixture: LiveSession,
    *,
    role: ContextRole,
    hg_scene_id: str,
    hg_round_id: str,
) -> AuthoritativeContextContribution | None:
    grounding = rebuild_scene_grounding_from_continuity(fixture.manager)
    if role == "director":
        body = format_grounding_prompt_prefix(grounding).strip()
        if not body:
            return None
        content = body
    else:
        body = format_character_grounding_section(grounding).strip()
        if not body:
            return None
        content = (
            "Settled scene facts (authoritative current continuity; do not contradict):\n"
            + body
        )
    fact_ids = [
        str(item.get("fact_id", ""))
        for item in (grounding.get("facts") or [])
        if isinstance(item, dict) and item.get("fact_id")
    ]
    return AuthoritativeContextContribution(
        source_kind="scene_grounding",
        content=content,
        authority_class="authoritative",
        knowledge_ids=tuple(f"grounding:{fact_id}" for fact_id in fact_ids[:20]),
        provenance={
            "hg_scene_id": hg_scene_id,
            "hg_round_id": hg_round_id,
            "projection_kind": "live_scene_grounding",
            "schema_version": grounding.get("schema_version"),
            "fact_ids": fact_ids,
            "last_rebuilt_turn": grounding.get("last_rebuilt_turn"),
            "continuity_version": fixture.continuity_version,
            "authority_note": "live_continuity_projection_not_knowledge_store",
        },
        priority=12,
    )


def project_active_constraints(
    fixture: LiveSession,
    *,
    hg_scene_id: str,
    hg_round_id: str,
    character_id: str,
) -> AuthoritativeContextContribution | None:
    grounding = rebuild_scene_grounding_from_continuity(fixture.manager)
    body = format_character_binding_constraints_section(grounding).strip()
    if not body:
        return None
    return AuthoritativeContextContribution(
        source_kind="active_constraints",
        content=(
            "Binding scene constraints (authoritative; must not be contradicted in action):\n"
            + body
        ),
        authority_class="authoritative",
        knowledge_ids=(f"constraints:{character_id}:{hg_scene_id}",),
        provenance={
            "hg_scene_id": hg_scene_id,
            "hg_round_id": hg_round_id,
            "projection_kind": "live_binding_constraints",
            "character_id": character_id,
            "continuity_version": fixture.continuity_version,
            "authority_note": "live_continuity_projection_not_knowledge_store",
        },
        priority=13,
    )


def project_authoritative_context(
    fixture: LiveSession,
    *,
    role: ContextRole,
    hg_scene_id: str,
    hg_round_id: str,
    character_id: str | None = None,
    turn_index: int = 0,
    continuity_turn_index: int | None = None,
    actors_used_this_round: list[str] | None = None,
    eligible_actors: list[str] | None = None,
) -> list[AuthoritativeContextContribution]:
    """Project live authoritative continuity context (no persistence)."""
    contributions: list[AuthoritativeContextContribution] = []
    scene = project_scene_state(
        fixture,
        role=role,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        continuity_turn_index=continuity_turn_index,
        actors_used_this_round=actors_used_this_round,
        eligible_actors=eligible_actors,
    )
    if scene is not None:
        contributions.append(scene)
    canon = project_continuity_canon(
        fixture,
        role=role,
        character_id=character_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
    )
    if canon is not None:
        contributions.append(canon)
    grounding = project_scene_grounding(
        fixture,
        role=role,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
    )
    if grounding is not None:
        contributions.append(grounding)
    if role == "character" and character_id:
        constraints = project_active_constraints(
            fixture,
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id=character_id,
        )
        if constraints is not None:
            contributions.append(constraints)
    return contributions

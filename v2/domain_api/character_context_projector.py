"""Character-specific PromptContribution projections for live inference (#30)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from character_state_model import CharacterState  # noqa: E402
from continuity_issue_manager_wiring import DEFAULT_ACTIVE_ISSUE_LIMIT  # noqa: E402
from continuity_issue_retrieval import get_active_issues  # noqa: E402
from continuity_state import IssueStatus  # noqa: E402

from .continuity_context_projector import (  # noqa: E402
    project_scene_progression,
    project_scene_setup,
)
from .contract import PromptContribution  # noqa: E402
from .session_state import LiveSession  # noqa: E402


def _format_profile_map(profile: dict[str, Any]) -> str:
    if not profile:
        return ""
    return ", ".join(f"{key}={value}" for key, value in profile.items())


def _present_cast_labels(fixture: LiveSession, character_id: str) -> tuple[list[str], list[str]]:
    mgr = fixture.manager
    assert mgr.scene_state is not None
    present = [
        str(name).strip()
        for name in (getattr(mgr.scene_state, "present_characters", None) or fixture.cast)
        if str(name or "").strip()
    ]
    focus = [name for name in present if name != character_id]
    absent = [
        str(name).strip()
        for name in (getattr(mgr.scene_state, "absent_but_relevant", None) or [])
        if str(name or "").strip() and str(name).strip() != character_id
    ]
    return focus, absent


def project_character_identity(
    *,
    state: CharacterState | None,
    character_id: str,
    role: str,
    scene_role_name: str = "",
) -> PromptContribution | None:
    if state is None:
        return None
    parts = [
        "CHARACTER IDENTITY (authoritative portrayal anchor):",
        f"You are {character_id}.",
    ]
    if scene_role_name:
        parts.append(f"Scene role: {scene_role_name}.")
    elif role:
        parts.append(f"Assigned role label: {role}.")
    description = str(state.description or "").strip()
    if description:
        parts.append(f"Description: {description}")
    personality = str(state.personality or "").strip()
    if personality:
        parts.append(f"Personality: {personality}")
    core_goals = [str(goal).strip() for goal in (state.core_goals or []) if str(goal).strip()]
    if core_goals:
        parts.append(f"Core goals: {', '.join(core_goals)}")
    long_term = str(state.long_term_goal or "").strip()
    if long_term and not core_goals:
        parts.append(f"Long-term goal: {long_term}")
    medium_term = str(state.medium_term_goal or "").strip()
    if medium_term:
        parts.append(f"Medium-term goal: {medium_term}")
    content = "\n".join(parts).strip()
    return PromptContribution(
        contribution_id="character-identity",
        source_kind="character_identity",
        authority_class="authoritative",
        knowledge_ids=(f"character-identity:{character_id}",),
        priority=18,
        content=content,
        provenance={
            "character_id": character_id,
            "role": role,
            "scene_role_name": scene_role_name or None,
            "projection_kind": "character_identity",
        },
    )


def project_character_expression(
    *,
    state: CharacterState | None,
    character_id: str,
) -> PromptContribution | None:
    if state is None:
        return None
    parts = ["CHARACTER EXPRESSION (how you characteristically speak and react):"]
    if state.voice_profile:
        parts.append(f"Voice profile: {_format_profile_map(state.voice_profile)}")
    if state.reaction_profile:
        parts.append(f"Reaction profile: {_format_profile_map(state.reaction_profile)}")
    if state.speech_fingerprint:
        parts.append(
            f"Speech fingerprint: {_format_profile_map(state.speech_fingerprint)}"
        )
    if state.emotional_state:
        parts.append(f"Current emotional state: {state.emotional_state}")
    if state.stress_level is not None:
        parts.append(f"Stress level: {state.stress_level}/10")
    if state.short_term_tactic:
        parts.append(f"Current tactic: {state.short_term_tactic}")
    if state.current_objective:
        parts.append(f"Immediate objective: {state.current_objective}")
    if len(parts) == 1:
        return None
    return PromptContribution(
        contribution_id="character-expression",
        source_kind="character_expression",
        authority_class="authoritative",
        knowledge_ids=(f"character-expression:{character_id}",),
        priority=19,
        content="\n".join(parts),
        provenance={
            "character_id": character_id,
            "projection_kind": "character_expression",
        },
    )


def project_character_relationships(
    *,
    state: CharacterState | None,
    character_id: str,
    focus_names: list[str],
    secondary_names: list[str],
) -> PromptContribution | None:
    if state is None:
        return None
    snapshot = state.relationship_prompt_snapshot(
        focus_names=focus_names,
        secondary_names=secondary_names,
    )
    focused = snapshot.get("focused_threads") or []
    secondary = snapshot.get("secondary_threads") or []
    if not focused and not secondary:
        return None
    payload = {
        "focused_threads": focused,
        "secondary_threads": secondary,
    }
    return PromptContribution(
        contribution_id="character-relationships",
        source_kind="character_relationships",
        authority_class="authoritative",
        knowledge_ids=tuple(
            f"relationship:{character_id}:{thread['name']}"
            for thread in [*focused, *secondary]
            if thread.get("name")
        ),
        priority=19,
        content=(
            "CHARACTER RELATIONSHIPS (bounded to current scene cast):\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
        ),
        provenance={
            "character_id": character_id,
            "projection_kind": "character_relationships",
            "focus_names": list(focus_names),
            "secondary_names": list(secondary_names),
        },
    )


def project_character_scene_context(
    fixture: LiveSession,
    *,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
) -> PromptContribution | None:
    setup = project_scene_setup(
        fixture,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
    )
    progression = project_scene_progression(
        fixture,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
    )
    blocks: list[str] = ["SCENE CONTEXT (authoritative current scene position):"]
    if setup is not None and setup.content.strip():
        blocks.append(setup.content.strip())
    blocks.append(progression.content.strip())
    mgr = fixture.manager
    assert mgr.scene_state is not None
    role_assignments = dict(getattr(mgr.scene_state, "role_assignments", {}) or {})
    if role_assignments:
        blocks.append(
            "Cast role map:\n"
            + json.dumps(role_assignments, ensure_ascii=False, indent=2)
        )
    return PromptContribution(
        contribution_id="scene-context",
        source_kind="scene_context",
        authority_class="authoritative",
        knowledge_ids=(f"scene-context:{hg_scene_id}",),
        priority=19,
        content="\n\n".join(blocks),
        provenance={
            "hg_scene_id": hg_scene_id,
            "hg_round_id": hg_round_id,
            "projection_kind": "character_scene_context",
        },
    )


def project_character_scene_pressures(
    fixture: LiveSession,
    *,
    character_id: str,
) -> PromptContribution | None:
    mgr = fixture.manager
    active_issues = get_active_issues(
        manager=mgr,
        limit=DEFAULT_ACTIVE_ISSUE_LIMIT,
        statuses=[IssueStatus.ACTIVE, IssueStatus.ESCALATING],
    )
    if not active_issues:
        return None
    entries: list[dict[str, Any]] = []
    for issue in active_issues:
        participants = list(issue.participants)
        if participants and character_id not in participants:
            continue
        entries.append(
            {
                "issue_id": issue.issue_id,
                "status": issue.status.value,
                "participants": participants,
                "pressure_kind": issue.pressure_kind,
                "blocked_what": issue.blocked_what,
                "required_next_step": issue.required_next_step,
                "description": issue.description,
            }
        )
    if not entries:
        entries = [
            {
                "issue_id": issue.issue_id,
                "status": issue.status.value,
                "participants": list(issue.participants),
                "pressure_kind": issue.pressure_kind,
                "blocked_what": issue.blocked_what,
                "required_next_step": issue.required_next_step,
                "description": issue.description,
            }
            for issue in active_issues
        ]
    return PromptContribution(
        contribution_id="scene-pressures",
        source_kind="scene_pressures",
        authority_class="derived",
        knowledge_ids=tuple(f"issue:{entry['issue_id']}" for entry in entries),
        priority=20,
        content=(
            "SCENE PRESSURES (bounded active issues relevant to this Character):\n"
            + json.dumps({"active_issues": entries}, ensure_ascii=False, indent=2)
        ),
        provenance={
            "character_id": character_id,
            "projection_kind": "character_scene_pressures",
            "active_issue_count": len(entries),
        },
    )


def project_character_director_context(
    *,
    character_id: str,
    director_decision: dict[str, Any] | None,
) -> PromptContribution | None:
    if not isinstance(director_decision, dict) or not director_decision:
        return None
    advisory = {
        "reason": str(director_decision.get("reason", "") or "").strip(),
        "environment_event": str(director_decision.get("environment_event", "") or "").strip(),
        "tension_shift": str(director_decision.get("tension_shift", "") or "").strip(),
    }
    if not any(advisory.values()):
        return None
    return PromptContribution(
        contribution_id="director-context",
        source_kind="director_context",
        authority_class="suggestive",
        knowledge_ids=(f"director-context:{character_id}",),
        priority=22,
        content=(
            "DIRECTOR CONTEXT (advisory only — informs pressure and circumstances; "
            "does not prescribe your dialogue, action, emotion, or decisions):\n"
            + json.dumps(advisory, ensure_ascii=False, indent=2)
        ),
        provenance={
            "character_id": character_id,
            "projection_kind": "character_director_context",
            "visibility": "advisory_projection",
        },
    )


def build_character_lane_contributions(
    fixture: LiveSession,
    *,
    manifest_id: str,
    character_id: str,
    role: str,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    director_decision: dict[str, Any] | None,
) -> list[PromptContribution]:
    state = fixture.character_states.get(character_id)
    mgr = fixture.manager
    assert mgr.scene_state is not None
    scene_role_name = str(
        (getattr(mgr.scene_state, "role_assignments", {}) or {}).get(character_id, "")
    ).strip()
    focus_names, secondary_names = _present_cast_labels(fixture, character_id)
    lanes: list[PromptContribution | None] = [
        project_character_identity(
            state=state,
            character_id=character_id,
            role=role,
            scene_role_name=scene_role_name,
        ),
        project_character_expression(state=state, character_id=character_id),
        project_character_relationships(
            state=state,
            character_id=character_id,
            focus_names=focus_names,
            secondary_names=secondary_names,
        ),
        project_character_scene_context(
            fixture,
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            turn_index=turn_index,
        ),
        project_character_scene_pressures(fixture, character_id=character_id),
        project_character_director_context(
            character_id=character_id,
            director_decision=director_decision,
        ),
    ]
    contributions: list[PromptContribution] = []
    for lane in lanes:
        if lane is None:
            continue
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-{lane.contribution_id}",
                source_kind=lane.source_kind,
                authority_class=lane.authority_class,
                knowledge_ids=lane.knowledge_ids,
                priority=lane.priority,
                content=lane.content,
                provenance=dict(lane.provenance),
            )
        )
    return contributions

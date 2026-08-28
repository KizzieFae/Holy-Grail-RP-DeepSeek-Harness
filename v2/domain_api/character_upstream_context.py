"""Shared pre-Librarian Character upstream contribution assembly (#38)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .character_context_projector import build_character_lane_contributions
from .character_conversation_projection import project_character_conversation_for_manifest
from .contract import PromptContribution
from .continuity_context_projector import project_authoritative_context
from .context_substrate import auth_projections_to_contributions, semantic_correction_contribution
from .session_state import LiveSession, RoundFixture
from .storyteller_round_packaging import storyteller_contributions_for_consumer


LEGACY_CHARACTER_KNOWLEDGE_SOURCE_KINDS = frozenset(
    {
        "authored_character_knowledge",
        "scene_reference",
        "learned_world_knowledge",
        "user_profile",
    }
)


@dataclass(frozen=True)
class CharacterUpstreamContext:
    contributions: tuple[PromptContribution, ...]
    upstream_fingerprint: str
    completeness: dict[str, Any]


def _contribution_fingerprint(contributions: tuple[PromptContribution, ...]) -> str:
    payload = [
        {
            "contribution_id": item.contribution_id,
            "source_kind": item.source_kind,
            "content": item.content,
            "priority": item.priority,
        }
        for item in contributions
    ]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assemble_character_upstream_contributions(
    fixture: LiveSession,
    rnd: RoundFixture,
    *,
    manifest_id: str,
    character_id: str,
    role: str,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    director_decision: dict[str, Any] | None,
    correction_context: dict[str, Any] | None,
    memory_projections: list[tuple[str, dict[str, Any]]],
    private_secret: str,
    include_correction: bool = True,
) -> CharacterUpstreamContext:
    auth_projections = project_authoritative_context(
        fixture,
        role="character",
        character_id=character_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
    )
    contributions: list[PromptContribution] = list(
        auth_projections_to_contributions(manifest_id, auth_projections)
    )
    has_continuity_summary = False
    has_transcript = False
    has_trigger = False
    if rnd.character_turns:
        has_continuity_summary = True
        prior_lines = []
        for turn in rnd.character_turns:
            move_json = json.dumps(turn.committed_move, ensure_ascii=False)
            prior_lines.append(
                f"- {turn.character_id} (commit {turn.domain_commit_id}): {move_json}"
            )
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-continuity-summary",
                source_kind="continuity_summary",
                authority_class="authoritative",
                knowledge_ids=tuple(
                    f"commit:{turn.domain_commit_id}" for turn in rnd.character_turns
                ),
                priority=15,
                content="Committed turns earlier in this round:\n" + "\n".join(prior_lines),
                provenance={
                    "hg_round_id": hg_round_id,
                    "visibility": "orchestration_projection",
                },
            )
        )
    transcript_content, trigger_content, conv_prov = project_character_conversation_for_manifest(
        fixture,
        character_id=character_id,
    )
    if transcript_content:
        has_transcript = True
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-recent-scene-transcript",
                source_kind="recent_scene_transcript",
                authority_class="derived",
                knowledge_ids=(
                    f"rp_history:transcript:{character_id}:{hg_round_id}",
                ),
                priority=16,
                content=transcript_content,
                provenance={
                    "hg_round_id": hg_round_id,
                    "visibility": "character_viewer_projection",
                    **conv_prov,
                },
            )
        )
    if trigger_content:
        has_trigger = True
        trigger_entry_id = conv_prov.get("trigger_entry_id")
        knowledge_ids: tuple[str, ...] = (
            (f"rp_history:trigger:{trigger_entry_id}",)
            if trigger_entry_id
            else (f"rp_history:trigger:{character_id}:{hg_round_id}",)
        )
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-user-turn-trigger",
                source_kind="user_turn_trigger",
                authority_class="derived",
                knowledge_ids=knowledge_ids,
                priority=17,
                content=trigger_content,
                provenance={
                    "hg_round_id": hg_round_id,
                    "visibility": "character_viewer_projection",
                    **conv_prov,
                },
            )
        )
    contributions.extend(
        build_character_lane_contributions(
            fixture,
            manifest_id=manifest_id,
            character_id=character_id,
            role=role,
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            turn_index=turn_index,
            director_decision=director_decision,
        )
    )
    contributions.extend(
        storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id=manifest_id,
            consumer_target="character",
            character_id=character_id,
        )
    )
    if private_secret.strip():
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-character-private",
                source_kind="character_private",
                authority_class="authoritative",
                knowledge_ids=(f"character-private:{character_id}",),
                priority=25,
                content=f"Character-private knowledge for {character_id}: {private_secret}",
                provenance={"character_id": character_id, "visibility": "character_only"},
            )
        )
    for index, (memory_content, memory_provenance) in enumerate(memory_projections):
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-character-memory-{index}",
                source_kind="character_memory",
                authority_class="derived",
                knowledge_ids=(
                    f"character-memory:{character_id}:{memory_provenance.get('memory_lane', 'session')}",
                ),
                priority=26 + index,
                content=memory_content,
                provenance={
                    "character_id": character_id,
                    **memory_provenance,
                },
            )
        )
    if include_correction and isinstance(correction_context, dict) and correction_context:
        contributions.append(
            semantic_correction_contribution(
                manifest_id,
                correction_context,
                inference_id=str(correction_context.get("evaluation_pass_id") or manifest_id),
            )
        )
    frozen = tuple(contributions)
    return CharacterUpstreamContext(
        contributions=frozen,
        upstream_fingerprint=_contribution_fingerprint(frozen),
        completeness={
            "has_continuity_summary": has_continuity_summary,
            "has_transcript": has_transcript,
            "has_trigger": has_trigger,
            "has_private": bool(private_secret.strip()),
            "memory_lane_count": len(memory_projections),
            "has_correction": bool(include_correction and correction_context),
        },
    )

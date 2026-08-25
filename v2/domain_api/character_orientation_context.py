"""Character knowledge-orientation manifest assembly (#38)."""

from __future__ import annotations

from typing import Any

from .character_contract import CHARACTER_ORIENTATION_SCHEMA
from .character_upstream_context import CharacterUpstreamContext
from .contract import PromptContribution


def build_character_orientation_context(
    upstream: CharacterUpstreamContext,
    *,
    manifest_id: str,
    character_id: str,
    inference_id: str,
) -> tuple[tuple[PromptContribution, ...], dict[str, Any]]:
    contributions = list(upstream.contributions)
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-character-orientation-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"inference:{inference_id}",),
            priority=100,
            content=(
                "CHARACTER KNOWLEDGE ORIENTATION TASK:\n"
                f"You are orienting as character {character_id}.\n"
                "Given the upstream scene context above, identify what additional knowledge "
                "you need to act in this turn.\n"
                "Populate information_gaps with focus questions for the Librarian.\n"
                "Do NOT output a character move, dialogue, narration, or continuity mutations.\n"
                "Do NOT reference retrieval backends, candidate ids, or relevance ranks."
            ),
            provenance={
                "projection_kind": "character_orientation_instruction",
                "contract": CHARACTER_ORIENTATION_SCHEMA,
                "character_id": character_id,
            },
        )
    )
    envelope = {
        "character_id": character_id,
        "upstream_fingerprint": upstream.upstream_fingerprint,
        "completeness": dict(upstream.completeness),
    }
    return tuple(contributions), envelope

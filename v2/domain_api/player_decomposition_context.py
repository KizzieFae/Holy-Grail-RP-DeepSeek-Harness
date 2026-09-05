"""Player perceptual-decomposition inference context (#109)."""

from __future__ import annotations

from narrative_visibility_prompt import PLAYER_SEMANTIC_DECOMPOSITION_OUTPUT_INSTRUCTION

from .contract import (
    PlayerDecompositionContextPrepareRequest,
    PromptContribution,
    PromptContributionManifest,
)
from .session_state import LiveSession


def prepare_player_decomposition_context(
    fixture: LiveSession,
    req: PlayerDecompositionContextPrepareRequest,
) -> PromptContributionManifest:
    hg_scene_id = fixture.hg_scene_id
    hg_round_id = str(req.hg_round_id or f"player-decomposition-{req.inference_id}")
    manifest_id = f"manifest-player-decomposition-{req.inference_id}"

    contributions = [
        PromptContribution(
            contribution_id=f"{manifest_id}-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"inference:{req.inference_id}",),
            priority=30,
            content=(
                "Decompose the player-authored turn provided in the user message "
                "into semantic perceptual units with verbatim excerpts only.\n"
                f"\n{PLAYER_SEMANTIC_DECOMPOSITION_OUTPUT_INSTRUCTION}\n"
            ),
            provenance={"inference_id": req.inference_id, "role": "player_decomposition"},
        ),
    ]

    return PromptContributionManifest(
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        role="player_decomposition",
        character_id=None,
        turn_index=req.turn_index,
        attempt_index=req.attempt_index,
        contributions=tuple(contributions),
    )

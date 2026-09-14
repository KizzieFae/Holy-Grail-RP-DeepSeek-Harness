"""Player uniform-eligibility adversarial verification context (#197)."""

from __future__ import annotations

from narrative_visibility_prompt import PLAYER_UNIFORM_ELIGIBILITY_VERIFICATION_OUTPUT_INSTRUCTION

from .contract import (
    PlayerUniformEligibilityVerificationContextPrepareRequest,
    PromptContribution,
    PromptContributionManifest,
)
from .manifest_validation import finalize_prompt_contribution_manifest
from .session_state import LiveSession


def prepare_player_uniform_eligibility_verification_context(
    fixture: LiveSession,
    req: PlayerUniformEligibilityVerificationContextPrepareRequest,
) -> PromptContributionManifest:
    hg_scene_id = fixture.hg_scene_id
    hg_round_id = str(
        req.hg_round_id or f"player-uniform-eligibility-verification-{req.inference_id}"
    )
    manifest_id = f"manifest-player-uniform-eligibility-verification-{req.inference_id}"

    contributions = [
        PromptContribution(
            contribution_id=f"{manifest_id}-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"inference:{req.inference_id}",),
            priority=30,
            content=(
                "An affirmative uniform-projection proposal is under adversarial review. "
                "Find whether ANY semantic content disqualifies uniform projection for the "
                "player-authored turn in the user message.\n"
                f"\n{PLAYER_UNIFORM_ELIGIBILITY_VERIFICATION_OUTPUT_INSTRUCTION}\n"
            ),
            provenance={
                "inference_id": req.inference_id,
                "role": "player_uniform_eligibility_verification",
            },
        ),
    ]

    return finalize_prompt_contribution_manifest(
        "player_uniform_eligibility_verification",
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        role="player_uniform_eligibility_verification",
        character_id=None,
        turn_index=req.turn_index,
        attempt_index=req.attempt_index,
        contributions=contributions,
    )

"""Player visibility-complexity checker inference context (#121)."""

from __future__ import annotations

from narrative_visibility_prompt import PLAYER_VISIBILITY_TRIAGE_OUTPUT_INSTRUCTION

from .contract import (
    PlayerVisibilityTriageContextPrepareRequest,
    PromptContribution,
    PromptContributionManifest,
)
from .manifest_validation import finalize_prompt_contribution_manifest
from .session_state import LiveSession


def prepare_player_visibility_triage_context(
    fixture: LiveSession,
    req: PlayerVisibilityTriageContextPrepareRequest,
) -> PromptContributionManifest:
    hg_scene_id = fixture.hg_scene_id
    hg_round_id = str(req.hg_round_id or f"player-visibility-triage-{req.inference_id}")
    manifest_id = f"manifest-player-visibility-triage-{req.inference_id}"

    contributions = [
        PromptContribution(
            contribution_id=f"{manifest_id}-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"inference:{req.inference_id}",),
            priority=30,
            content=(
                "Evaluate whether the player-authored turn in the user message is affirmatively "
                "safe for uniform projection to all present Characters without semantic decomposition.\n"
                f"\n{PLAYER_VISIBILITY_TRIAGE_OUTPUT_INSTRUCTION}\n"
            ),
            provenance={"inference_id": req.inference_id, "role": "player_visibility_triage"},
        ),
    ]

    return finalize_prompt_contribution_manifest(
        "player_visibility_triage",
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        role="player_visibility_triage",
        character_id=None,
        turn_index=req.turn_index,
        attempt_index=req.attempt_index,
        contributions=contributions,
    )

"""Host-side validation for model-only prompt contribution packages (#134)."""

from __future__ import annotations

from typing import Sequence

from .contract import PromptContribution, PromptContributionManifest
from .manifest_projection_policy import (
    InferenceKind,
    validate_model_context_contributions,
)


def validate_prompt_contribution_manifest(manifest: PromptContributionManifest) -> None:
    if not manifest.inference_kind:
        raise ValueError(
            "PromptContributionManifest.inference_kind is required for model-context validation"
        )
    validate_model_context_contributions(manifest.inference_kind, manifest.contributions)


def validate_contribution_package(
    inference_kind: InferenceKind | str,
    contributions: Sequence[PromptContribution],
) -> None:
    validate_model_context_contributions(str(inference_kind), contributions)


def finalize_prompt_contribution_manifest(
    inference_kind: InferenceKind | str,
    *,
    manifest_id: str,
    inference_id: str,
    hg_scene_id: str,
    hg_round_id: str,
    role: str,
    character_id: str | None,
    turn_index: int,
    attempt_index: int,
    contributions: Sequence[PromptContribution],
) -> PromptContributionManifest:
    ordered = tuple(contributions)
    validate_model_context_contributions(str(inference_kind), ordered)
    return PromptContributionManifest(
        manifest_id=manifest_id,
        inference_id=inference_id,
        inference_kind=str(inference_kind),
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        role=role,
        character_id=character_id,
        turn_index=turn_index,
        attempt_index=attempt_index,
        contributions=ordered,
    )

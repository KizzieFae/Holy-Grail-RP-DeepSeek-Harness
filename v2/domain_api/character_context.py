"""Character role context/manifest assembly (#54 C2)."""

from __future__ import annotations

from typing import Any

from .character_upstream_context import assemble_character_upstream_contributions
from .context_substrate import memory_projections_for_character
from .contract import ContextPrepareRequest, PromptContribution, PromptContributionManifest
from .librarian_bundle_codec import librarian_knowledge_bundle_from_dict
from .librarian_packaging_mapper import map_librarian_bundle_to_contributions
from .librarian_packaging_validity import PackagingBindingContext
from .memory_service import MemoryService
from .plot_cognition_overlay_service import PlotCognitionOverlayService
from .session_state import LiveSession, RoundFixture


def prepare_character_context(
    fixture: LiveSession,
    rnd: RoundFixture,
    req: ContextPrepareRequest,
    *,
    memory_service: MemoryService | None,
    overlay_service: PlotCognitionOverlayService | None = None,
) -> PromptContributionManifest:
    manifest_id = f"manifest-character-{req.inference_id}-{req.attempt_index}"
    private_secret = fixture.character_private_secrets.get(req.character_id, "")
    memory_projections = memory_projections_for_character(
        fixture, req.character_id, memory_service
    )
    upstream = assemble_character_upstream_contributions(
        fixture,
        rnd,
        manifest_id=manifest_id,
        character_id=req.character_id,
        role=req.role,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        turn_index=req.turn_index,
        director_decision=req.director_decision,
        correction_context=req.correction_context,
        memory_projections=memory_projections,
        private_secret=private_secret,
        include_correction=True,
        overlay_service=overlay_service,
        projection_batch_id=req.plot_cognition_projection_batch_id,
        projection_semantic_results=req.plot_cognition_projection_semantic_results,
    )
    contributions: list[PromptContribution] = list(upstream.contributions)
    librarian_audit = dict(req.librarian_knowledge_audit or {})
    if isinstance(req.librarian_bundle, dict) and req.librarian_bundle:
        try:
            bundle = librarian_knowledge_bundle_from_dict(req.librarian_bundle)
            binding = PackagingBindingContext(
                hg_round_id=req.hg_round_id,
                turn_index=req.turn_index,
                pipeline_stage="character",
                continuity_version=int(fixture.continuity_version),
                authoritative_snapshot_id=(
                    f"cv:{fixture.continuity_version}:scene:{req.hg_scene_id}:round:{req.hg_round_id}"
                ),
                bound_character_id=req.character_id,
            )
            packaging = map_librarian_bundle_to_contributions(
                bundle,
                manifest_id=manifest_id,
                consumer_target="character",
                binding=binding,
            )
            librarian_audit.update(
                {
                    "bundle_id": bundle.bundle_id,
                    "eligibility_accepted": packaging.eligibility.accepted,
                    "eligibility_reason": packaging.eligibility.reason,
                    "rejection_codes": list(packaging.eligibility.rejection_codes),
                    "entries_considered": packaging.entries_considered,
                    "entries_mapped": packaging.entries_mapped,
                    "mediation_mode": bundle.mediation_mode,
                    "omitted_reason": packaging.omitted_reason,
                }
            )
            if packaging.contributions:
                contributions.extend(packaging.contributions)
        except (KeyError, TypeError, ValueError) as exc:
            librarian_audit.update(
                {
                    "bundle_decode_error": str(exc),
                    "eligibility_accepted": False,
                }
            )
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"inference:{req.inference_id}",),
            priority=30,
            content=(
                "Output only valid JSON for move_schema_version 2 with non-empty beats[], "
                "motivation object, and semantic_evaluation. "
                "Each beat must be type action (key action) or type speech (key dialogue). "
                "Action-only, speech-only, and mixed beat sequences are all valid when "
                "appropriate to the scene."
            ),
            provenance={
                "inference_id": req.inference_id,
                **({"librarian_knowledge_audit": librarian_audit} if librarian_audit else {}),
            },
        ),
    )
    return PromptContributionManifest(
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        role="character",
        character_id=req.character_id,
        turn_index=req.turn_index,
        attempt_index=req.attempt_index,
        contributions=contributions,
    )

"""Director role context/manifest assembly (#54 C2)."""

from __future__ import annotations

from domain.modules.authority_reference import validate_authority_references

from .context_substrate import auth_projections_to_contributions, semantic_correction_contribution
from .continuity_context_projector import project_authoritative_context
from .contract import DirectorContextPrepareRequest, DirectorContextPrepareResponse, PromptContribution
from .director_context_digests import (
    build_director_scene_evidence_contributions,
    director_scene_condition_flags,
    validate_director_context_completeness,
)
from .plot_cognition_overlay_service import PlotCognitionOverlayService
from .plot_cognition_orchestration_service import PlotCognitionOrchestrationService
from .session_state import LiveSession, RoundFixture
from .storyteller_round_packaging import storyteller_contributions_for_consumer


def prepare_director_context(
    fixture: LiveSession,
    rnd: RoundFixture,
    req: DirectorContextPrepareRequest,
    *,
    available_actors: list[str],
    overlay_service: PlotCognitionOverlayService | None = None,
) -> DirectorContextPrepareResponse:
    manifest_id = f"manifest-director-{req.inference_id}-{req.attempt_index}"
    used = list(req.actors_used_this_round) or list(rnd.actors_used_this_round)
    auth_projections = project_authoritative_context(
        fixture,
        role="director",
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        turn_index=req.turn_index,
        actors_used_this_round=used,
        eligible_actors=available_actors,
    )
    scene_contributions, authority_refs = build_director_scene_evidence_contributions(
        fixture,
        rnd,
        manifest_id,
        available_actors,
        auth_contributions=list(
            auth_projections_to_contributions(manifest_id, auth_projections)
        ),
    )
    contributions: list[PromptContribution] = list(scene_contributions)
    contributions.extend(
        storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id=manifest_id,
            consumer_target="director",
            overlay_service=overlay_service,
            orchestration_service=PlotCognitionOrchestrationService(overlay_service)
            if overlay_service is not None
            else None,
        )
    )
    contributions.extend(
        (
            PromptContribution(
                contribution_id=f"{manifest_id}-director-scratch",
                source_kind="director_scratch",
                authority_class="derived",
                knowledge_ids=(f"director:{req.inference_id}",),
                priority=20,
                content=(
                    "Director scratch: weigh participation balance and select the next actor. "
                    "Do not assume character-private knowledge."
                ),
                provenance={"inference_id": req.inference_id, "role": "director"},
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-instruction",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=(f"inference:{req.inference_id}",),
                priority=30,
                content=(
                    "Output only JSON with next_actor, end_round, reason, environment_event, "
                    "tension_shift. tension_shift must be escalate, soften, or steady. "
                    "environment_event is optional; use an empty string rather than repeating "
                    "a recent accepted environment development."
                ),
                provenance={"inference_id": req.inference_id},
            ),
        )
    )
    correction = req.correction_context
    if isinstance(correction, dict) and correction:
        contributions.insert(
            -1,
            semantic_correction_contribution(
                manifest_id,
                correction,
                inference_id=req.inference_id,
                attempt_index=req.attempt_index,
            ),
        )
    flags = director_scene_condition_flags(fixture, rnd, available_actors)
    context_completeness = validate_director_context_completeness(
        contributions,
        has_round_turns=flags["has_round_turns"],
        multiple_eligible=flags["multiple_eligible"],
        has_active_issues=flags["has_active_issues"],
        has_user_turn=flags["has_user_turn"],
    )
    normalized_refs, ref_errors = validate_authority_references(authority_refs)
    if ref_errors:
        raise ValueError("Director context preparation failed: " + "; ".join(ref_errors))
    return DirectorContextPrepareResponse(
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        role="director",
        character_id=None,
        turn_index=rnd.turn_index,
        attempt_index=req.attempt_index,
        contributions=tuple(contributions),
        authority_references=tuple(normalized_refs),
        context_completeness=context_completeness,
    )

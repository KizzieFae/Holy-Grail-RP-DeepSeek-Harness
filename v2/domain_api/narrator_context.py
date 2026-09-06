"""Narrator render context/manifest assembly (#54 C2). Read-only — no persistence."""

from __future__ import annotations

import json
from typing import Any

from perception_audibility_structured import redact_structured_move_for_orchestration
from narrator_render_instruction import build_narrator_render_prompt

from .context_substrate import auth_projections_to_contributions, semantic_correction_contribution
from .continuity_context_projector import project_authoritative_context
from .contract import NarratorContextPrepareRequest, PromptContribution
from .manifest_validation import finalize_prompt_contribution_manifest
from .narrator_environment_cognition import build_cognition_context_payload
from .narrator_environment_sufficiency import format_environmental_response_obligations
from .narrator_environment_context import (
    immediate_user_turn_contribution,
    triggering_user_contribution,
)
from .narrator_environment_packet import assemble_narrator_environment_packet
from .session_state import CharacterTurnRecord, LiveSession, RoundFixture
from .storyteller_round_packaging import storyteller_contributions_for_consumer


def _environmental_obligation_text(req: NarratorContextPrepareRequest) -> str:
    text = str(req.environmental_response_obligations_text or "").strip()
    if text:
        return text
    raw_obligations = req.environmental_response_obligations
    if not isinstance(raw_obligations, list) or not raw_obligations:
        return ""
    from domain_api.narrator_environment_contract import EnvironmentalResponseObligation

    obligations = [
        EnvironmentalResponseObligation(
            obligation_id=str(item.get("obligation_id") or ""),
            need_id=str(item.get("need_id") or "") or None,
            rendering_question=str(item.get("rendering_question") or ""),
            render_behavior=item.get("render_behavior", "bounded_refusal"),  # type: ignore[arg-type]
            grounded_material=tuple(
                str(part)
                for part in list(item.get("grounded_material") or [])
                if str(part).strip()
            ),
            resolution_category=item.get("resolution_category", "cannot_safely_resolve"),  # type: ignore[arg-type]
            response_sufficient=bool(item.get("response_sufficient")),
            mediation_outcome=item.get("mediation_outcome"),  # type: ignore[arg-type]
            sufficiency_state=item.get("sufficiency_state", "unresolved"),  # type: ignore[arg-type]
            established_b2_property_key=str(item.get("established_b2_property_key") or "")
            or None,
            established_b2_value=str(item.get("established_b2_value") or "") or None,
            refusal_reason=str(item.get("refusal_reason") or "") or None,
        )
        for item in raw_obligations
        if isinstance(item, dict)
    ]
    return format_environmental_response_obligations(obligations)


def prepare_narrator_context(
    fixture: LiveSession,
    rnd: RoundFixture,
    turn_record: CharacterTurnRecord,
    req: NarratorContextPrepareRequest,
    *,
    story_records: list[Any] | None,
):
    mgr = fixture.manager
    assert mgr.scene_state is not None
    manifest_id = f"manifest-narrator-{req.inference_id}-{req.attempt_index}"
    present_labels = list(
        getattr(mgr.scene_state, "present_characters", None) or fixture.cast
    )
    director_decision = dict(turn_record.director_decision)
    environment_event = str(director_decision.get("environment_event", "") or "")
    narrate_move = redact_structured_move_for_orchestration(
        dict(turn_record.committed_move),
        present_characters=present_labels,
    )
    env_packet, env_view = assemble_narrator_environment_packet(
        fixture,
        story_records=story_records,
    )
    env_context = build_cognition_context_payload(
        fixture,
        rnd,
        turn_record,
        story_records=story_records,
    )
    auth_projections = project_authoritative_context(
        fixture,
        role="narrator",
        character_id=req.character_id,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        continuity_turn_index=turn_record.continuity_turn_index,
    )
    scene_context = next(
        (proj.content for proj in auth_projections if proj.source_kind == "scene_state"),
        (
            f"Location: {mgr.scene_state.location or 'unknown'}. "
            f"Present: {', '.join(present_labels)}. "
            f"Continuity turn counter after commit: {turn_record.continuity_turn_index}."
        ),
    )
    obligation_text = _environmental_obligation_text(req)
    render_instruction = build_narrator_render_prompt(
        char_name=req.character_id,
        action="",
        dialogue="",
        environment_event=environment_event,
        scene_context=scene_context,
        structured_move=narrate_move,
        environmental_baseline=env_packet.render_summary(),
        environmental_response_obligations=None,
    )
    committed_move_json = json.dumps(narrate_move, ensure_ascii=False, indent=2)
    contributions: list[PromptContribution] = list(
        auth_projections_to_contributions(manifest_id, auth_projections)
    )
    contributions.extend(
        storyteller_contributions_for_consumer(
            fixture,
            rnd,
            manifest_id=manifest_id,
            consumer_target="narrator",
        )
    )
    narrator_contributions: list[PromptContribution] = [
            PromptContribution(
                contribution_id=f"{manifest_id}-environmental-baseline",
                source_kind="narrator_environment_baseline",
                authority_class="authoritative",
                knowledge_ids=(f"env:{env_view.location_ref}",),
                priority=17,
                content=env_packet.render_summary(),
                provenance={
                    "domain_commit_id": req.domain_commit_id,
                    "visibility": "orchestration_projection",
                    "assembly_metadata": env_packet.assembly_metadata,
                },
            ),
    ]
    immediate = env_context.get("immediate_user_turn")
    if isinstance(immediate, dict) and immediate:
        narrator_contributions.append(
            immediate_user_turn_contribution(
                manifest_id,
                domain_commit_id=req.domain_commit_id,
                immediate_user_turn=immediate,
                priority=18,
            )
        )
    narrator_contributions.extend(
        [
            triggering_user_contribution(
                manifest_id,
                domain_commit_id=req.domain_commit_id,
                triggering_user=env_context.get("triggering_user"),
                committed_occurrence=env_context.get("committed_occurrence"),
                priority=19,
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-committed-move",
                source_kind="committed_move",
                authority_class="authoritative",
                knowledge_ids=(f"commit:{req.domain_commit_id}",),
                priority=20,
                content=(
                    f"Committed character move for {req.character_id} "
                    f"(domain_commit_id={req.domain_commit_id}):\n{committed_move_json}"
                ),
                provenance={
                    "character_id": req.character_id,
                    "domain_commit_id": req.domain_commit_id,
                    "visibility": "presentation",
                },
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-director-decision",
                source_kind="director_decision",
                authority_class="derived",
                knowledge_ids=(f"round:{req.hg_round_id}",),
                priority=25,
                content=(
                    "Accepted director decision for this round: "
                    f"{json.dumps(director_decision, ensure_ascii=False)}"
                ),
                provenance={
                    "hg_round_id": req.hg_round_id,
                    "visibility": "orchestration_projection",
                },
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-instruction",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=(f"inference:{req.inference_id}",),
                priority=30,
                content=render_instruction,
                provenance={"inference_id": req.inference_id, "role": "narrator"},
            ),
        ]
    )
    contributions.extend(narrator_contributions)
    if obligation_text:
        contributions.insert(
            -1,
            PromptContribution(
                contribution_id=f"{manifest_id}-environmental-response-obligation",
                source_kind="environmental_response_obligation",
                authority_class="derived",
                knowledge_ids=(req.inference_id,),
                priority=27,
                content=obligation_text,
                provenance={
                    "inference_id": req.inference_id,
                    "visibility": "presentation",
                },
            ),
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
    return finalize_prompt_contribution_manifest(
        "narrator_presentation",
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        role="narrator",
        character_id=req.character_id,
        turn_index=rnd.turn_index,
        attempt_index=req.attempt_index,
        contributions=contributions,
    )

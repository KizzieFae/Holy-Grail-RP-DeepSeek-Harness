"""Narrator environmental cognition context assembly (#54 C2 / #49)."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .contract import (
    NarratorEnvironmentCognitionPrepareRequest,
    PromptContribution,
    PromptContributionManifest,
)
from .narrator_environment_cognition import (
    NARRATOR_ENVIRONMENT_COGNITION_RUBRIC,
    build_cognition_context_payload,
    build_librarian_knowledge_access_request,
    parse_n1_cognition_result,
)
from .session_state import CharacterTurnRecord, LiveSession, RoundFixture


def triggering_user_contribution(
    manifest_id: str,
    *,
    domain_commit_id: str,
    triggering_user: Any,
    committed_occurrence: Any,
    priority: int = 18,
) -> PromptContribution:
    return PromptContribution(
        contribution_id=f"{manifest_id}-triggering-user",
        source_kind="triggering_user_context",
        authority_class="authoritative",
        knowledge_ids=(f"commit:{domain_commit_id}",),
        priority=priority,
        content=json.dumps(
            {
                "triggering_user": triggering_user,
                "committed_occurrence": committed_occurrence,
            },
            ensure_ascii=False,
            indent=2,
        ),
        provenance={
            "domain_commit_id": domain_commit_id,
            "visibility": "orchestration_projection",
        },
    )


def prepare_environment_cognition_context(
    fixture: LiveSession,
    rnd: RoundFixture,
    turn_record: CharacterTurnRecord,
    req: NarratorEnvironmentCognitionPrepareRequest,
    *,
    story_records: list[Any] | None,
) -> dict[str, Any]:
    context = build_cognition_context_payload(
        fixture,
        rnd,
        turn_record,
        story_records=story_records,
    )
    manifest_id = f"manifest-narrator-env-cog-{req.inference_id}-{req.domain_commit_id}"
    contributions = [
        PromptContribution(
            contribution_id=f"{manifest_id}-environmental-baseline",
            source_kind="narrator_environment_baseline",
            authority_class="authoritative",
            knowledge_ids=(f"env:{context['environmental_current_view']['location_ref']}",),
            priority=18,
            content=json.dumps(
                {
                    "environmental_packet": context["environmental_packet"],
                    "environmental_current_view": context["environmental_current_view"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            provenance={
                "domain_commit_id": req.domain_commit_id,
                "visibility": "orchestration_projection",
            },
        ),
        triggering_user_contribution(
            manifest_id,
            domain_commit_id=req.domain_commit_id,
            triggering_user=context.get("triggering_user"),
            committed_occurrence=context.get("committed_occurrence"),
            priority=19,
        ),
        PromptContribution(
            contribution_id=f"{manifest_id}-instruction",
            source_kind="narrator_environment_cognition",
            authority_class="derived",
            knowledge_ids=(f"inference:{req.inference_id}",),
            priority=30,
            content=NARRATOR_ENVIRONMENT_COGNITION_RUBRIC,
            provenance={"inference_id": req.inference_id, "role": "narrator"},
        ),
    ]
    manifest = PromptContributionManifest(
        manifest_id=manifest_id,
        inference_id=req.inference_id,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        role="narrator",
        character_id=req.character_id,
        turn_index=rnd.turn_index,
        attempt_index=0,
        contributions=contributions,
    )
    n1 = parse_n1_cognition_result({"baseline_sufficient": True, "information_needs": []})
    knowledge_requests: list[dict[str, Any]] = []
    if not n1.baseline_sufficient:
        for need in n1.information_needs:
            kar = build_librarian_knowledge_access_request(
                fixture=fixture,
                rnd=rnd,
                need=need,
                location_ref=str(context["environmental_current_view"].get("location_ref", "")),
                inference_id=req.inference_id,
                character_id=req.character_id,
                turn_index=rnd.turn_index,
            )
            knowledge_requests.append(asdict(kar))
    return {
        "manifest": manifest,
        "context": context,
        "knowledge_access_requests": knowledge_requests,
    }


def build_environment_knowledge_requests(
    fixture: LiveSession,
    rnd: RoundFixture,
    turn_record: CharacterTurnRecord,
    req: NarratorEnvironmentCognitionPrepareRequest,
    *,
    n1_raw: dict[str, Any],
) -> list[dict[str, Any]]:
    context_payload = build_cognition_context_payload(fixture, rnd, turn_record)
    n1 = parse_n1_cognition_result(n1_raw)
    if n1.baseline_sufficient:
        return []
    location_ref = str(context_payload["environmental_current_view"].get("location_ref", ""))
    return [
        asdict(
            build_librarian_knowledge_access_request(
                fixture=fixture,
                rnd=rnd,
                need=need,
                location_ref=location_ref,
                inference_id=req.inference_id,
                character_id=req.character_id,
                turn_index=rnd.turn_index,
            )
        )
        for need in n1.information_needs
    ]

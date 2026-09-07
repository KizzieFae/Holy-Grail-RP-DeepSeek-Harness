"""Narrator environmental cognition — N1 assessment and N2 resolution (#49)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from domain_api.librarian_contract import (
    ALL_INFORMATION_CLASSES,
    BudgetExpectations,
    DegradationPreferences,
    InformationNeed,
    KnowledgeAccessRequest,
    VisibilityEnvelope,
)
from domain_api.retrieval_contract import EntityRef
from domain_api.narrator_environment_contract import (
    CognitionStatusReason,
    MediationOutcomeKind,
    NarratorEnvironmentCognitionAudit,
    NarratorEnvironmentN1Result,
    NarratorEnvironmentResolution,
    NarratorInformationNeed,
)
from domain_api.narrator_environment_authority import (
    EnvironmentalB2EstablishmentDecision,
    NarratorEnvironmentalB2Proposal,
    evaluate_host_environmental_b2_establishment,
    mediation_allows_bounded_composition,
    mediation_blocks_invention,
)
from domain_api.narrator_environment_establishment import (
    persist_host_accepted_b2_environmental_descriptor,
    reject_c_establishment_via_narrator,
)
from domain_api.narrator_environment_projection import build_environmental_current_view
from domain_api.narrator_environment_packet import assemble_narrator_environment_packet
from domain_api.narrator_environment_sufficiency import (
    build_cognition_unavailable_obligation,
    build_sufficiency_undetermined_obligation,
    format_environmental_response_obligations,
    reconcile_post_mediation_environmental_resolutions,
    refresh_obligations_after_b2,
)
from domain_api.story_knowledge_service import StoryKnowledgeService
from .session_history import project_immediate_user_turn_context


_FINISH_LIMIT_KINDS = frozenset({"max-tokens", "max_tokens", "max_tokens_reached"})
_VALID_RESOLUTION_CATEGORIES = frozenset({"A", "B1", "B2", "C", "cannot_safely_resolve"})
_STATUS_DETAIL_MAX_CHARS = 240


def _normalize_finish_kind(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("kind", "") or "").strip().lower()
    return str(value or "").strip().lower()


def _bounded_status_detail(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) <= _STATUS_DETAIL_MAX_CHARS:
        return text
    return text[: _STATUS_DETAIL_MAX_CHARS - 1] + "…"


def _parse_information_needs(raw: dict[str, Any]) -> list[NarratorInformationNeed]:
    needs: list[NarratorInformationNeed] = []
    for index, item in enumerate(list(raw.get("information_needs") or [])):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "") or "").strip()
        if not question:
            continue
        need_id = str(item.get("need_id", "") or f"need-{index + 1}")
        refs = tuple(
            str(ref).strip()
            for ref in list(item.get("referent_refs") or [])
            if str(ref).strip()
        )
        needs.append(NarratorInformationNeed(need_id=need_id, question=question, referent_refs=refs))
    return needs


def _contract_schema_valid(parsed: dict[str, Any]) -> bool:
    if "baseline_sufficient" not in parsed:
        return False
    if not isinstance(parsed.get("baseline_sufficient"), bool):
        return False
    resolutions = parsed.get("resolutions")
    if resolutions is None or not isinstance(resolutions, list):
        return False
    for item in resolutions:
        if not isinstance(item, dict):
            return False
        category = str(item.get("category", "") or "")
        if category and category not in _VALID_RESOLUTION_CATEGORIES:
            return False
    return True


def _determined_outcome_from_parsed(parsed: dict[str, Any]) -> NarratorEnvironmentN1Result | None:
    if not _contract_schema_valid(parsed):
        return None
    baseline_sufficient = bool(parsed.get("baseline_sufficient"))
    needs = _parse_information_needs(parsed)
    if baseline_sufficient and needs:
        return None
    if baseline_sufficient:
        return NarratorEnvironmentN1Result(
            cognition_status="determined",
            status_reason="model_result",
            baseline_sufficient=True,
            information_needs=[],
            assessment_notes=str(parsed.get("assessment_notes", "") or ""),
        )
    if not needs:
        return None
    return NarratorEnvironmentN1Result(
        cognition_status="determined",
        status_reason="model_result",
        baseline_sufficient=False,
        information_needs=needs,
        assessment_notes=str(parsed.get("assessment_notes", "") or ""),
    )


def _indeterminate_outcome(
    reason: CognitionStatusReason,
    *,
    status_detail: str = "",
) -> NarratorEnvironmentN1Result:
    return NarratorEnvironmentN1Result(
        cognition_status="indeterminate",
        status_reason=reason,
        baseline_sufficient=None,
        information_needs=[],
        assessment_notes="",
        status_detail=_bounded_status_detail(status_detail),
    )


def classify_environment_cognition_outcome(
    cognition_raw: str | dict[str, Any] | None,
    inference_envelope: dict[str, Any] | None = None,
) -> tuple[NarratorEnvironmentN1Result, dict[str, Any] | None]:
    """Deterministically classify environmental cognition (#151)."""
    envelope = dict(inference_envelope or {})
    inference_failed = bool(envelope.get("inference_failed"))
    finish_kind = _normalize_finish_kind(envelope.get("finish_kind"))

    parsed: dict[str, Any] | None = None
    raw_text = ""
    if isinstance(cognition_raw, dict):
        parsed = cognition_raw
        raw_text = json.dumps(cognition_raw, ensure_ascii=False)
    elif cognition_raw is not None:
        raw_text = str(cognition_raw).strip()
        if raw_text:
            try:
                loaded = json.loads(raw_text)
            except json.JSONDecodeError:
                return _indeterminate_outcome("malformed_output", status_detail=raw_text[:120]), None
            parsed = loaded if isinstance(loaded, dict) else None

    if parsed is not None:
        determined = _determined_outcome_from_parsed(parsed)
        if determined is not None:
            return determined, parsed
        if raw_text:
            return _indeterminate_outcome("contract_invalid", status_detail=raw_text[:120]), None

    if inference_failed:
        return _indeterminate_outcome("inference_error"), None
    if finish_kind in _FINISH_LIMIT_KINDS:
        return _indeterminate_outcome("provider_limit"), None
    return _indeterminate_outcome("empty_output"), None


def parse_n1_cognition_result(raw: dict[str, Any]) -> NarratorEnvironmentN1Result:
    outcome, _ = classify_environment_cognition_outcome(raw, None)
    return outcome


def _public_event_for_commit(
    fixture: LiveSession,
    domain_commit_id: str,
    continuity_turn_index: int | None = None,
) -> Any | None:
    commit_id = str(domain_commit_id or "").strip()
    if continuity_turn_index is not None:
        for event in reversed(fixture.manager.public_events):
            if getattr(event, "turn_index", None) == continuity_turn_index:
                return event
    for event in fixture.manager.public_events:
        if str(getattr(event, "source_domain_commit_id", "") or "") == commit_id:
            return event
        meta = getattr(event, "metadata", None) or {}
        if isinstance(meta, dict) and str(meta.get("domain_commit_id", "") or "") == commit_id:
            return event
    return None


def extract_triggering_user_context(
    fixture: LiveSession,
    turn_record: CharacterTurnRecord,
) -> dict[str, Any] | None:
    event = _public_event_for_commit(
        fixture,
        turn_record.domain_commit_id,
        turn_record.continuity_turn_index,
    )
    if event is None or getattr(event, "occurrence_evidence", None) is None:
        return None
    trigger = event.occurrence_evidence.triggering_user
    if trigger is None:
        return None
    return trigger.to_dict()


def extract_committed_occurrence_summary(
    fixture: LiveSession,
    turn_record: CharacterTurnRecord,
) -> dict[str, Any]:
    event = _public_event_for_commit(
        fixture,
        turn_record.domain_commit_id,
        turn_record.continuity_turn_index,
    )
    payload: dict[str, Any] = {
        "character_id": turn_record.character_id,
        "domain_commit_id": turn_record.domain_commit_id,
        "continuity_turn_index": turn_record.continuity_turn_index,
    }
    if event is not None:
        payload["summary"] = str(event.summary or "")
        if getattr(event, "occurrence_evidence", None) is not None:
            evidence = event.occurrence_evidence
            payload["contributions"] = [
                item.to_dict() for item in evidence.contributions
            ]
            if evidence.triggering_user is not None:
                payload["triggering_user"] = evidence.triggering_user.to_dict()
    return payload


def parse_n2_cognition_results(raw: dict[str, Any]) -> list[NarratorEnvironmentResolution]:
    resolutions: list[NarratorEnvironmentResolution] = []
    for item in list(raw.get("resolutions") or []):
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "") or "cannot_safely_resolve")
        if category not in {"A", "B1", "B2", "C", "cannot_safely_resolve"}:
            category = "cannot_safely_resolve"
        refs = tuple(
            str(ref).strip()
            for ref in list(item.get("stable_refs") or [])
            if str(ref).strip()
        )
        mediation = item.get("mediation_outcome")
        if mediation not in {
            "match",
            "no_match",
            "ambiguous",
            "forbidden",
            "retrieval_failure",
            "mediation_failure",
        }:
            mediation = None
        response_sufficient = item.get("response_sufficient")
        if response_sufficient is not None:
            response_sufficient = bool(response_sufficient)
        resolutions.append(
            NarratorEnvironmentResolution(
                need_id=str(item.get("need_id", "") or "") or None,
                category=category,  # type: ignore[arg-type]
                detail=str(item.get("detail", "") or ""),
                property_key=str(item.get("property_key", "") or "") or None,
                value=str(item.get("value", "") or "") or None,
                stable_refs=refs,
                mediation_outcome=mediation,  # type: ignore[arg-type]
                establishment_record_id=str(item.get("establishment_record_id", "") or "") or None,
                supersedes=str(item.get("supersedes", "") or "") or None,
                reasoning_summary=str(item.get("reasoning_summary", "") or ""),
                response_sufficient=response_sufficient,
            )
        )
    return resolutions


def build_librarian_knowledge_access_request(
    *,
    fixture: LiveSession,
    rnd: RoundFixture,
    need: NarratorInformationNeed,
    location_ref: str,
    inference_id: str,
    character_id: str,
    turn_index: int,
) -> KnowledgeAccessRequest:
    entity_refs = _entity_refs_for_retrieval(
        tuple(need.referent_refs) or (location_ref,)
    )
    envelope = VisibilityEnvelope(
        viewer_role="orchestration",
        authority_ceiling_enforced="derived",
        viewer_character_id=character_id,
        subject_character_id=character_id,
    )
    return KnowledgeAccessRequest(
        request_id=f"nar-env-{need.need_id}-{inference_id}",
        consumer_role="narrator",
        consumer_instance_id=character_id,
        audit_reason="narrator_environment_cognition",
        hg_scene_id=fixture.hg_scene_id,
        hg_round_id=rnd.hg_round_id,
        turn_index=turn_index,
        pipeline_stage="host_default",
        visibility_envelope=envelope,
        information_need=InformationNeed(
            focus_questions=(need.question,),
            entity_refs=entity_refs,
        ),
        correlation_inference_id=inference_id,
        requested_information_classes=frozenset(
            {"authored_static", "compiled_index", "story_derived"}
        ),
        host_allowed_information_classes=ALL_INFORMATION_CLASSES,
        budget_expectations=BudgetExpectations(max_bundle_entries=8, max_bundle_chars=4000),
        degradation_preferences=DegradationPreferences(),
    )


def _entity_refs_for_retrieval(refs: tuple[str, ...]) -> tuple[EntityRef, ...]:
    return tuple(
        EntityRef(
            ref_kind=ref.split(":", 1)[0] if ":" in ref else "entity",
            stable_ref=ref,
        )
        for ref in refs
        if ref
    )


def apply_n2_establishment_decisions(
    fixture: LiveSession,
    service: StoryKnowledgeService,
    *,
    resolutions: list[NarratorEnvironmentResolution],
    turn_record: CharacterTurnRecord,
    cognition_id: str,
) -> list[dict[str, Any]]:
    story_records = service.list_records(str(fixture.memory_scope_id or ""))
    current_view = build_environmental_current_view(fixture, story_records=story_records)
    decisions: list[dict[str, Any]] = []
    for resolution in resolutions:
        if resolution.category == "B2":
            if not resolution.property_key or not resolution.value:
                decisions.append(
                    {
                        "resolution_need_id": resolution.need_id,
                        "accepted": False,
                        "reason": "missing_property_key_or_value",
                        "authority_decision": None,
                    }
                )
                continue
            refs = resolution.stable_refs
            if not refs and fixture.manager.scene_state is not None:
                from .narrator_environment_location_binding import bind_location_stable_ref

                refs = (bind_location_stable_ref(fixture.manager.scene_state.location).stable_ref,)
            proposal = NarratorEnvironmentalB2Proposal(
                cognition_id=cognition_id,
                need_id=resolution.need_id,
                property_key=resolution.property_key,
                value=resolution.value,
                stable_refs=refs,
                mediation_outcome=resolution.mediation_outcome,
                detail=resolution.detail,
                supersedes=resolution.supersedes,
            )
            authority_decision = evaluate_host_environmental_b2_establishment(
                proposal,
                current_view=current_view,
            )
            decision_audit = authority_decision.to_audit_dict()
            if not authority_decision.authorized:
                decisions.append(
                    {
                        "resolution_need_id": resolution.need_id,
                        "accepted": False,
                        "reason": authority_decision.reason_code,
                        "authority_decision": decision_audit,
                    }
                )
                continue
            result = persist_host_accepted_b2_environmental_descriptor(
                fixture,
                service,
                establishment_decision=authority_decision,
                property_key=resolution.property_key,
                value=resolution.value,
                stable_refs=refs,
                source_domain_commit_id=turn_record.domain_commit_id,
                turn_index=turn_record.continuity_turn_index,
                cognition_id=cognition_id,
                supersedes=resolution.supersedes,
            )
            result["authority_decision"] = decision_audit
            result["resolution_need_id"] = resolution.need_id
            if result.get("accepted"):
                resolution.establishment_record_id = result.get("story_record_id")
                story_records = service.list_records(str(fixture.memory_scope_id or ""))
                current_view = build_environmental_current_view(
                    fixture, story_records=story_records
                )
            decisions.append(result)
        elif resolution.category == "C":
            decisions.append(
                {
                    **reject_c_establishment_via_narrator(),
                    "resolution_need_id": resolution.need_id,
                }
            )
        elif resolution.category == "B1":
            decisions.append(
                {
                    "accepted": True,
                    "reason": "b1_ephemeral_no_persistence",
                    "resolution_need_id": resolution.need_id,
                }
            )
    return decisions


def build_cognition_context_payload(
    fixture: LiveSession,
    rnd: RoundFixture,
    turn_record: CharacterTurnRecord,
    *,
    story_records: list[Any] | None = None,
) -> dict[str, Any]:
    packet, view = assemble_narrator_environment_packet(fixture, story_records=story_records)
    return {
        "environmental_packet": packet.to_dict(),
        "environmental_current_view": view.to_dict(),
        "immediate_user_turn": project_immediate_user_turn_context(fixture.rp_history),
        "triggering_user": extract_triggering_user_context(fixture, turn_record),
        "committed_occurrence": extract_committed_occurrence_summary(fixture, turn_record),
        "committed_move": turn_record.committed_move,
        "director_decision": turn_record.director_decision,
        "hg_round_id": rnd.hg_round_id,
        "character_id": turn_record.character_id,
        "domain_commit_id": turn_record.domain_commit_id,
    }


def finalize_narrator_environment_cognition(
    fixture: LiveSession,
    turn_record: CharacterTurnRecord,
    *,
    story_service: StoryKnowledgeService,
    n1_raw: dict[str, Any] | None = None,
    n2_raw: dict[str, Any] | None = None,
    cognition_raw: str | dict[str, Any] | None = None,
    inference_envelope: dict[str, Any] | None = None,
    librarian_outcomes: list[dict[str, Any]] | None = None,
    cognition_id: str | None = None,
    inference_attempt_id: str | None = None,
) -> dict[str, Any]:
    cognition_id = cognition_id or f"nar-env-cog-{uuid.uuid4().hex[:12]}"
    if cognition_raw is not None or inference_envelope is not None:
        n1, parsed_payload = classify_environment_cognition_outcome(
            cognition_raw if cognition_raw is not None else (n1_raw or {}),
            inference_envelope,
        )
        n2_source = parsed_payload or {}
    else:
        merged_raw = dict(n1_raw or {})
        if isinstance(n2_raw, dict) and n2_raw.get("resolutions") is not None:
            merged_raw["resolutions"] = list(n2_raw.get("resolutions") or [])
        n1, parsed_payload = classify_environment_cognition_outcome(merged_raw, None)
        n2_source = parsed_payload or merged_raw

    _, view = assemble_narrator_environment_packet(
        fixture,
        story_records=story_service.list_records(str(fixture.memory_scope_id or "")),
    )

    if n1.cognition_status == "indeterminate":
        obligations = [build_sufficiency_undetermined_obligation(n1.status_reason)]
        audit = NarratorEnvironmentCognitionAudit(
            cognition_id=cognition_id,
            location_ref=view.location_ref,
            cognition_status="indeterminate",
            status_reason=n1.status_reason,
            cognition_failed=False,
            inference_attempt_id=inference_attempt_id,
            n1=n1,
            environmental_response_obligations=obligations,
            immediate_user_turn=project_immediate_user_turn_context(fixture.rp_history),
            triggering_user=extract_triggering_user_context(fixture, turn_record),
            domain_commit_id=turn_record.domain_commit_id,
        )
        turn_meta = fixture.manager.turn_metadata_by_index.setdefault(
            turn_record.continuity_turn_index,
            {},
        )
        turn_meta["narrator_environment_audit"] = audit.to_dict()
        return {
            "accepted": True,
            "cognition_id": cognition_id,
            "cognition_status": "indeterminate",
            "status_reason": n1.status_reason,
            "baseline_sufficient": None,
            "audit": audit.to_dict(),
            "establishment_decisions": [],
            "environmental_response_obligations": [item.to_dict() for item in obligations],
            "environmental_response_obligations_text": format_environmental_response_obligations(
                obligations
            ),
            "updated_environmental_view": view.to_dict(),
        }

    n2 = parse_n2_cognition_results(n2_source)
    n2_raw_items = [
        item for item in list(n2_source.get("resolutions") or []) if isinstance(item, dict)
    ]

    story_records = story_service.list_records(str(fixture.memory_scope_id or ""))
    current_view = build_environmental_current_view(fixture, story_records=story_records)

    n2, sufficiency_evaluations, obligations = reconcile_post_mediation_environmental_resolutions(
        n1=n1,
        resolutions=n2,
        librarian_outcomes=librarian_outcomes,
        n2_raw_items=n2_raw_items,
        current_view=current_view,
    )

    decisions = apply_n2_establishment_decisions(
        fixture,
        story_service,
        resolutions=n2,
        turn_record=turn_record,
        cognition_id=cognition_id,
    )

    obligations = refresh_obligations_after_b2(
        obligations,
        resolutions=n2,
        establishment_decisions=decisions,
    )

    _, view = assemble_narrator_environment_packet(
        fixture,
        story_records=story_service.list_records(str(fixture.memory_scope_id or "")),
    )

    audit = NarratorEnvironmentCognitionAudit(
        cognition_id=cognition_id,
        location_ref=view.location_ref,
        cognition_status="determined",
        status_reason="model_result",
        cognition_failed=False,
        inference_attempt_id=inference_attempt_id,
        n1=n1,
        librarian_queries=list(librarian_outcomes or []),
        n2_resolutions=n2,
        establishment_decisions=decisions,
        sufficiency_evaluations=sufficiency_evaluations,
        environmental_response_obligations=obligations,
        immediate_user_turn=project_immediate_user_turn_context(fixture.rp_history),
        triggering_user=extract_triggering_user_context(fixture, turn_record),
        domain_commit_id=turn_record.domain_commit_id,
    )

    turn_meta = fixture.manager.turn_metadata_by_index.setdefault(
        turn_record.continuity_turn_index,
        {},
    )
    turn_meta["narrator_environment_audit"] = audit.to_dict()

    return {
        "accepted": True,
        "cognition_id": cognition_id,
        "cognition_status": "determined",
        "status_reason": "model_result",
        "baseline_sufficient": n1.baseline_sufficient,
        "audit": audit.to_dict(),
        "establishment_decisions": decisions,
        "environmental_response_obligations": [item.to_dict() for item in obligations],
        "environmental_response_obligations_text": format_environmental_response_obligations(
            obligations
        ),
        "updated_environmental_view": view.to_dict(),
    }


def record_environment_cognition_failure(
    fixture: LiveSession,
    turn_record: CharacterTurnRecord,
    *,
    failure_stage: str,
    failure_reason: str,
    cognition_id: str | None = None,
) -> dict[str, Any]:
    """Durable audit when environmental cognition hard-fails before classification (#49 / #151)."""
    cognition_id = cognition_id or f"nar-env-cog-{uuid.uuid4().hex[:12]}"
    n1 = NarratorEnvironmentN1Result(
        cognition_status="failed",
        status_reason="pipeline_exception",
        baseline_sufficient=None,
        information_needs=[],
        assessment_notes="",
        status_detail=_bounded_status_detail(failure_reason),
    )
    obligations = [build_cognition_unavailable_obligation(failure_reason)]
    _, view = assemble_narrator_environment_packet(fixture, story_records=[])
    audit = NarratorEnvironmentCognitionAudit(
        cognition_id=cognition_id,
        location_ref=view.location_ref,
        cognition_status="failed",
        status_reason="pipeline_exception",
        cognition_failed=True,
        failure_stage=failure_stage,
        failure_reason=failure_reason,
        n1=n1,
        environmental_response_obligations=obligations,
        domain_commit_id=turn_record.domain_commit_id,
    )
    audit_dict = audit.to_dict()
    audit_dict["environmental_response_obligations_text"] = format_environmental_response_obligations(
        obligations
    )
    turn_meta = fixture.manager.turn_metadata_by_index.setdefault(
        turn_record.continuity_turn_index,
        {},
    )
    turn_meta["narrator_environment_audit"] = audit_dict
    return audit_dict


NARRATOR_ENVIRONMENT_COGNITION_RUBRIC = (
    "Structured Narrator environmental cognition (#49). Two stages in one JSON object.\n"
    "Input authority (#71 dual-input):\n"
    "- immediate_user_turn_context (when present): current-turn player action/speech; "
    "semantic signal for perceptual/descriptive obligation — NOT durable world truth.\n"
    "- triggering_user_context (when present): authoritative promoted occurrence evidence (#51); "
    "precedence for durable factual claims; overlapping wording does not create two events.\n"
    "Stage N1 — baseline assessment:\n"
    "- Semantically assess whether the immediate user action requires environmental/perceptual response.\n"
    "- baseline_sufficient: true only when baseline + inputs already answer material needs.\n"
    "- information_needs: semantic questions when insufficient; never keyword/regex rules.\n"
    "Stage N2 — grounded resolution for each need:\n"
    "- category A: established grounded detail from packet or Librarian match.\n"
    "- category B1: ephemeral immersive texture (no persistence).\n"
    "- category B2: continuity-bearing persistent property — requires property_key, value, stable_refs.\n"
    "- category C: material story fact — mark only; Host establishes separately.\n"
    "- cannot_safely_resolve: when ambiguity/forbidden/retrieval_failure/mediation_failure.\n"
    "Post-mediation sufficiency (#89): Librarian match means relevant knowledge was found, "
    "NOT that the rendering need is sufficient. Set response_sufficient per need.\n"
    "When response_sufficient is true, prefer category A using matched grounded detail.\n"
    "When response_sufficient is false and bounded detail is needed, propose minimum B2 "
    "compatible with existing truth (match does NOT prohibit B2).\n"
    "Never invent on retrieval/mediation failure. Never reinterpret match as no_match.\n"
    "Output JSON: {baseline_sufficient, information_needs[], resolutions[], assessment_notes}.\n"
    "Each resolution may include response_sufficient (boolean)."
)

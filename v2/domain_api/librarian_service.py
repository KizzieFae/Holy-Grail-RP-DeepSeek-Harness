"""Librarian read-side service (#34 S2a).

Orchestrates KnowledgeAccessRequest mediation across authoritative projection,
validated #31 Retrieval, DSH contextual inference results, and deterministic fallback.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .librarian_authoritative_input import (
    authoritative_snapshot_id,
    collect_authoritative_working_items,
)
from .librarian_contract import (
    BudgetAccounting,
    BundleAudit,
    BundleDegradation,
    BundleDegradationLevel,
    BundleDegradationMode,
    BundleValidity,
    HostMediationValidation,
    InvalidationKey,
    KnowledgeAccessRequest,
    LibrarianKnowledgeBundle,
    LibrarianMediationPrepareResponse,
    LibrarianMediationResult,
    MediationMode,
    RequestSatisfactionSummary,
    SourceDiagnostics,
    SourceStatus,
    compute_bundle_hash,
    new_bundle_id,
    validate_knowledge_access_request,
)
from .librarian_mapper import (
    build_retrieval_access_requests,
    effective_information_classes,
    merge_retrieval_candidate_ids,
)
from .librarian_mediation import (
    assess_focus_question_satisfaction,
    build_bundle_entries_from_contextual_result,
    build_fallback_bundle_entries,
)
from .librarian_mediation_catalog import MediationWorkingSet, build_mediation_working_set
from .librarian_mediation_context import build_mediation_manifest_contributions
from .librarian_mediation_validate import (
    parse_librarian_mediation_result,
    validate_librarian_mediation_result,
)
from .librarian_contract import LibrarianBundleEntry
from .retrieval_contract import RetrievalAccessResponse, RetrievalCandidate
from .retrieval_service import RetrievalService
from .session_state import LiveSession

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MediationAssembly:
    working_set: MediationWorkingSet
    retrieval_request_ids: tuple[str, ...]
    retrieval_responses: tuple[RetrievalAccessResponse, ...]
    per_source: tuple[SourceStatus, ...]
    consulted: tuple[str, ...]
    omitted: tuple[str, ...]


def _dedupe_candidates(candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]:
    seen: set[str] = set()
    deduped: list[RetrievalCandidate] = []
    for candidate in candidates:
        if candidate.candidate_id in seen:
            continue
        seen.add(candidate.candidate_id)
        deduped.append(candidate)
    return deduped


def _apply_bundle_budget(
    request: KnowledgeAccessRequest,
    entries: list[LibrarianBundleEntry],
) -> tuple[list[LibrarianBundleEntry], int]:
    budget = request.budget_expectations
    selected: list[LibrarianBundleEntry] = []
    total_chars = 0
    truncated = 0
    for entry in sorted(entries, key=lambda item: item.librarian_annotation.relevance_rank):
        content_len = len(entry.content)
        if len(selected) >= budget.max_bundle_entries:
            truncated += 1
            continue
        if total_chars + content_len > budget.max_bundle_chars:
            truncated += 1
            continue
        selected.append(entry)
        total_chars += content_len
    return selected, truncated


class LibrarianService:
    """Read-side semantic mediator — no Continuity writes."""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self._retrieval = retrieval_service or RetrievalService()

    def assemble_mediation_inputs(
        self,
        request: KnowledgeAccessRequest,
        fixture: LiveSession,
    ) -> MediationAssembly:
        validate_knowledge_access_request(request)
        per_source: list[SourceStatus] = []
        consulted: list[str] = []
        omitted: list[str] = []

        authoritative_items = collect_authoritative_working_items(request, fixture)
        if authoritative_items:
            consulted.append("authoritative_live_continuity")
        else:
            omitted.append("authoritative_live_continuity")

        retrieval_responses: list[RetrievalAccessResponse] = []
        merged_candidates: list[RetrievalCandidate] = []
        retrieval_request_ids: list[str] = []
        retrieval_classes = effective_information_classes(request)

        if retrieval_classes:
            retrieval_requests = build_retrieval_access_requests(
                request,
                memory_scope_id=fixture.memory_scope_id,
                character_file_ids=dict(fixture.character_file_ids or {}),
            )
            for retrieval_request in retrieval_requests:
                retrieval_request_ids.append(retrieval_request.request_id)
                try:
                    response = self._retrieval.retrieve(retrieval_request, fixture)
                    retrieval_responses.append(response)
                    merged_candidates.extend(response.candidates)
                    per_source.append(
                        SourceStatus(
                            source_tier="retrieval_candidate",
                            status="ok"
                            if response.degradation_level == "none"
                            else "degraded",
                            detail=response.degradation_level,
                        )
                    )
                except (ValueError, OSError) as exc:
                    _logger.warning("retrieval degraded for %s: %s", retrieval_request.request_id, exc)
                    per_source.append(
                        SourceStatus(
                            source_tier="retrieval_candidate",
                            status="unavailable",
                            detail=str(exc),
                        )
                    )
            consulted.append("retrieval_candidate")
        else:
            omitted.append("retrieval_candidate")

        working_set = build_mediation_working_set(
            authoritative_items,
            _dedupe_candidates(merged_candidates),
        )
        return MediationAssembly(
            working_set=working_set,
            retrieval_request_ids=tuple(retrieval_request_ids),
            retrieval_responses=tuple(retrieval_responses),
            per_source=tuple(per_source),
            consulted=tuple(dict.fromkeys(consulted)),
            omitted=tuple(dict.fromkeys(omitted)),
        )

    def prepare_mediation_context(
        self,
        request: KnowledgeAccessRequest,
        fixture: LiveSession,
        *,
        inference_id: str,
    ) -> LibrarianMediationPrepareResponse:
        assembly = self.assemble_mediation_inputs(request, fixture)
        manifest_id = f"manifest-librarian-{request.request_id}"
        catalog_tuple = tuple(assembly.working_set.catalog.values())
        contributions = build_mediation_manifest_contributions(
            request,
            manifest_id=manifest_id,
            inference_id=inference_id,
            catalog=catalog_tuple,
            authoritative_snapshot_id=authoritative_snapshot_id(fixture, request),
        )
        return LibrarianMediationPrepareResponse(
            manifest_id=manifest_id,
            inference_id=inference_id,
            request_id=request.request_id,
            hg_scene_id=request.hg_scene_id,
            hg_round_id=request.hg_round_id,
            contributions=contributions,
            mediation_catalog=catalog_tuple,
            retrieval_request_ids=assembly.retrieval_request_ids,
            candidate_ids_supplied=assembly.working_set.candidate_ids,
            authoritative_snapshot_id=authoritative_snapshot_id(fixture, request),
        )

    def access_knowledge(
        self,
        request: KnowledgeAccessRequest,
        fixture: LiveSession,
        *,
        mediation_result: LibrarianMediationResult | dict[str, Any] | None = None,
        inference_id: str | None = None,
        allow_deterministic_fallback: bool | None = None,
    ) -> LibrarianKnowledgeBundle:
        assembly = self.assemble_mediation_inputs(request, fixture)
        parsed_result = mediation_result
        host_validation: HostMediationValidation | None = None
        fallback_reason: str | None = None
        mediation_mode: MediationMode = "authoritative_only"
        structured_evidence: dict[str, Any] | None = None

        if isinstance(mediation_result, dict):
            parsed, parse_error = parse_librarian_mediation_result(mediation_result)
            if parsed is None:
                fallback_reason = parse_error or "malformed_mediation_result"
                parsed_result = None
            else:
                parsed_result = parsed

        use_fallback = (
            request.degradation_preferences.allow_heuristic_fallback
            if allow_deterministic_fallback is None
            else allow_deterministic_fallback
        )

        entries: list[LibrarianBundleEntry] = []
        connections = ()
        if isinstance(parsed_result, LibrarianMediationResult):
            host_validation = validate_librarian_mediation_result(
                parsed_result,
                catalog=assembly.working_set.catalog,
                request=request,
            )
            if host_validation.accepted:
                entries, connections = build_bundle_entries_from_contextual_result(
                    request,
                    assembly.working_set.catalog,
                    parsed_result,
                )
                mediation_mode = "contextual_semantic"
                structured_evidence = {
                    "selected_source_ids": [item.source_id for item in parsed_result.selected_items],
                    "synthesis_ids": [item.synthesis_id for item in parsed_result.synthesis_entries],
                }
            else:
                fallback_reason = host_validation.reason

        if not entries and use_fallback and assembly.working_set.mediation_items:
            entries = build_fallback_bundle_entries(
                request,
                assembly.working_set.mediation_items,
            )
            mediation_mode = "deterministic_fallback"
            if fallback_reason is None:
                fallback_reason = "contextual_mediation_unavailable"

        if not entries and assembly.working_set.mediation_items:
            auth_only = [
                item
                for item in assembly.working_set.mediation_items
                if item.authoritative_item is not None
            ]
            if auth_only:
                entries = build_fallback_bundle_entries(request, auth_only)
            mediation_mode = "authoritative_only"
            if fallback_reason is None:
                fallback_reason = "no_usable_semantic_mediation"

        return self._finalize_bundle(
            request,
            fixture,
            assembly=assembly,
            entries=entries,
            connections=connections,
            mediation_mode=mediation_mode,
            host_validation=host_validation,
            inference_id=inference_id,
            fallback_reason=fallback_reason,
            structured_evidence=structured_evidence,
        )

    def _finalize_bundle(
        self,
        request: KnowledgeAccessRequest,
        fixture: LiveSession,
        *,
        assembly: MediationAssembly,
        entries: list[LibrarianBundleEntry],
        connections: tuple[Any, ...],
        mediation_mode: MediationMode,
        host_validation: HostMediationValidation | None,
        inference_id: str | None,
        fallback_reason: str | None,
        structured_evidence: dict[str, Any] | None,
    ) -> LibrarianKnowledgeBundle:
        degradation_mode: BundleDegradationMode = "none"
        degradation_level: BundleDegradationLevel = "none"
        deterministic_fallback_used = mediation_mode == "deterministic_fallback"

        truncated_count = 0
        if entries:
            entries, truncated_count = _apply_bundle_budget(request, entries)
        if truncated_count:
            degradation_mode = "budget_truncated"
            degradation_level = "partial" if entries else "degraded"

        if mediation_mode == "deterministic_fallback":
            degradation_mode = "deterministic_fallback"
            degradation_level = "partial" if entries else "degraded"
        elif mediation_mode == "authoritative_only":
            degradation_mode = "authoritative_only"
            degradation_level = "partial" if entries else "degraded"
        elif any(item.status != "ok" for item in assembly.per_source):
            degradation_level = "partial"

        if not entries:
            degradation_level = "degraded"
            if degradation_mode == "none":
                degradation_mode = "partial_sources"

        satisfaction = RequestSatisfactionSummary(
            focus_questions=assess_focus_question_satisfaction(
                request,
                entries,
                mediation_mode=mediation_mode,
            ),
            truncated=truncated_count > 0,
            truncation_reason="budget" if truncated_count > 0 else None,
        )

        validity = BundleValidity(
            validity_scope="stage_current",
            bound_hg_round_id=request.hg_round_id,
            bound_turn_index=request.turn_index,
            bound_pipeline_stage=request.pipeline_stage,
            bound_domain_commit_id=request.domain_commit_id,
            valid_from_authoritative_snapshot_id=authoritative_snapshot_id(fixture, request),
            invalidation_keys=(
                InvalidationKey(key_kind="continuity_version", key_value=str(fixture.continuity_version)),
                InvalidationKey(key_kind="hg_round_id", key_value=request.hg_round_id),
                InvalidationKey(key_kind="pipeline_stage", key_value=request.pipeline_stage),
            ),
        )

        candidate_ids = merge_retrieval_candidate_ids(assembly.retrieval_responses)
        bundle_id = new_bundle_id()
        strategy = {
            "contextual_semantic": "contextual_semantic_v1",
            "deterministic_fallback": "structured_focus_question_fallback_v1",
            "authoritative_only": "authoritative_only_v1",
        }[mediation_mode]
        audit_payload: dict[str, Any] = {
            "bundle_id": bundle_id,
            "request_id": request.request_id,
            "mediation_mode": mediation_mode,
            "retrieval_request_ids": list(assembly.retrieval_request_ids),
            "candidate_ids_considered": list(candidate_ids),
            "entry_ids": [entry.entry_id for entry in entries],
            "fallback_reason": fallback_reason,
        }
        audit = BundleAudit(
            bundle_hash=compute_bundle_hash(audit_payload),
            retrieval_request_ids=assembly.retrieval_request_ids,
            candidate_ids_considered=candidate_ids,
            original_request_id=request.request_id,
            mediation_mode=mediation_mode,
            mediation_strategy=strategy,
            inference_id=inference_id,
            host_validation=host_validation,
            fallback_reason=fallback_reason,
            structured_mediation_evidence=structured_evidence,
        )

        return LibrarianKnowledgeBundle(
            bundle_id=bundle_id,
            request_id=request.request_id,
            consumer_role=request.consumer_role,
            pipeline_stage=request.pipeline_stage,
            hg_round_id=request.hg_round_id,
            turn_index=request.turn_index,
            mediation_mode=mediation_mode,
            validity=validity,
            degradation=BundleDegradation(
                level=degradation_level,
                mode=degradation_mode,
                per_source=assembly.per_source,
                deterministic_fallback_used=deterministic_fallback_used,
            ),
            satisfaction=satisfaction,
            entries=tuple(entries),
            budget_accounting=BudgetAccounting(
                entries_returned=len(entries),
                entries_considered=len(assembly.working_set.mediation_items),
                chars_returned=sum(len(entry.content) for entry in entries),
                chars_budget=request.budget_expectations.max_bundle_chars,
                entries_truncated=truncated_count,
            ),
            source_diagnostics=SourceDiagnostics(
                consulted_tiers=assembly.consulted,
                omitted_tiers=assembly.omitted,
                per_source=assembly.per_source,
            ),
            audit=audit,
            connections=connections,
        )


def build_host_default_request(
    fixture: LiveSession,
    *,
    pipeline_stage: str = "host_default",
    viewer_character_id: str | None = None,
    subject_character_id: str | None = None,
) -> KnowledgeAccessRequest:
    """Construct the accepted host_default baseline request envelope."""
    from .librarian_contract import (
        BudgetExpectations,
        DegradationPreferences,
        InformationNeed,
        KnowledgeAccessRequest,
        VisibilityEnvelope,
        new_request_id,
    )

    last_round = fixture.rounds[-1] if fixture.rounds else None
    template_id = str((fixture.setup_snapshot or {}).get("scene_template_id") or "").strip() or None
    return KnowledgeAccessRequest(
        request_id=new_request_id(),
        consumer_role="host_default",
        audit_reason="host_default_baseline_bundle",
        hg_scene_id=fixture.hg_scene_id,
        hg_round_id=str(last_round.hg_round_id if last_round else "unbound"),
        turn_index=int(last_round.turn_index if last_round else 0),
        pipeline_stage=pipeline_stage,  # type: ignore[arg-type]
        visibility_envelope=VisibilityEnvelope(
            viewer_role="host_internal",
            authority_ceiling_enforced="derived",
            viewer_character_id=viewer_character_id,
            subject_character_id=subject_character_id,
            session_template_id=template_id,
        ),
        information_need=InformationNeed(
            focus_questions=(
                "What authoritative scene/issue grounding and recent developments does this stage require?",
            ),
            recall_breadth_preference="focused",
        ),
        budget_expectations=BudgetExpectations(max_bundle_entries=24, max_bundle_chars=16000),
        degradation_preferences=DegradationPreferences(),
    )

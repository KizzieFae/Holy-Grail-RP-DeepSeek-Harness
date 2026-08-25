"""Generalized Retrieval candidate-access façade (#31 S1)."""

from __future__ import annotations

import json
import logging
from typing import Any

from .authored_knowledge import (
    AuthoredKnowledgeRecord,
    compile_authored_records_from_snapshot,
)
from .compiled_index_provider import CompiledIndexRetrievalProvider
from .knowledge_write_policy import filter_active_learned_world_records
from .character_epistemic import character_may_know_candidate
from .retrieval_contract import (
    BackendRetrievalRank,
    DegradationLevel,
    GenerationHints,
    HardAccessConstraints,
    ProviderStatus,
    RetrievalAccessDiagnostics,
    RetrievalAccessRequest,
    RetrievalAccessResponse,
    RetrievalCandidate,
    RetrievalCandidatePayload,
    validate_retrieval_access_request,
)
from .retrieval_selection import (
    RetrievalQueryContext,
    character_index_keys,
    merge_authored_record_sets,
)
from .scope_knowledge_repository import (
    DEFAULT_LEARNED_WORLD_LIMIT,
    DEFAULT_USER_PROFILE_LIMIT,
    LEARNED_WORLD_KNOWLEDGE,
    USER_PROFILE,
    ScopeKnowledgeRecord,
    ScopeKnowledgeRepository,
)
from .session_state import LiveSession

_logger = logging.getLogger(__name__)

CLASS_PRIORITY = {
    "authored_static": 0,
    "compiled_index": 1,
    "promoted_learned_world": 2,
    "user_profile": 3,
    "episodic_session": 4,
    "cross_scope_relationship": 5,
}

DEFAULT_CLASS_RECALL = {
    "authored_static": 128,
    "compiled_index": 128,
    "promoted_learned_world": DEFAULT_LEARNED_WORLD_LIMIT,
    "user_profile": DEFAULT_USER_PROFILE_LIMIT,
}


def _authority_ok(authority_class: str, hard: HardAccessConstraints) -> bool:
    if hard.exclude_authoritative_live and authority_class == "authoritative":
        return False
    return True


def _provenance_complete(provenance: dict[str, Any]) -> bool:
    if not provenance:
        return False
    return bool(
        str(provenance.get("knowledge_lane", "") or "").strip()
        or str(provenance.get("source_kind", "") or "").strip()
        or str(provenance.get("retrieval_provider_id", "") or "").strip()
    )


def _authored_to_candidate(
    record: AuthoredKnowledgeRecord,
    information_class: str,
    *,
    provider_id: str,
    source_index: int | None = None,
) -> RetrievalCandidate:
    rank = None
    if source_index is not None:
        rank = BackendRetrievalRank(
            retrieval_provider_id=provider_id,
            rank_metric="source_index",
            rank_value=source_index,
        )
    provenance = dict(record.provenance)
    provenance.setdefault("source_kind", record.source_kind)
    provenance.setdefault("source_asset_id", record.source_asset_id)
    return RetrievalCandidate(
        candidate_id=record.knowledge_id,
        information_class=information_class,
        payload=RetrievalCandidatePayload(content=record.content),
        authority_class=record.authority_class,
        visibility=record.visibility,
        subject_character_file_id=record.subject_character_file_id,
        provenance=provenance,
        backend_retrieval_rank=rank,
        host_internal_metadata={"legacy_authored_record": record.to_dict()},
    )


def _scope_to_candidate(record: ScopeKnowledgeRecord, information_class: str) -> RetrievalCandidate:
    provenance = dict(record.provenance)
    provenance.setdefault("source_kind", record.source_kind)
    provenance.setdefault("knowledge_lane", record.knowledge_kind)
    provenance.setdefault("scope_id", record.scope_id)
    temporal: dict[str, Any] = {}
    if record.created_at:
        temporal["created_at"] = record.created_at
    return RetrievalCandidate(
        candidate_id=record.knowledge_id,
        information_class=information_class,
        payload=RetrievalCandidatePayload(content=record.content),
        authority_class=record.authority_class,
        visibility=record.visibility,
        subject_character_file_id=record.subject_character_file_id,
        temporal_metadata=temporal,
        provenance=provenance,
        host_internal_metadata={"legacy_scope_record": record.to_dict()},
    )


def _hard_access_allows(
    candidate: RetrievalCandidate,
    hard: HardAccessConstraints,
    *,
    character_file_ids: dict[str, str],
    diagnostics: RetrievalAccessDiagnostics,
) -> bool:
    if candidate.information_class not in hard.allowed_information_classes:
        diagnostics.hard_access_rejected += 1
        return False
    if candidate.information_class in hard.prohibited_information_classes:
        diagnostics.hard_access_rejected += 1
        return False
    if not _authority_ok(candidate.authority_class, hard):
        diagnostics.hard_access_rejected += 1
        return False
    source_kind = str(candidate.provenance.get("source_kind", "") or "")
    if hard.allowed_source_kinds is not None and source_kind not in hard.allowed_source_kinds:
        diagnostics.hard_access_rejected += 1
        return False
    if hard.prohibited_source_kinds and source_kind in hard.prohibited_source_kinds:
        diagnostics.hard_access_rejected += 1
        return False
    if hard.subject_character_file_id:
        subj = candidate.subject_character_file_id
        if subj and subj != hard.subject_character_file_id:
            diagnostics.hard_access_rejected += 1
            return False
    if hard.require_provenance_complete and not _provenance_complete(candidate.provenance):
        diagnostics.incomplete_provenance_count += 1
        diagnostics.hard_access_rejected += 1
        return False
    visibility = str(candidate.visibility or "")
    viewer_file_id = None
    if hard.viewer_character_id and hard.viewer_character_id in character_file_ids:
        viewer_file_id = character_file_ids.get(hard.viewer_character_id)
    elif hard.subject_character_file_id:
        viewer_file_id = hard.subject_character_file_id
    if visibility == "character_scoped":
        if not viewer_file_id or candidate.subject_character_file_id != viewer_file_id:
            diagnostics.hard_access_rejected += 1
            return False
    if visibility == "template_participants":
        template_id = hard.session_template_id
        asset_id = str(candidate.provenance.get("source_asset_id", "") or "")
        if not template_id or asset_id != template_id:
            diagnostics.hard_access_rejected += 1
            return False
    if hard.entity_eligibility_refs:
        stable_refs = {
            ref.stable_ref
            for ref in hard.entity_eligibility_refs
            if str(ref.stable_ref or "").strip()
        }
        candidate_refs = {ref.stable_ref for ref in candidate.subject_entity_refs}
        if candidate.subject_character_file_id:
            candidate_refs.add(candidate.subject_character_file_id)
        if stable_refs and not stable_refs.intersection(candidate_refs):
            diagnostics.hard_access_rejected += 1
            return False
    if hard.known_by_character_name and not character_may_know_candidate(
        character_id=hard.known_by_character_name,
        provenance=candidate.provenance,
        host_internal_metadata=candidate.host_internal_metadata,
    ):
        diagnostics.hard_access_rejected += 1
        return False
    return True


def _candidate_sort_key(candidate: RetrievalCandidate) -> tuple[Any, ...]:
    class_rank = CLASS_PRIORITY.get(candidate.information_class, 99)
    backend_rank = 0.0
    if candidate.backend_retrieval_rank and candidate.backend_retrieval_rank.rank_value is not None:
        try:
            backend_rank = float(candidate.backend_retrieval_rank.rank_value)
        except (TypeError, ValueError):
            backend_rank = 0.0
    return (class_rank, backend_rank, candidate.candidate_id)


def _hint_boost(candidate: RetrievalCandidate, hints: GenerationHints) -> float:
    """Weak ordering boost from hints — not eligibility."""
    boost = 0.0
    content_lower = candidate.payload.content.lower()
    for term in hints.query_terms:
        token = str(term or "").strip().lower()
        if token and token in content_lower:
            boost -= 0.01
    for anchor in hints.entity_anchors:
        token = str(anchor or "").strip()
        if token and token in (
            candidate.subject_character_file_id or "",
            str(candidate.provenance.get("source_asset_id", "") or ""),
        ):
            boost -= 0.02
    for pref in hints.source_preferences:
        token = str(pref or "").strip()
        if token and token == str(candidate.provenance.get("source_kind", "") or ""):
            boost -= 0.005
    return boost


def _apply_class_recall(
    candidates: list[RetrievalCandidate],
    hints: GenerationHints,
) -> list[RetrievalCandidate]:
    budgets = dict(DEFAULT_CLASS_RECALL)
    budgets.update(hints.class_recall_budgets)
    if hints.recall_mode == "focused":
        for key in budgets:
            budgets[key] = max(1, budgets[key] // 2)
    kept: list[RetrievalCandidate] = []
    per_class: dict[str, int] = {}
    for candidate in candidates:
        limit = budgets.get(candidate.information_class, 64)
        count = per_class.get(candidate.information_class, 0)
        if count >= limit:
            continue
        per_class[candidate.information_class] = count + 1
        kept.append(candidate)
    return kept


def _apply_response_budget(
    candidates: list[RetrievalCandidate],
    request: RetrievalAccessRequest,
    diagnostics: RetrievalAccessDiagnostics,
) -> list[RetrievalCandidate]:
    budget = request.response_budget
    per_class_caps = dict(budget.per_class_max_candidates)
    selected: list[RetrievalCandidate] = []
    total_chars = 0
    per_class: dict[str, int] = {}
    for candidate in candidates:
        if len(selected) >= budget.max_candidates:
            diagnostics.budget_exhausted += 1
            continue
        class_cap = per_class_caps.get(candidate.information_class)
        if class_cap is not None:
            count = per_class.get(candidate.information_class, 0)
            if count >= class_cap:
                diagnostics.budget_exhausted += 1
                continue
        content_len = len(candidate.payload.content)
        if total_chars + content_len > budget.max_total_chars:
            diagnostics.budget_exhausted += 1
            continue
        selected.append(candidate)
        total_chars += content_len
        per_class[candidate.information_class] = per_class.get(candidate.information_class, 0) + 1
    return selected


class RetrievalService:
    """Role-agnostic retrieval candidate-access boundary."""

    def __init__(
        self,
        scope_repo: ScopeKnowledgeRepository | None = None,
        *,
        retrieval_provider: CompiledIndexRetrievalProvider | None = None,
    ) -> None:
        self._scope_repo = scope_repo
        self._retrieval_provider = retrieval_provider or CompiledIndexRetrievalProvider()

    def retrieve(
        self,
        request: RetrievalAccessRequest,
        fixture: LiveSession,
    ) -> RetrievalAccessResponse:
        validate_retrieval_access_request(request)
        diagnostics = RetrievalAccessDiagnostics()
        provider_status: list[ProviderStatus] = []
        raw_candidates: list[RetrievalCandidate] = []
        hard = request.hard_access
        hints = request.generation_hints
        allowed = set(hard.allowed_information_classes) - set(hard.prohibited_information_classes)
        character_file_ids = dict(fixture.character_file_ids or {})

        snapshot_records: list[AuthoredKnowledgeRecord] = []
        index_records: list[AuthoredKnowledgeRecord] = []

        if "authored_static" in allowed:
            diagnostics.consulted_sources.append("authored_snapshot")
            snapshot_records = compile_authored_records_from_snapshot(fixture.setup_snapshot or {})
            for record in snapshot_records:
                raw_candidates.append(
                    _authored_to_candidate(record, "authored_static", provider_id="authored_snapshot")
                )

        if "compiled_index" in allowed and self._retrieval_provider.is_configured():
            diagnostics.consulted_sources.append("compiled_index")
            query_ctx = RetrievalQueryContext(
                character_file_id=hard.subject_character_file_id,
                character_display_name=hard.viewer_character_id or "",
                session_template_id=hard.session_template_id,
                character_index_keys=tuple(hints.entity_anchors) or character_index_keys(
                    character_file_id=hard.subject_character_file_id,
                    character_display_name=hard.viewer_character_id or "",
                ),
            )
            try:
                index_records = self._retrieval_provider.query(query_ctx)
                provider_status.append(
                    ProviderStatus(provider_id=self._retrieval_provider.provider_id, status="ok")
                )
                for idx, record in enumerate(index_records):
                    raw_candidates.append(
                        _authored_to_candidate(
                            record,
                            "compiled_index",
                            provider_id=self._retrieval_provider.provider_id,
                            source_index=idx,
                        )
                    )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                _logger.warning("compiled index retrieval degraded: %s", exc)
                provider_status.append(
                    ProviderStatus(
                        provider_id=self._retrieval_provider.provider_id,
                        status="degraded",
                        detail=str(exc),
                    )
                )
        elif "compiled_index" in allowed:
            provider_status.append(
                ProviderStatus(
                    provider_id=self._retrieval_provider.provider_id,
                    status="unavailable",
                    detail="index not configured",
                )
            )

        merged_authored, merge_dedupe = merge_authored_record_sets(snapshot_records, index_records)
        diagnostics.dedupe_dropped += merge_dedupe
        merged_ids = {record.knowledge_id for record in merged_authored}
        authored_candidates = [
            candidate
            for candidate in raw_candidates
            if candidate.information_class not in {"authored_static", "compiled_index"}
            or candidate.candidate_id in merged_ids
        ]

        scope_id = request.memory_scope_id or fixture.memory_scope_id
        scope_candidates: list[RetrievalCandidate] = []
        if scope_id and self._scope_repo is not None:
            if "promoted_learned_world" in allowed:
                diagnostics.consulted_sources.append("scope_learned_world")
                limit = hints.class_recall_budgets.get(
                    "promoted_learned_world", DEFAULT_LEARNED_WORLD_LIMIT
                )
                world_records = self._scope_repo.list_records(
                    scope_id,
                    knowledge_kinds={LEARNED_WORLD_KNOWLEDGE},
                    limit=limit,
                )
                active = filter_active_learned_world_records(fixture, world_records)
                for record in active:
                    scope_candidates.append(_scope_to_candidate(record, "promoted_learned_world"))

            if "user_profile" in allowed:
                diagnostics.consulted_sources.append("scope_user_profile")
                limit = hints.class_recall_budgets.get("user_profile", DEFAULT_USER_PROFILE_LIMIT)
                profile_records = self._scope_repo.list_records(
                    scope_id,
                    knowledge_kinds={USER_PROFILE},
                    limit=limit,
                )
                for record in profile_records:
                    scope_candidates.append(_scope_to_candidate(record, "user_profile"))

        combined = authored_candidates + scope_candidates
        diagnostics.candidate_count_raw = len(combined)

        seen_ids: set[str] = set()
        deduped: list[RetrievalCandidate] = []
        for candidate in combined:
            if candidate.candidate_id in seen_ids:
                diagnostics.dedupe_dropped += 1
                continue
            seen_ids.add(candidate.candidate_id)
            deduped.append(candidate)

        filtered = [
            candidate
            for candidate in deduped
            if _hard_access_allows(
                candidate,
                hard,
                character_file_ids=character_file_ids,
                diagnostics=diagnostics,
            )
        ]

        filtered.sort(key=lambda item: (_hint_boost(item, hints), _candidate_sort_key(item)))
        recalled = _apply_class_recall(filtered, hints)
        bounded = _apply_response_budget(recalled, request, diagnostics)
        diagnostics.candidate_count_returned = len(bounded)
        diagnostics.provider_status = provider_status

        degradation: DegradationLevel = "none"
        if not bounded and combined:
            degradation = "empty"
        elif any(item.status != "ok" for item in provider_status):
            degradation = "partial" if bounded else "empty"

        return RetrievalAccessResponse(
            request_id=request.request_id,
            candidates=tuple(bounded),
            diagnostics=diagnostics,
            degradation_level=degradation,
        )

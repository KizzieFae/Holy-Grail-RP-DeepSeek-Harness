"""Story knowledge retrieval helpers — evidence budget and candidate building (#50)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .retrieval_contract import (
    BackendRetrievalRank,
    EntityRef,
    GenerationHints,
    HardAccessConstraints,
    RetrievalAccessDiagnostics,
    RetrievalCandidate,
    RetrievalCandidatePayload,
    RetrievalAccessRequest,
)
from .session_state import LiveSession
from .story_knowledge_contract import SelectionPath, StoryKnowledgeRecord
from .story_knowledge_epistemic import story_record_epistemically_eligible
from .story_semantic_index import SemanticIndexBackend


def _record_serialized_size(record: StoryKnowledgeRecord) -> int:
    return len(json.dumps(record.to_dict(), ensure_ascii=False))


def _referent_match(
    record: StoryKnowledgeRecord,
    entity_refs: tuple[EntityRef, ...],
) -> bool:
    if not entity_refs:
        return True
    record_refs = {ref.stable_ref for ref in record.stable_refs}
    required = {ref.stable_ref for ref in entity_refs if str(ref.stable_ref or "").strip()}
    if not required:
        return True
    return bool(record_refs.intersection(required))


def build_query_text(hints: GenerationHints, request: RetrievalAccessRequest) -> str:
    parts = list(hints.query_terms)
    parts.extend(hints.entity_anchors)
    parts.extend(hints.temporal_hints)
    parts.append(request.hg_scene_id)
    return "\n".join(part for part in parts if str(part).strip())


def record_to_candidate(record: StoryKnowledgeRecord) -> RetrievalCandidate:
    information_class = "story_occurrence" if record.record_kind == "occurrence" else "story_derived"
    candidate_id = record.record_id
    content_parts = [
        record.evidence.summary or "",
        record.evidence.committed_text,
        record.evidence.context_before,
        record.evidence.context_after,
    ]
    content = "\n".join(part for part in content_parts if part.strip())
    entity_refs = tuple(
        EntityRef(ref_kind=ref.ref_kind, stable_ref=ref.stable_ref, display_hint=ref.display_hint)
        for ref in record.stable_refs
    )
    provenance = {
        "provenance_domain": "story",
        "knowledge_lane": information_class,
        "source_kind": "story_knowledge",
        "retrieval_provider_id": "story_knowledge_jsonl",
        "record_kind": record.record_kind,
        "memory_scope_id": record.memory_scope_id,
        "source_event_id": record.event_id,
        "story_record_id": record.story_record_id,
        "source_domain_commit_id": record.source_domain_commit_id,
        "turn_index": record.turn_index,
        "event_type": record.event_type,
    }
    return RetrievalCandidate(
        candidate_id=candidate_id,
        information_class=information_class,  # type: ignore[arg-type]
        payload=RetrievalCandidatePayload(
            content=content,
            structured_payload=record.to_dict(),
        ),
        authority_class="derived",
        visibility="story_scope",
        subject_entity_refs=entity_refs,
        temporal_metadata={"turn_index": record.turn_index},
        provenance=provenance,
        backend_retrieval_rank=BackendRetrievalRank(
            retrieval_provider_id="story_knowledge_jsonl",
            rank_metric="turn_index",
            rank_value=record.turn_index if record.turn_index is not None else 0,
        ),
    )


@dataclass
class StorySelectionResult:
    candidates: list[RetrievalCandidate]
    selection_path: SelectionPath
    eligible_count: int
    eligible_chars: int
    budget_chars: int
    semantic_index_failed: bool = False


def select_story_candidates(
    *,
    fixture: LiveSession,
    request: RetrievalAccessRequest,
    records: list[StoryKnowledgeRecord],
    semantic_index: SemanticIndexBackend | None,
    diagnostics: RetrievalAccessDiagnostics,
) -> StorySelectionResult:
    hard = request.hard_access
    viewer = hard.known_by_character_name or hard.viewer_character_id
    viewer_role = hard.viewer_role

    eligible: list[StoryKnowledgeRecord] = []
    for record in records:
        if not _referent_match(record, hard.entity_eligibility_refs):
            diagnostics.hard_access_rejected += 1
            continue
        if not story_record_epistemically_eligible(
            fixture,
            record,
            viewer_character_id=viewer,
            viewer_role=viewer_role,
        ):
            diagnostics.hard_access_rejected += 1
            continue
        eligible.append(record)

    eligible_chars = sum(_record_serialized_size(record) for record in eligible)
    budget_chars = request.response_budget.max_total_chars

    if not eligible:
        return StorySelectionResult([], "none", 0, 0, budget_chars)

    if eligible_chars <= budget_chars:
        ordered = sorted(
            eligible,
            key=lambda item: (
                -(item.turn_index if item.turn_index is not None else -1),
                item.record_id,
            ),
        )
        candidates = [record_to_candidate(record) for record in ordered]
        candidates = _apply_candidate_budget(candidates, request, diagnostics)
        return StorySelectionResult(
            candidates,
            "full_eligible",
            len(eligible),
            eligible_chars,
            budget_chars,
        )

    if semantic_index is None or not semantic_index.available:
        return StorySelectionResult([], "none", len(eligible), eligible_chars, budget_chars, True)

    query_text = build_query_text(request.generation_hints, request)
    ranked_ids = semantic_index.rank(
        query_text,
        [record.record_id for record in eligible],
        limit=request.response_budget.max_candidates,
    )
    if not ranked_ids:
        return StorySelectionResult([], "none", len(eligible), eligible_chars, budget_chars, True)

    by_id = {record.record_id: record for record in eligible}
    ranked_records = [by_id[record_id] for record_id in ranked_ids if record_id in by_id]
    candidates = [record_to_candidate(record) for record in ranked_records]
    for index, candidate in enumerate(candidates):
        candidates[index] = RetrievalCandidate(
            candidate_id=candidate.candidate_id,
            information_class=candidate.information_class,
            payload=candidate.payload,
            authority_class=candidate.authority_class,
            visibility=candidate.visibility,
            subject_character_file_id=candidate.subject_character_file_id,
            subject_entity_refs=candidate.subject_entity_refs,
            temporal_metadata=candidate.temporal_metadata,
            provenance=candidate.provenance,
            backend_retrieval_rank=BackendRetrievalRank(
                retrieval_provider_id="story_semantic_index",
                rank_metric="cosine_similarity",
                rank_value=index,
            ),
            host_internal_metadata=candidate.host_internal_metadata,
        )
    candidates = _apply_candidate_budget(candidates, request, diagnostics)
    return StorySelectionResult(
        candidates,
        "semantic_ranked",
        len(eligible),
        eligible_chars,
        budget_chars,
    )


def _apply_candidate_budget(
    candidates: list[RetrievalCandidate],
    request: RetrievalAccessRequest,
    diagnostics: RetrievalAccessDiagnostics,
) -> list[RetrievalCandidate]:
    budget = request.response_budget
    selected: list[RetrievalCandidate] = []
    total_chars = 0
    for candidate in candidates:
        if len(selected) >= budget.max_candidates:
            diagnostics.budget_exhausted += 1
            break
        content_len = len(candidate.payload.content)
        if total_chars + content_len > budget.max_total_chars:
            diagnostics.budget_exhausted += 1
            break
        selected.append(candidate)
        total_chars += content_len
    return selected

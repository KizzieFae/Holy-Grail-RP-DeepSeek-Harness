"""Bounded semantic mediation for Librarian read path (#34 S2a.4).

Relevance is derived from consumer focus questions and structured hints — not from
#31 backend_retrieval_rank. This is intentionally deterministic structured mediation;
LLM-backed strategies can be injected via LibrarianMediationStrategy when Host/DSH
requires deeper contextual ranking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from .librarian_authoritative_input import AuthoritativeWorkingItem, authoritative_item_to_bundle_entry
from .librarian_contract import (
    InterpretiveStatus,
    KnowledgeAccessRequest,
    LibrarianAnnotation,
    LibrarianBundleEntry,
    LibrarianMediationResult,
    MediationCatalogItem,
    MediationMode,
    MediationSelectionItem,
    QuestionOutcome,
    QuestionOutcomeStatus,
    RelevanceBand,
    StableReference,
    SynthesisMeta,
    VisibilityScope,
    BundleConnection,
)
from .retrieval_contract import RetrievalCandidate


@dataclass(frozen=True)
class MediationCandidate:
    candidate: RetrievalCandidate | None
    authoritative_item: AuthoritativeWorkingItem | None
    source_kind: str


@dataclass(frozen=True)
class MediationScore:
    score: float
    matched_terms: tuple[str, ...]
    answers_focus_questions: tuple[str, ...]
    interpretive_status: InterpretiveStatus


_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _tokenize(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if len(token) > 2}


def _focus_tokens(request: KnowledgeAccessRequest) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for question in request.information_need.focus_questions:
        key = str(question or "").strip()
        if not key:
            continue
        mapping[key] = _tokenize(key)
    return mapping


def _content_for_item(item: MediationCandidate) -> str:
    if item.authoritative_item is not None:
        return item.authoritative_item.contribution.content
    if item.candidate is not None:
        return item.candidate.payload.content
    return ""


def _entity_tokens(request: KnowledgeAccessRequest) -> set[str]:
    tokens: set[str] = set()
    envelope = request.visibility_envelope
    for value in (
        envelope.viewer_character_id,
        envelope.subject_character_id,
    ):
        if value:
            tokens.add(str(value).lower())
    for ref in request.information_need.entity_refs:
        if ref.stable_ref:
            tokens.add(str(ref.stable_ref).lower())
        if ref.display_hint:
            tokens.add(str(ref.display_hint).lower())
    return tokens


def score_mediation_item(
    request: KnowledgeAccessRequest,
    item: MediationCandidate,
) -> MediationScore:
    content = _content_for_item(item)
    content_tokens = _tokenize(content)
    focus_map = _focus_tokens(request)
    entity_tokens = _entity_tokens(request)

    matched_terms: set[str] = set()
    answered_questions: list[str] = []
    overlap_score = 0.0
    for question, question_tokens in focus_map.items():
        if not question_tokens:
            continue
        overlap = question_tokens & content_tokens
        if overlap:
            overlap_score += len(overlap) / max(1, len(question_tokens))
            matched_terms.update(overlap)
            answered_questions.append(question)

    entity_hits = sum(1 for token in entity_tokens if token in content.lower())
    relationship_bonus = 0.0
    for focus in request.information_need.relationship_focus:
        subject = str(focus.subject_ref or "").lower()
        obj = str(focus.object_ref or "").lower()
        if subject and subject in content.lower():
            relationship_bonus += 0.15
        if obj and obj in content.lower():
            relationship_bonus += 0.1

    authoritative_bonus = 0.0
    interpretive_status: InterpretiveStatus = "likely"
    if item.authoritative_item is not None:
        authoritative_bonus = 0.35
        interpretive_status = "confirmed"
    elif item.candidate is not None:
        interpretive_status = "likely" if overlap_score >= 0.35 else "speculative"

    # Deliberately ignore backend_retrieval_rank — semantic mediation is separate.
    score = overlap_score + (entity_hits * 0.08) + relationship_bonus + authoritative_bonus
    if item.authoritative_item is not None and not overlap_score:
        score += 0.2  # stage-required authoritative context remains visible

    return MediationScore(
        score=score,
        matched_terms=tuple(sorted(matched_terms)),
        answers_focus_questions=tuple(answered_questions),
        interpretive_status=interpretive_status,
    )


def _relevance_band(rank: int, score: float) -> RelevanceBand:
    if rank <= 3 or score >= 0.6:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def retrieval_candidate_to_bundle_entry(
    candidate: RetrievalCandidate,
    *,
    entry_id: str,
    relevance_rank: int,
    mediation: MediationScore,
) -> LibrarianBundleEntry:
    visibility: VisibilityScope | str = candidate.visibility or "public"
    provenance = dict(candidate.provenance)
    provenance.setdefault("candidate_id", candidate.candidate_id)
    provenance["mediation_basis"] = "deterministic_fallback_lexical"
    if candidate.backend_retrieval_rank is not None:
        provenance["backend_retrieval_rank_preserved_in_audit_only"] = True

    return LibrarianBundleEntry(
        entry_id=entry_id,
        ref=StableReference(
            ref_kind="retrieval_candidate",
            stable_ref=candidate.candidate_id,
            display_hint=str(candidate.information_class),
        ),
        content=candidate.payload.content,
        information_class=candidate.information_class,
        source_tier="retrieval_candidate",
        authority_class=candidate.authority_class,
        visibility_scope=visibility,
        provenance=provenance,
        temporal_relationship="timeless_authored"
        if candidate.information_class in {"authored_static", "compiled_index"}
        else "recent",
        structured_payload=dict(candidate.payload.structured_payload or {}),
        librarian_annotation=LibrarianAnnotation(
            relevance_rank=relevance_rank,
            relevance_band=_relevance_band(relevance_rank, mediation.score),
            salience_note=(
                f"focus overlap score={mediation.score:.3f}; "
                f"matched_terms={','.join(mediation.matched_terms) or 'none'}"
            ),
            interpretive_status=mediation.interpretive_status,
            answers_focus_questions=mediation.answers_focus_questions,
        ),
    )


class LibrarianMediationStrategy(Protocol):
    def mediate(
        self,
        request: KnowledgeAccessRequest,
        items: list[MediationCandidate],
    ) -> list[tuple[MediationCandidate, MediationScore]]:
        ...


class StructuredFocusQuestionMediation:
    """Deterministic fallback only — retrieval-style lexical ranking, not contextual mediation."""

    def mediate(
        self,
        request: KnowledgeAccessRequest,
        items: list[MediationCandidate],
    ) -> list[tuple[MediationCandidate, MediationScore]]:
        scored = [(item, score_mediation_item(request, item)) for item in items]
        scored.sort(
            key=lambda pair: (
                -pair[1].score,
                pair[0].authoritative_item is None,
                pair[0].candidate.candidate_id if pair[0].candidate else "",
            )
        )
        return scored


def build_fallback_bundle_entries(
    request: KnowledgeAccessRequest,
    items: list[MediationCandidate],
) -> list[LibrarianBundleEntry]:
    return build_bundle_entries(
        request,
        items,
        strategy=StructuredFocusQuestionMediation(),
    )


def _catalog_item_to_bundle_entry(
    catalog_item: MediationCatalogItem,
    *,
    entry_id: str,
    selection: MediationSelectionItem | None = None,
    default_rank: int,
) -> LibrarianBundleEntry:
    rank = selection.relevance_rank if selection else default_rank
    annotation = LibrarianAnnotation(
        relevance_rank=rank,
        relevance_band=selection.relevance_band if selection else None,
        salience_note=selection.salience_note if selection else "contextual_semantic_mediation",
        interpretive_status=(
            selection.interpretive_status
            if selection and selection.interpretive_status
            else ("confirmed" if catalog_item.authority_class == "authoritative" else "likely")
        ),
        answers_focus_questions=selection.answers_focus_questions if selection else (),
    )
    provenance = dict(catalog_item.provenance)
    provenance["mediation_basis"] = "contextual_semantic"
    provenance["catalog_source_id"] = catalog_item.source_id
    return LibrarianBundleEntry(
        entry_id=entry_id,
        ref=StableReference(
            ref_kind=catalog_item.source_kind,
            stable_ref=catalog_item.stable_ref,
            display_hint=catalog_item.source_id,
        ),
        content=catalog_item.content,
        information_class=catalog_item.information_class,
        source_tier=catalog_item.source_tier,
        authority_class=catalog_item.authority_class,
        visibility_scope=catalog_item.visibility_scope,
        provenance=provenance,
        temporal_relationship=catalog_item.temporal_relationship,
        librarian_annotation=annotation,
    )


def build_bundle_entries_from_contextual_result(
    request: KnowledgeAccessRequest,
    catalog: dict[str, MediationCatalogItem],
    result: LibrarianMediationResult,
) -> tuple[list[LibrarianBundleEntry], tuple[BundleConnection, ...]]:
    entries: list[LibrarianBundleEntry] = []
    source_to_entry: dict[str, str] = {}
    for index, selection in enumerate(
        sorted(result.selected_items, key=lambda item: item.relevance_rank),
        start=1,
    ):
        catalog_item = catalog.get(selection.source_id)
        if catalog_item is None:
            continue
        entry_id = f"entry-{index}"
        entries.append(
            _catalog_item_to_bundle_entry(
                catalog_item,
                entry_id=entry_id,
                selection=selection,
                default_rank=index,
            )
        )
        source_to_entry[selection.source_id] = entry_id

    synth_start = len(entries)
    for offset, synth in enumerate(result.synthesis_entries, start=1):
        entry_id = f"synth-{offset}"
        refs = tuple(
            StableReference(ref_kind="catalog", stable_ref=source_id, display_hint=source_id)
            for source_id in synth.source_ids
            if source_id in catalog
        )
        entries.append(
            LibrarianBundleEntry(
                entry_id=entry_id,
                ref=StableReference(
                    ref_kind="semantic_inference",
                    stable_ref=synth.synthesis_id,
                    display_hint=synth.synthesis_kind,
                ),
                content=synth.content,
                information_class="semantic_inference",
                source_tier="retrieval_candidate",
                authority_class="suggestive",
                visibility_scope="scene_orchestration",
                provenance={
                    "mediation_basis": "contextual_semantic",
                    "synthesis_id": synth.synthesis_id,
                    "source_ids": list(synth.source_ids),
                },
                temporal_relationship="recent",
                librarian_annotation=LibrarianAnnotation(
                    relevance_rank=synth_start + offset,
                    relevance_band="medium",
                    salience_note="contextual synthesis",
                    interpretive_status=synth.interpretive_status,
                ),
                synthesis_meta=SynthesisMeta(
                    synthesis_kind=synth.synthesis_kind,
                    source_entry_refs=refs,
                    interpretive_status=synth.interpretive_status,
                ),
            )
        )

    connections: list[BundleConnection] = []
    for conn in result.connections:
        from_entry = source_to_entry.get(conn.from_source_id)
        to_entry = source_to_entry.get(conn.to_source_id)
        if not from_entry or not to_entry:
            continue
        connections.append(
            BundleConnection(
                connection_id=conn.connection_id,
                edge_kind=conn.edge_kind,
                from_entry_id=from_entry,
                to_entry_id=to_entry,
                note=conn.note,
            )
        )
    return entries, tuple(connections)


def build_bundle_entries(
    request: KnowledgeAccessRequest,
    items: list[MediationCandidate],
    *,
    strategy: LibrarianMediationStrategy | None = None,
) -> list[LibrarianBundleEntry]:
    mediator = strategy or StructuredFocusQuestionMediation()
    scored = mediator.mediate(request, items)
    entries: list[LibrarianBundleEntry] = []
    for rank, (item, mediation) in enumerate(scored, start=1):
        entry_id = f"entry-{rank}"
        if item.authoritative_item is not None:
            entries.append(
                authoritative_item_to_bundle_entry(
                    item.authoritative_item,
                    entry_id=entry_id,
                    relevance_rank=rank,
                    answers_focus_questions=mediation.answers_focus_questions,
                )
            )
        elif item.candidate is not None:
            entries.append(
                retrieval_candidate_to_bundle_entry(
                    item.candidate,
                    entry_id=entry_id,
                    relevance_rank=rank,
                    mediation=mediation,
                )
            )
    return entries


def assess_focus_question_satisfaction(
    request: KnowledgeAccessRequest,
    entries: list[LibrarianBundleEntry],
    *,
    mediation_mode: MediationMode = "contextual_semantic",
) -> tuple[QuestionOutcome, ...]:
    outcomes: list[QuestionOutcome] = []
    for question in request.information_need.focus_questions:
        key = str(question or "").strip()
        if not key:
            continue
        supporting = [
            entry.entry_id
            for entry in entries
            if key in entry.librarian_annotation.answers_focus_questions
        ]
        if supporting and mediation_mode == "contextual_semantic":
            status: QuestionOutcomeStatus = "answered"
        elif supporting and mediation_mode == "deterministic_fallback":
            status = "partial"
        elif mediation_mode == "deterministic_fallback":
            partial = [
                entry.entry_id
                for entry in entries
                if _tokenize(key) & _tokenize(entry.content)
            ]
            status = "partial" if partial else "unanswered"
            supporting = partial
        elif supporting:
            status = "answered"
        else:
            partial = [
                entry.entry_id
                for entry in entries
                if _tokenize(key) & _tokenize(entry.content)
            ]
            if partial:
                status = "partial"
                supporting = partial
            else:
                status = "unanswered"
        outcomes.append(
            QuestionOutcome(
                question=key,
                status=status,
                supporting_entry_ids=tuple(supporting),
                note=(
                    "deterministic_fallback — lexical overlap is not full semantic satisfaction"
                    if mediation_mode == "deterministic_fallback" and status != "unanswered"
                    else None
                ),
            )
        )
    return tuple(outcomes)

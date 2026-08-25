"""Map KnowledgeAccessRequest to #31 RetrievalAccessRequest(s) (#34 S2a.2)."""

from __future__ import annotations

import uuid
from typing import Iterable

from .librarian_contract import KnowledgeAccessRequest, RecallBreadthPreference
from .retrieval_contract import (
    ALL_INFORMATION_CLASSES,
    DEFAULT_LIBRARIAN_MAX_CANDIDATES,
    DEFAULT_LIBRARIAN_MAX_CHARS,
    GenerationHints,
    HardAccessConstraints,
    ResponseBudget,
    RetrievalAccessRequest,
)

_RETRIEVAL_CLASSES = frozenset(ALL_INFORMATION_CLASSES)

_DEFAULT_CLASS_BUDGETS = {
    "authored_static": 128,
    "compiled_index": 128,
    "promoted_learned_world": 32,
    "user_profile": 24,
    "episodic_session": 16,
    "cross_scope_relationship": 16,
}

_FOCUSED_CLASS_BUDGETS = {
    key: max(1, value // 2) for key, value in _DEFAULT_CLASS_BUDGETS.items()
}


def effective_information_classes(request: KnowledgeAccessRequest) -> frozenset[str]:
    allowed = set(request.host_allowed_information_classes)
    if request.requested_information_classes is not None:
        allowed &= set(request.requested_information_classes)
    return frozenset(allowed & _RETRIEVAL_CLASSES)


def _recall_mode(preference: RecallBreadthPreference, information_class: str) -> str:
    if preference == "focused":
        return "focused"
    if information_class in {"episodic_session", "cross_scope_relationship"}:
        return "focused"
    return "broad"


def _class_budgets(
    preference: RecallBreadthPreference,
    request: KnowledgeAccessRequest,
) -> dict[str, int]:
    base = dict(_FOCUSED_CLASS_BUDGETS if preference == "focused" else _DEFAULT_CLASS_BUDGETS)
    per_request = max(1, request.budget_expectations.max_bundle_entries // max(1, len(base)))
    for key in list(base.keys()):
        base[key] = min(base[key], per_request)
    return base


def _query_terms(request: KnowledgeAccessRequest) -> tuple[str, ...]:
    need = request.information_need
    terms: list[str] = []
    for question in need.focus_questions:
        token = str(question or "").strip()
        if token:
            terms.append(token)
    for topic in need.topics:
        token = str(topic or "").strip()
        if token:
            terms.append(token)
    return tuple(terms)


def _entity_anchors(request: KnowledgeAccessRequest) -> tuple[str, ...]:
    anchors: list[str] = []
    envelope = request.visibility_envelope
    if envelope.subject_character_id:
        anchors.append(envelope.subject_character_id)
    for ref in request.information_need.entity_refs:
        if str(ref.stable_ref or "").strip():
            anchors.append(str(ref.stable_ref))
    return tuple(dict.fromkeys(anchors))


def _relationship_focus(request: KnowledgeAccessRequest) -> tuple[str, ...]:
    return tuple(
        f"{item.subject_ref}:{item.object_ref or ''}:{item.relationship_kind or ''}".strip(":")
        for item in request.information_need.relationship_focus
        if str(item.subject_ref or "").strip()
    )


def _temporal_hints(request: KnowledgeAccessRequest) -> tuple[str, ...]:
    orientation = request.information_need.temporal_orientation
    if orientation is None:
        return ()
    return (orientation,)


def build_retrieval_access_requests(
    request: KnowledgeAccessRequest,
    *,
    memory_scope_id: str | None,
    character_file_ids: dict[str, str] | None = None,
) -> list[RetrievalAccessRequest]:
    """One RetrievalAccessRequest per eligible information class (Layer A/B mapping)."""
    classes = effective_information_classes(request)
    if not classes:
        return []

    envelope = request.visibility_envelope
    need = request.information_need
    preference = need.recall_breadth_preference
    file_ids = character_file_ids or {}
    subject_file_id = None
    if envelope.subject_character_id:
        subject_file_id = file_ids.get(envelope.subject_character_id, envelope.subject_character_id)

    hard_template = HardAccessConstraints(
        viewer_character_id=envelope.viewer_character_id,
        subject_character_file_id=subject_file_id,
        session_template_id=envelope.session_template_id,
        exclude_authoritative_live=True,
        require_provenance_complete=request.degradation_preferences.require_provenance_complete,
    )

    query_terms = _query_terms(request)
    entity_anchors = _entity_anchors(request)
    relationship_focus = _relationship_focus(request)
    temporal_hints = _temporal_hints(request)
    class_budgets = _class_budgets(preference, request)

    per_class_candidates = max(
        4,
        min(
            DEFAULT_LIBRARIAN_MAX_CANDIDATES,
            request.budget_expectations.max_bundle_entries,
        ),
    )
    per_class_chars = max(
        512,
        min(
            DEFAULT_LIBRARIAN_MAX_CHARS,
            request.budget_expectations.max_bundle_chars // max(1, len(classes)),
        ),
    )

    retrieval_requests: list[RetrievalAccessRequest] = []
    for information_class in sorted(classes):
        allowed = frozenset({information_class})
        hard = HardAccessConstraints(
            viewer_character_id=hard_template.viewer_character_id,
            subject_character_file_id=hard_template.subject_character_file_id,
            session_template_id=hard_template.session_template_id,
            allowed_information_classes=allowed,
            prohibited_information_classes=frozenset(
                _RETRIEVAL_CLASSES - allowed,
            ),
            exclude_authoritative_live=True,
            require_provenance_complete=hard_template.require_provenance_complete,
        )
        hints = GenerationHints(
            query_terms=query_terms,
            entity_anchors=entity_anchors,
            relationship_focus=relationship_focus,
            temporal_hints=temporal_hints,
            recall_mode=_recall_mode(preference, information_class),
            class_recall_budgets={information_class: class_budgets.get(information_class, 32)},
        )
        retrieval_requests.append(
            RetrievalAccessRequest(
                request_id=f"hg-retrieval-{uuid.uuid4()}",
                consumer_role="librarian",
                hg_scene_id=request.hg_scene_id,
                hg_round_id=request.hg_round_id,
                turn_index=request.turn_index,
                memory_scope_id=memory_scope_id,
                hard_access=hard,
                generation_hints=hints,
                response_budget=ResponseBudget(
                    max_candidates=per_class_candidates,
                    max_total_chars=per_class_chars,
                    per_class_max_candidates={information_class: class_budgets.get(information_class, 32)},
                ),
                audit_reason=f"librarian_s2a:{request.request_id}:{information_class}",
            )
        )
    return retrieval_requests


def merge_retrieval_candidate_ids(
    responses: Iterable[object],
) -> tuple[str, ...]:
    seen: list[str] = []
    observed: set[str] = set()
    for response in responses:
        for candidate in getattr(response, "candidates", ()) or ():
            candidate_id = str(getattr(candidate, "candidate_id", "") or "")
            if not candidate_id or candidate_id in observed:
                continue
            observed.add(candidate_id)
            seen.append(candidate_id)
    return tuple(seen)

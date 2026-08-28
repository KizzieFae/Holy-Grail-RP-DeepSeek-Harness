"""Retrieval candidate-access contracts (#31 S0).

Layer A (hard access), Layer B (generation hints), and response types for the
generalized Retrieval façade. Semantic relevance and Librarian mediation are
explicitly out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .contract import AuthorityClass

InformationClass = Literal[
    "authored_static",
    "compiled_index",
    "promoted_learned_world",
    "user_profile",
    "episodic_session",
    "cross_scope_relationship",
    "story_occurrence",
    "story_derived",
]

RecallMode = Literal["broad", "focused"]
RetrievalConsumerRole = Literal[
    "librarian",
    "host_packaging_legacy",
    "host_internal",
    "storyteller",
]
DegradationLevel = Literal["none", "partial", "empty"]

ALL_INFORMATION_CLASSES: frozenset[str] = frozenset(
    {
        "authored_static",
        "compiled_index",
        "promoted_learned_world",
        "user_profile",
        "episodic_session",
        "cross_scope_relationship",
        "story_occurrence",
        "story_derived",
    }
)

DEFAULT_LIBRARIAN_MAX_CANDIDATES = 64
DEFAULT_LIBRARIAN_MAX_CHARS = 32000


@dataclass(frozen=True)
class EntityRef:
    ref_kind: str
    stable_ref: str
    display_hint: str | None = None


@dataclass(frozen=True)
class HardAccessConstraints:
    """Layer A — eligibility gates (must not be overridden by hints)."""

    viewer_character_id: str | None = None
    viewer_role: str | None = None
    subject_character_file_id: str | None = None
    subject_character_display_name: str | None = None
    session_template_id: str | None = None
    allowed_information_classes: frozenset[str] = ALL_INFORMATION_CLASSES
    prohibited_information_classes: frozenset[str] = frozenset()
    allowed_source_kinds: frozenset[str] | None = None
    prohibited_source_kinds: frozenset[str] | None = None
    entity_eligibility_refs: tuple[EntityRef, ...] = ()
    exclude_authoritative_live: bool = True
    require_provenance_complete: bool = False
    known_by_character_name: str | None = None


@dataclass(frozen=True)
class GenerationHints:
    """Layer B — bounded recall guidance (not semantic relevance)."""

    query_terms: tuple[str, ...] = ()
    entity_anchors: tuple[str, ...] = ()
    relationship_focus: tuple[str, ...] = ()
    temporal_hints: tuple[str, ...] = ()
    source_preferences: tuple[str, ...] = ()
    recall_mode: RecallMode = "broad"
    class_recall_budgets: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ResponseBudget:
    max_candidates: int = DEFAULT_LIBRARIAN_MAX_CANDIDATES
    max_total_chars: int = DEFAULT_LIBRARIAN_MAX_CHARS
    per_class_max_candidates: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalAccessRequest:
    request_id: str
    consumer_role: RetrievalConsumerRole
    hg_scene_id: str
    hg_round_id: str
    turn_index: int
    memory_scope_id: str | None = None
    hard_access: HardAccessConstraints = HardAccessConstraints()
    generation_hints: GenerationHints = GenerationHints()
    response_budget: ResponseBudget = ResponseBudget()
    audit_reason: str = ""


@dataclass(frozen=True)
class BackendRetrievalRank:
    """Weak within-backend ordering prior — not semantic relevance."""

    retrieval_provider_id: str
    rank_metric: str
    rank_value: float | int | None = None


@dataclass(frozen=True)
class RetrievalCandidatePayload:
    content: str
    structured_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class RetrievalCandidate:
    candidate_id: str
    information_class: InformationClass
    payload: RetrievalCandidatePayload
    authority_class: AuthorityClass
    visibility: str
    subject_character_file_id: str | None = None
    subject_entity_refs: tuple[EntityRef, ...] = ()
    temporal_metadata: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    backend_retrieval_rank: BackendRetrievalRank | None = None
    host_internal_metadata: dict[str, Any] = field(default_factory=dict)

    def consumer_dict(self) -> dict[str, Any]:
        """Export for external consumers — strips host-internal metadata."""
        return {
            "candidate_id": self.candidate_id,
            "information_class": self.information_class,
            "payload": {
                "content": self.payload.content,
                "structured_payload": dict(self.payload.structured_payload or {}),
            },
            "authority_class": self.authority_class,
            "visibility": self.visibility,
            "subject_character_file_id": self.subject_character_file_id,
            "subject_entity_refs": [
                {
                    "ref_kind": ref.ref_kind,
                    "stable_ref": ref.stable_ref,
                    "display_hint": ref.display_hint,
                }
                for ref in self.subject_entity_refs
            ],
            "temporal_metadata": dict(self.temporal_metadata),
            "provenance": dict(self.provenance),
            "backend_retrieval_rank": (
                {
                    "retrieval_provider_id": self.backend_retrieval_rank.retrieval_provider_id,
                    "rank_metric": self.backend_retrieval_rank.rank_metric,
                    "rank_value": self.backend_retrieval_rank.rank_value,
                }
                if self.backend_retrieval_rank is not None
                else None
            ),
        }


@dataclass
class ProviderStatus:
    provider_id: str
    status: Literal["ok", "degraded", "unavailable"] = "ok"
    detail: str = ""


@dataclass
class RetrievalAccessDiagnostics:
    provider_status: list[ProviderStatus] = field(default_factory=list)
    candidate_count_raw: int = 0
    candidate_count_returned: int = 0
    hard_access_rejected: int = 0
    dedupe_dropped: int = 0
    budget_exhausted: int = 0
    incomplete_provenance_count: int = 0
    consulted_sources: list[str] = field(default_factory=list)
    story_selection_path: str | None = None
    story_eligible_count: int = 0
    story_eligible_chars: int = 0
    story_semantic_index_failed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider_status": [
                {
                    "provider_id": item.provider_id,
                    "status": item.status,
                    "detail": item.detail,
                }
                for item in self.provider_status
            ],
            "candidate_count_raw": self.candidate_count_raw,
            "candidate_count_returned": self.candidate_count_returned,
            "hard_access_rejected": self.hard_access_rejected,
            "dedupe_dropped": self.dedupe_dropped,
            "budget_exhausted": self.budget_exhausted,
            "incomplete_provenance_count": self.incomplete_provenance_count,
            "consulted_sources": list(self.consulted_sources),
        }
        if self.story_selection_path is not None:
            payload["story_selection_path"] = self.story_selection_path
        if self.story_eligible_count:
            payload["story_eligible_count"] = self.story_eligible_count
        if self.story_eligible_chars:
            payload["story_eligible_chars"] = self.story_eligible_chars
        if self.story_semantic_index_failed:
            payload["story_semantic_index_failed"] = True
        return payload


@dataclass(frozen=True)
class RetrievalAccessResponse:
    request_id: str
    candidates: tuple[RetrievalCandidate, ...]
    diagnostics: RetrievalAccessDiagnostics
    degradation_level: DegradationLevel = "none"


def validate_retrieval_access_request(request: RetrievalAccessRequest) -> None:
    if not str(request.request_id or "").strip():
        raise ValueError("request_id is required")
    if not str(request.hg_scene_id or "").strip():
        raise ValueError("hg_scene_id is required")
    if not str(request.hg_round_id or "").strip():
        raise ValueError("hg_round_id is required")
    if request.turn_index < 0:
        raise ValueError("turn_index must be non-negative")
    unknown = set(request.hard_access.allowed_information_classes) - ALL_INFORMATION_CLASSES
    if unknown:
        raise ValueError(f"unknown information_class in allowed set: {sorted(unknown)}")
    prohibited = set(request.hard_access.prohibited_information_classes) - ALL_INFORMATION_CLASSES
    if prohibited:
        raise ValueError(f"unknown information_class in prohibited set: {sorted(prohibited)}")
    if request.response_budget.max_candidates <= 0:
        raise ValueError("response_budget.max_candidates must be positive")
    if request.response_budget.max_total_chars <= 0:
        raise ValueError("response_budget.max_total_chars must be positive")

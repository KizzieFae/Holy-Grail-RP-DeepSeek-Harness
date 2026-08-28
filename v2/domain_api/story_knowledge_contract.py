"""Story-derived knowledge contracts (#50)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

STORY_KNOWLEDGE_SCHEMA_VERSION = 1

RecordKind = Literal["occurrence", "derived"]
ProvenanceDomain = Literal["story"]
EpistemicAuthorityRefKind = Literal[
    "inherit_source_events",
    "establishment_decision",
    "orchestration_visibility",
]

MediationOutcome = Literal[
    "match",
    "no_match",
    "ambiguous",
    "forbidden",
    "retrieval_failure",
    "mediation_failure",
]

SelectionPath = Literal["full_eligible", "semantic_ranked", "none"]


@dataclass(frozen=True)
class StableRef:
    ref_kind: str
    stable_ref: str
    display_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref_kind": self.ref_kind,
            "stable_ref": self.stable_ref,
            "display_hint": self.display_hint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StableRef:
        return cls(
            ref_kind=str(data.get("ref_kind", "")),
            stable_ref=str(data.get("stable_ref", "")),
            display_hint=data.get("display_hint"),
        )


@dataclass(frozen=True)
class StoryRelation:
    rel: str
    target_id: str

    def to_dict(self) -> dict[str, Any]:
        return {"rel": self.rel, "target_id": self.target_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryRelation:
        return cls(rel=str(data.get("rel", "")), target_id=str(data.get("target_id", "")))


@dataclass(frozen=True)
class StoryEvidence:
    summary: str | None
    committed_text: str
    context_before: str = ""
    context_after: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "committed_text": self.committed_text,
            "context_before": self.context_before,
            "context_after": self.context_after,
        }
        if self.summary:
            payload["summary"] = self.summary
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryEvidence:
        return cls(
            summary=data.get("summary"),
            committed_text=str(data.get("committed_text", "")),
            context_before=str(data.get("context_before", "")),
            context_after=str(data.get("context_after", "")),
        )

    def serialized_size(self) -> int:
        return len(json.dumps(self.to_dict(), ensure_ascii=False))


@dataclass(frozen=True)
class EstablishmentEpistemic:
    known_by_at_commit: tuple[str, ...] = ()
    routes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "known_by_at_commit": list(self.known_by_at_commit),
            "routes": dict(self.routes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EstablishmentEpistemic:
        return cls(
            known_by_at_commit=tuple(str(x) for x in data.get("known_by_at_commit", []) if str(x).strip()),
            routes={str(k): str(v) for k, v in dict(data.get("routes") or {}).items()},
        )


@dataclass(frozen=True)
class EpistemicAuthorityRef:
    ref_kind: EpistemicAuthorityRefKind
    ref_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"ref_kind": self.ref_kind, "ref_payload": dict(self.ref_payload)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpistemicAuthorityRef:
        return cls(
            ref_kind=data.get("ref_kind", "inherit_source_events"),  # type: ignore[arg-type]
            ref_payload=dict(data.get("ref_payload") or {}),
        )


@dataclass(frozen=True)
class StoryEvidenceProjectionProvenance:
    """Audit manifest: which PublicEvent components composed globally searchable text."""

    source_event_id: str
    projection_sources: tuple[str, ...]
    scoped_evidence_present: bool = False
    scoped_evidence_projected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_event_id": self.source_event_id,
            "projection_sources": list(self.projection_sources),
            "scoped_evidence_present": self.scoped_evidence_present,
            "scoped_evidence_projected": self.scoped_evidence_projected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> StoryEvidenceProjectionProvenance | None:
        if not isinstance(data, dict) or not data:
            return None
        sources = [
            str(item).strip()
            for item in list(data.get("projection_sources") or [])
            if str(item).strip()
        ]
        event_id = str(data.get("source_event_id", "") or "").strip()
        if not event_id and not sources:
            return None
        return cls(
            source_event_id=event_id,
            projection_sources=tuple(sources),
            scoped_evidence_present=bool(data.get("scoped_evidence_present")),
            scoped_evidence_projected=bool(data.get("scoped_evidence_projected")),
        )


@dataclass
class StoryKnowledgeRecord:
    schema_version: int
    record_kind: RecordKind
    memory_scope_id: str
    source_session_id: str
    source_domain_commit_id: str
    hg_scene_id: str
    turn_index: int | None
    event_type: str | None
    participants: list[str] = field(default_factory=list)
    location: str | None = None
    stable_refs: list[StableRef] = field(default_factory=list)
    grounding_markers: list[str] = field(default_factory=list)
    evidence: StoryEvidence = field(default_factory=lambda: StoryEvidence(None, ""))
    establishment_epistemic: EstablishmentEpistemic | None = None
    related_refs: list[StoryRelation] = field(default_factory=list)
    event_id: str | None = None
    story_record_id: str | None = None
    epistemic_authority_ref: EpistemicAuthorityRef | None = None
    submission_authority_ref: str | None = None
    content_hash: str = ""
    written_at: str = ""
    evidence_projection: StoryEvidenceProjectionProvenance | None = None

    @property
    def record_id(self) -> str:
        if self.record_kind == "occurrence":
            return str(self.event_id or "")
        return str(self.story_record_id or "")

    def compute_content_hash(self) -> str:
        payload = self.to_dict(include_hash=False)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "record_kind": self.record_kind,
            "memory_scope_id": self.memory_scope_id,
            "source_session_id": self.source_session_id,
            "source_domain_commit_id": self.source_domain_commit_id,
            "hg_scene_id": self.hg_scene_id,
            "turn_index": self.turn_index,
            "event_type": self.event_type,
            "participants": list(self.participants),
            "location": self.location,
            "stable_refs": [ref.to_dict() for ref in self.stable_refs],
            "grounding_markers": list(self.grounding_markers),
            "evidence": self.evidence.to_dict(),
            "related_refs": [ref.to_dict() for ref in self.related_refs],
        }
        if self.establishment_epistemic is not None:
            payload["establishment_epistemic"] = self.establishment_epistemic.to_dict()
        if self.event_id:
            payload["event_id"] = self.event_id
        if self.story_record_id:
            payload["story_record_id"] = self.story_record_id
        if self.epistemic_authority_ref is not None:
            payload["epistemic_authority_ref"] = self.epistemic_authority_ref.to_dict()
        if self.submission_authority_ref:
            payload["submission_authority_ref"] = self.submission_authority_ref
        if include_hash:
            payload["content_hash"] = self.content_hash or self.compute_content_hash()
        if self.written_at:
            payload["written_at"] = self.written_at
        if self.evidence_projection is not None:
            payload["evidence_projection"] = self.evidence_projection.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryKnowledgeRecord:
        evidence_raw = dict(data.get("evidence") or {})
        epistemic_raw = data.get("establishment_epistemic")
        authority_raw = data.get("epistemic_authority_ref")
        return cls(
            schema_version=int(data.get("schema_version", STORY_KNOWLEDGE_SCHEMA_VERSION)),
            record_kind=data.get("record_kind", "occurrence"),  # type: ignore[arg-type]
            memory_scope_id=str(data.get("memory_scope_id", "")),
            source_session_id=str(data.get("source_session_id", "")),
            source_domain_commit_id=str(data.get("source_domain_commit_id", "")),
            hg_scene_id=str(data.get("hg_scene_id", "")),
            turn_index=int(data["turn_index"]) if data.get("turn_index") is not None else None,
            event_type=data.get("event_type"),
            participants=[str(x) for x in data.get("participants", [])],
            location=data.get("location"),
            stable_refs=[StableRef.from_dict(item) for item in data.get("stable_refs", []) if isinstance(item, dict)],
            grounding_markers=[str(x) for x in data.get("grounding_markers", []) if str(x).strip()],
            evidence=StoryEvidence.from_dict(evidence_raw),
            establishment_epistemic=(
                EstablishmentEpistemic.from_dict(epistemic_raw) if isinstance(epistemic_raw, dict) else None
            ),
            related_refs=[
                StoryRelation.from_dict(item) for item in data.get("related_refs", []) if isinstance(item, dict)
            ],
            event_id=data.get("event_id"),
            story_record_id=data.get("story_record_id"),
            epistemic_authority_ref=(
                EpistemicAuthorityRef.from_dict(authority_raw) if isinstance(authority_raw, dict) else None
            ),
            submission_authority_ref=data.get("submission_authority_ref"),
            content_hash=str(data.get("content_hash", "")),
            written_at=str(data.get("written_at", "")),
            evidence_projection=StoryEvidenceProjectionProvenance.from_dict(
                data.get("evidence_projection")
                if isinstance(data.get("evidence_projection"), dict)
                else None
            ),
        )

    def embedding_text(self) -> str:
        parts = [
            self.evidence.summary or "",
            self.evidence.committed_text,
            self.evidence.context_before,
            self.evidence.context_after,
            " ".join(self.participants),
            self.location or "",
        ]
        return "\n".join(part for part in parts if part.strip()).strip()


@dataclass(frozen=True)
class DerivedStoryRecordSubmission:
    story_record_id: str
    memory_scope_id: str
    source_domain_commit_id: str
    source_session_id: str
    hg_scene_id: str
    source_event_ids: tuple[str, ...]
    stable_refs: tuple[StableRef, ...]
    evidence: StoryEvidence
    epistemic_authority_ref: EpistemicAuthorityRef
    submission_authority_ref: str
    related_refs: tuple[StoryRelation, ...] = ()
    turn_index: int | None = None
    location: str | None = None
    participants: tuple[str, ...] = ()

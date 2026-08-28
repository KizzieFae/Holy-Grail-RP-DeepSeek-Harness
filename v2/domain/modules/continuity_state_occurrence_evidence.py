"""Bounded occurrence evidence companion for promoted PublicEvents (Issue #51)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Implementation-level bounds (architectural invariant: bounded + semantically sufficient).
MAX_CONTRIBUTION_CONTENT = 500
MAX_CONTRIBUTIONS = 5
MAX_TRIGGER_EXCERPT = 300
MAX_SCOPED_EVIDENCE = 3
MAX_FACT_REFS = 12
MAX_SUMMARY_LEN = 500


def _bound_text(text: str, *, limit: int) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


@dataclass
class OccurrenceContribution:
    producer: str
    contribution_kind: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "producer": self.producer,
            "contribution_kind": self.contribution_kind,
            "content": self.content,
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OccurrenceContribution:
        meta = data.get("metadata")
        return cls(
            producer=str(data.get("producer", "") or ""),
            contribution_kind=str(data.get("contribution_kind", "") or ""),
            content=str(data.get("content", "") or ""),
            metadata={
                str(k): str(v)
                for k, v in (meta or {}).items()
                if str(k).strip() and str(v).strip()
            },
        )


@dataclass
class TriggeringUser:
    entry_id: str
    speaker: str
    content: str | None = None
    hg_round_id: str | None = None
    sequence_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "entry_id": self.entry_id,
            "speaker": self.speaker,
        }
        if self.content:
            payload["content"] = self.content
        if self.hg_round_id:
            payload["hg_round_id"] = self.hg_round_id
        if self.sequence_index is not None:
            payload["sequence_index"] = self.sequence_index
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TriggeringUser | None:
        entry_id = str(data.get("entry_id", "") or "").strip()
        if not entry_id:
            return None
        seq = data.get("sequence_index")
        return cls(
            entry_id=entry_id,
            speaker=str(data.get("speaker", "") or ""),
            content=(
                str(data.get("content")).strip()
                if data.get("content") is not None and str(data.get("content")).strip()
                else None
            ),
            hg_round_id=(
                str(data.get("hg_round_id")).strip()
                if data.get("hg_round_id")
                else None
            ),
            sequence_index=int(seq) if seq is not None else None,
        )


@dataclass
class StructuredFactRef:
    ref_kind: str
    ref_id: str

    def to_dict(self) -> dict[str, str]:
        return {"ref_kind": self.ref_kind, "ref_id": self.ref_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StructuredFactRef | None:
        ref_id = str(data.get("ref_id", "") or "").strip()
        if not ref_id:
            return None
        return cls(
            ref_kind=str(data.get("ref_kind", "") or "fact"),
            ref_id=ref_id,
        )


@dataclass
class ScopedEvidence:
    audibility: str
    audience: list[str]
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "audibility": self.audibility,
            "audience": list(self.audience),
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScopedEvidence | None:
        content = str(data.get("content", "") or "").strip()
        if not content:
            return None
        audience = [str(x) for x in list(data.get("audience") or []) if str(x).strip()]
        return cls(
            audibility=str(data.get("audibility", "") or "private"),
            audience=audience,
            content=content,
        )


@dataclass
class OccurrenceEvidence:
    contributions: list[OccurrenceContribution] = field(default_factory=list)
    triggering_user: TriggeringUser | None = None
    structured_fact_refs: list[StructuredFactRef] = field(default_factory=list)
    scoped_evidence: list[ScopedEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.contributions:
            payload["contributions"] = [item.to_dict() for item in self.contributions]
        if self.triggering_user is not None:
            payload["triggering_user"] = self.triggering_user.to_dict()
        if self.structured_fact_refs:
            payload["structured_fact_refs"] = [
                item.to_dict() for item in self.structured_fact_refs
            ]
        if self.scoped_evidence:
            payload["scoped_evidence"] = [item.to_dict() for item in self.scoped_evidence]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OccurrenceEvidence | None:
        if not isinstance(data, dict) or not data:
            return None
        contributions = [
            OccurrenceContribution.from_dict(item)
            for item in list(data.get("contributions") or [])
            if isinstance(item, dict)
        ]
        contributions = [c for c in contributions if c.content.strip()][:MAX_CONTRIBUTIONS]
        refs = [
            StructuredFactRef.from_dict(item)
            for item in list(data.get("structured_fact_refs") or [])
            if isinstance(item, dict)
        ]
        refs = [r for r in refs if r is not None][:MAX_FACT_REFS]
        scoped = [
            ScopedEvidence.from_dict(item)
            for item in list(data.get("scoped_evidence") or [])
            if isinstance(item, dict)
        ]
        scoped = [s for s in scoped if s is not None][:MAX_SCOPED_EVIDENCE]
        trigger = (
            TriggeringUser.from_dict(data.get("triggering_user"))
            if isinstance(data.get("triggering_user"), dict)
            else None
        )
        if not (contributions or trigger or refs or scoped):
            return None
        return cls(
            contributions=contributions,
            triggering_user=trigger,
            structured_fact_refs=[r for r in refs if r is not None],
            scoped_evidence=[s for s in scoped if s is not None],
        )


def globally_embeddable_occurrence_text(
    *,
    summary: str,
    occurrence_evidence: OccurrenceEvidence | None,
) -> str:
    """Compose epistemically global searchable text (excludes scoped private evidence)."""
    parts: list[str] = []
    base = str(summary or "").strip()
    if base:
        parts.append(base)
    if occurrence_evidence is not None:
        for contribution in occurrence_evidence.contributions:
            text = str(contribution.content or "").strip()
            if text:
                parts.append(text)
        trigger = occurrence_evidence.triggering_user
        if trigger is not None and trigger.content:
            excerpt = str(trigger.content).strip()
            if excerpt:
                parts.append(f"Player trigger: {excerpt}")
    return _bound_text("\n".join(parts), limit=MAX_SUMMARY_LEN * 2)


def globally_projected_source_manifest(
    *,
    event_id: str,
    summary: str,
    occurrence_evidence: OccurrenceEvidence | None,
) -> dict[str, Any]:
    """Bounded audit manifest for globally eligible #50 projection components (#51)."""
    sources: list[str] = []
    if str(summary or "").strip():
        sources.append("summary")
    scoped_present = False
    if occurrence_evidence is not None:
        for idx, contribution in enumerate(occurrence_evidence.contributions):
            if str(contribution.content or "").strip():
                sources.append(
                    "occurrence_evidence.contribution:"
                    f"{contribution.producer}:{contribution.contribution_kind}:{idx}"
                )
        trigger = occurrence_evidence.triggering_user
        if trigger is not None and str(trigger.content or "").strip():
            entry_id = str(trigger.entry_id or "").strip()
            sources.append(
                f"triggering_user:{entry_id}" if entry_id else "triggering_user"
            )
        scoped_present = bool(occurrence_evidence.scoped_evidence)
    return {
        "source_event_id": str(event_id or "").strip(),
        "projection_sources": sources,
        "scoped_evidence_present": scoped_present,
        "scoped_evidence_projected": False,
    }


def parse_occurrence_evidence(data: dict[str, Any] | None) -> OccurrenceEvidence | None:
    return OccurrenceEvidence.from_dict(data)

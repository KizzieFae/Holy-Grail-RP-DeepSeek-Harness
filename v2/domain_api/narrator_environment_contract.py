"""Narrator environmental-response contracts (#49)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

EnvironmentalDetailCategory = Literal[
    "A",
    "B1",
    "B2",
    "C",
    "cannot_safely_resolve",
]

MediationOutcomeKind = Literal[
    "match",
    "no_match",
    "ambiguous",
    "forbidden",
    "retrieval_failure",
    "mediation_failure",
]

ENVIRONMENTAL_DESCRIPTOR_MARKER = "environmental_descriptor"
ENVIRONMENTAL_DESCRIPTOR_EVENT_TYPE = "environmental_descriptor"


@dataclass(frozen=True)
class EnvironmentalDescriptor:
    """One perceptible property on a persistent referent."""

    property_key: str
    value: str
    source: Literal["authored", "story_derived"]
    stable_refs: tuple[str, ...] = ()
    story_record_id: str | None = None
    authored_knowledge_id: str | None = None
    supersedes: str | None = None
    turn_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "property_key": self.property_key,
            "value": self.value,
            "source": self.source,
            "stable_refs": list(self.stable_refs),
        }
        if self.story_record_id:
            payload["story_record_id"] = self.story_record_id
        if self.authored_knowledge_id:
            payload["authored_knowledge_id"] = self.authored_knowledge_id
        if self.supersedes:
            payload["supersedes"] = self.supersedes
        if self.turn_index is not None:
            payload["turn_index"] = self.turn_index
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvironmentalDescriptor | None:
        key = str(data.get("property_key", "") or "").strip()
        value = str(data.get("value", "") or "").strip()
        if not key or not value:
            return None
        source = data.get("source", "story_derived")
        if source not in ("authored", "story_derived"):
            source = "story_derived"
        refs = tuple(
            str(item).strip()
            for item in list(data.get("stable_refs") or [])
            if str(item).strip()
        )
        return cls(
            property_key=key,
            value=value,
            source=source,  # type: ignore[arg-type]
            stable_refs=refs,
            story_record_id=str(data.get("story_record_id", "") or "") or None,
            authored_knowledge_id=str(data.get("authored_knowledge_id", "") or "") or None,
            supersedes=str(data.get("supersedes", "") or "") or None,
            turn_index=(
                int(data["turn_index"]) if data.get("turn_index") is not None else None
            ),
        )


@dataclass(frozen=True)
class EnvironmentalConflict:
    property_key: str
    values: tuple[str, ...]
    record_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_key": self.property_key,
            "values": list(self.values),
            "record_ids": list(self.record_ids),
        }


@dataclass
class EnvironmentalCurrentView:
    """Deterministic projection: authored + story-derived environmental truth."""

    location_ref: str
    location_label: str
    effective_descriptors: dict[str, EnvironmentalDescriptor] = field(default_factory=dict)
    conflicts: list[EnvironmentalConflict] = field(default_factory=list)
    recent_changes: list[EnvironmentalDescriptor] = field(default_factory=list)
    assembly_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_ref": self.location_ref,
            "location_label": self.location_label,
            "effective_descriptors": {
                key: desc.to_dict() for key, desc in self.effective_descriptors.items()
            },
            "conflicts": [item.to_dict() for item in self.conflicts],
            "recent_changes": [item.to_dict() for item in self.recent_changes],
            "assembly_metadata": dict(self.assembly_metadata),
        }


@dataclass
class NarratorEnvironmentPacket:
    """Bounded environmental baseline for Narrator manifest assembly."""

    location_refs: tuple[str, ...]
    effective_descriptors: tuple[EnvironmentalDescriptor, ...]
    stable_sub_referents: tuple[str, ...]
    recent_environmental_changes: tuple[EnvironmentalDescriptor, ...]
    carryover_b2_refs: tuple[str, ...]
    assembly_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_refs": list(self.location_refs),
            "effective_descriptors": [item.to_dict() for item in self.effective_descriptors],
            "stable_sub_referents": list(self.stable_sub_referents),
            "recent_environmental_changes": [
                item.to_dict() for item in self.recent_environmental_changes
            ],
            "carryover_b2_refs": list(self.carryover_b2_refs),
            "assembly_metadata": dict(self.assembly_metadata),
        }

    def render_summary(self, *, max_chars: int = 4000) -> str:
        lines = [
            f"Active location: {self.location_refs[0] if self.location_refs else 'unknown'}",
            "Established environmental properties:",
        ]
        if self.effective_descriptors:
            for desc in self.effective_descriptors:
                lines.append(f"- {desc.property_key}: {desc.value} ({desc.source})")
        else:
            lines.append("- (no established environmental descriptors for this location)")
        if self.recent_environmental_changes:
            lines.append("Recent authoritative environmental changes:")
            for desc in self.recent_environmental_changes[:5]:
                lines.append(f"- {desc.property_key}: {desc.value}")
        text = "\n".join(lines)
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "…"


@dataclass(frozen=True)
class NarratorInformationNeed:
    need_id: str
    question: str
    referent_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "need_id": self.need_id,
            "question": self.question,
            "referent_refs": list(self.referent_refs),
        }


@dataclass
class NarratorEnvironmentN1Result:
    baseline_sufficient: bool
    information_needs: list[NarratorInformationNeed] = field(default_factory=list)
    assessment_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_sufficient": self.baseline_sufficient,
            "information_needs": [item.to_dict() for item in self.information_needs],
            "assessment_notes": self.assessment_notes,
        }


@dataclass
class NarratorEnvironmentResolution:
    need_id: str | None
    category: EnvironmentalDetailCategory
    detail: str
    property_key: str | None = None
    value: str | None = None
    stable_refs: tuple[str, ...] = ()
    mediation_outcome: MediationOutcomeKind | None = None
    establishment_record_id: str | None = None
    reasoning_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "need_id": self.need_id,
            "category": self.category,
            "detail": self.detail,
            "reasoning_summary": self.reasoning_summary,
        }
        if self.property_key:
            payload["property_key"] = self.property_key
        if self.value:
            payload["value"] = self.value
        if self.stable_refs:
            payload["stable_refs"] = list(self.stable_refs)
        if self.mediation_outcome:
            payload["mediation_outcome"] = self.mediation_outcome
        if self.establishment_record_id:
            payload["establishment_record_id"] = self.establishment_record_id
        return payload


@dataclass
class NarratorEnvironmentCognitionAudit:
    """Forensic audit record for one Narrator environmental cognition cycle."""

    cognition_id: str
    location_ref: str
    n1: NarratorEnvironmentN1Result
    librarian_queries: list[dict[str, Any]] = field(default_factory=list)
    n2_resolutions: list[NarratorEnvironmentResolution] = field(default_factory=list)
    establishment_decisions: list[dict[str, Any]] = field(default_factory=list)
    triggering_user: dict[str, Any] | None = None
    domain_commit_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cognition_id": self.cognition_id,
            "location_ref": self.location_ref,
            "n1": self.n1.to_dict(),
            "librarian_queries": list(self.librarian_queries),
            "n2_resolutions": [item.to_dict() for item in self.n2_resolutions],
            "establishment_decisions": list(self.establishment_decisions),
            "triggering_user": dict(self.triggering_user) if self.triggering_user else None,
            "domain_commit_id": self.domain_commit_id,
        }


def environmental_descriptor_payload(
    *,
    property_key: str,
    value: str,
    stable_refs: tuple[str, ...] = (),
    supersedes: str | None = None,
) -> str:
    return json.dumps(
        {
            "property_key": property_key,
            "value": value,
            "stable_refs": list(stable_refs),
            **({"supersedes": supersedes} if supersedes else {}),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def parse_environmental_descriptor_payload(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw.startswith("{"):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if not str(data.get("property_key", "") or "").strip():
        return None
    return data

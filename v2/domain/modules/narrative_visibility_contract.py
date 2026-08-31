"""NarrativeVisibilityRecord contract (#81) — viewer eligibility for history entries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

NARRATIVE_VISIBILITY_SCHEMA_VERSION = 1

UnitKind = Literal[
    "observable_scene",
    "observable_event",
    "speech",
    "internal",
    "presentation_only",
]

ValidationStatus = Literal[
    "valid",
    "invalid_fallback_structured",
    "invalid_excluded",
]

# Runaway protection — derived from narrator 8192-token ceiling (~20k chars typical prose).
MAX_NVR_UNIT_TEXT_CHARS = 4096
MAX_NVR_UNITS = 40
MAX_NVR_TOTAL_TEXT_CHARS = 20000

VALID_UNIT_KINDS = frozenset(
    {
        "observable_scene",
        "observable_event",
        "speech",
        "internal",
        "presentation_only",
    }
)


@dataclass
class NarrativeVisibilityUnit:
    unit_id: str
    kind: str
    text: str
    recipients: dict[str, Any]
    beat_index: int | None = None
    source: str = "narrator_generation"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "unit_id": self.unit_id,
            "kind": self.kind,
            "text": self.text,
            "recipients": dict(self.recipients),
            "source": self.source,
        }
        if self.beat_index is not None:
            payload["beat_index"] = self.beat_index
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NarrativeVisibilityUnit | None:
        unit_id = str(data.get("unit_id", "") or "").strip()
        kind = str(data.get("kind", "") or "").strip()
        text = str(data.get("text", "") or "").strip()
        recipients = data.get("recipients")
        if not unit_id or kind not in VALID_UNIT_KINDS or not text:
            return None
        if not isinstance(recipients, dict):
            return None
        beat_raw = data.get("beat_index")
        beat_index = int(beat_raw) if beat_raw is not None else None
        return cls(
            unit_id=unit_id,
            kind=kind,
            text=text,
            recipients=dict(recipients),
            beat_index=beat_index,
            source=str(data.get("source", "narrator_generation") or "narrator_generation"),
        )


@dataclass
class NarrativeVisibilityRecord:
    schema_version: int
    record_id: str
    units: list[NarrativeVisibilityUnit]
    validation_status: str = "valid"
    validation_notes: list[str] = field(default_factory=list)
    generation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "units": [unit.to_dict() for unit in self.units],
            "validation_status": self.validation_status,
            "validation_notes": list(self.validation_notes),
            "generation": dict(self.generation),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NarrativeVisibilityRecord | None:
        if not isinstance(data, dict):
            return None
        units_raw = data.get("units")
        if not isinstance(units_raw, list):
            return None
        units: list[NarrativeVisibilityUnit] = []
        for item in units_raw:
            if not isinstance(item, dict):
                continue
            unit = NarrativeVisibilityUnit.from_dict(item)
            if unit is not None:
                units.append(unit)
        if not units:
            return None
        return cls(
            schema_version=int(data.get("schema_version", NARRATIVE_VISIBILITY_SCHEMA_VERSION)),
            record_id=str(data.get("record_id", "") or f"nvr-{uuid.uuid4()}"),
            units=units,
            validation_status=str(data.get("validation_status", "valid") or "valid"),
            validation_notes=[
                str(note) for note in list(data.get("validation_notes") or []) if str(note).strip()
            ],
            generation=dict(data.get("generation") or {}),
        )


def narrative_visibility_from_metadata(metadata: dict[str, Any] | None) -> NarrativeVisibilityRecord | None:
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("narrative_visibility")
    record = NarrativeVisibilityRecord.from_dict(raw if isinstance(raw, dict) else None)
    if record is None:
        return None
    if record.validation_status != "valid":
        return None
    return record

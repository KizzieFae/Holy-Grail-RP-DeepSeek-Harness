"""Source-neutral perceptual visibility contract (#90 / #81 lineage)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

PERCEPTUAL_VISIBILITY_SCHEMA_VERSION = 2
LEGACY_NARRATIVE_VISIBILITY_SCHEMA_VERSION = 1

UnitKind = Literal[
    "observable_scene",
    "observable_event",
    "speech",
    "internal",
    "presentation_only",
    "uniform_projection",
]

ValidationStatus = Literal[
    "valid",
    "invalid_fallback_structured",
    "invalid_excluded",
    "historical_partial",
]

# Runaway protection — derived from narrator 8192-token ceiling (~20k chars typical prose).
MAX_PVR_UNIT_TEXT_CHARS = 4096
MAX_PVR_UNITS = 40
MAX_PVR_TOTAL_TEXT_CHARS = 20000

VALID_UNIT_KINDS = frozenset(
    {
        "observable_scene",
        "observable_event",
        "speech",
        "internal",
        "presentation_only",
        "uniform_projection",
    }
)

METADATA_KEY = "perceptual_visibility"
LEGACY_METADATA_KEY = "narrative_visibility"
VALIDATION_AUDIT_KEY = "perceptual_visibility_validation"

PLAYER_SOURCE_KIND = "player"
CHARACTER_SOURCE_KIND = "character"
PLAYER_PERCEPT_UNAVAILABLE_MARKER = (
    "[Player turn — perceptual detail unavailable to this character]"
)


@dataclass
class PerceptualVisibilityUnit:
    unit_id: str
    kind: str
    text: str
    recipients: dict[str, Any]
    authority: dict[str, Any] | None = None
    source_provenance: dict[str, Any] = field(default_factory=dict)
    source: str = "narrator_generation"
    perception_channel: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "unit_id": self.unit_id,
            "kind": self.kind,
            "text": self.text,
            "recipients": dict(self.recipients),
            "source": self.source,
        }
        if self.perception_channel:
            payload["perception_channel"] = self.perception_channel
        if self.authority is not None:
            payload["authority"] = dict(self.authority)
        if self.source_provenance:
            payload["source_provenance"] = dict(self.source_provenance)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerceptualVisibilityUnit | None:
        unit_id = str(data.get("unit_id", "") or "").strip()
        kind = str(data.get("kind", "") or "").strip()
        text = str(data.get("text", "") or "").strip()
        recipients = data.get("recipients")
        if not unit_id or kind not in VALID_UNIT_KINDS or not text:
            return None
        if not isinstance(recipients, dict):
            return None
        authority_raw = data.get("authority")
        authority = dict(authority_raw) if isinstance(authority_raw, dict) else None
        provenance_raw = data.get("source_provenance")
        provenance = dict(provenance_raw) if isinstance(provenance_raw, dict) else {}
        beat_raw = data.get("beat_index")
        if beat_raw is not None and "beat_index" not in provenance:
            provenance["beat_index"] = int(beat_raw)
        channel_raw = data.get("perception_channel")
        perception_channel = (
            str(channel_raw).strip()
            if channel_raw is not None and str(channel_raw).strip()
            else None
        )
        return cls(
            unit_id=unit_id,
            kind=kind,
            text=text,
            recipients=dict(recipients),
            authority=authority,
            source_provenance=provenance,
            source=str(data.get("source", "narrator_generation") or "narrator_generation"),
            perception_channel=perception_channel,
        )


@dataclass
class PerceptualVisibilityRecord:
    schema_version: int
    record_id: str
    units: list[PerceptualVisibilityUnit]
    source_kind: str = "unknown"
    validation_status: str = "valid"
    validation_profile: str = ""
    validation_notes: list[str] = field(default_factory=list)
    generation: dict[str, Any] = field(default_factory=dict)
    recovery: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "source_kind": self.source_kind,
            "units": [unit.to_dict() for unit in self.units],
            "validation_status": self.validation_status,
            "validation_profile": self.validation_profile,
            "validation_notes": list(self.validation_notes),
            "generation": dict(self.generation),
        }
        if self.recovery:
            payload["recovery"] = dict(self.recovery)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PerceptualVisibilityRecord | None:
        if not isinstance(data, dict):
            return None
        units_raw = data.get("units")
        if not isinstance(units_raw, list):
            return None
        units: list[PerceptualVisibilityUnit] = []
        for item in units_raw:
            if not isinstance(item, dict):
                continue
            unit = PerceptualVisibilityUnit.from_dict(item)
            if unit is not None:
                units.append(unit)
        validation_status = str(data.get("validation_status", "valid") or "valid")
        recovery = dict(data.get("recovery") or {})
        source_kind = str(data.get("source_kind", "unknown") or "unknown")
        if not units:
            if not (
                source_kind == PLAYER_SOURCE_KIND
                and validation_status == "invalid_excluded"
                and recovery.get("failure_class")
            ):
                return None
        return cls(
            schema_version=int(data.get("schema_version", PERCEPTUAL_VISIBILITY_SCHEMA_VERSION)),
            record_id=str(data.get("record_id", "") or f"pvr-{uuid.uuid4()}"),
            source_kind=source_kind,
            units=units,
            validation_status=validation_status,
            validation_profile=str(data.get("validation_profile", "") or ""),
            validation_notes=[
                str(note) for note in list(data.get("validation_notes") or []) if str(note).strip()
            ],
            generation=dict(data.get("generation") or {}),
            recovery=recovery,
        )

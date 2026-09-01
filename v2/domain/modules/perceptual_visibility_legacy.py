"""Historical metadata normalization for perceptual visibility (#90)."""

from __future__ import annotations

from typing import Any

from perceptual_visibility_contract import (
    LEGACY_METADATA_KEY,
    LEGACY_NARRATIVE_VISIBILITY_SCHEMA_VERSION,
    METADATA_KEY,
    PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
    PerceptualVisibilityRecord,
    PerceptualVisibilityUnit,
)
from perceptual_visibility_validation import ensure_unit_authority_resolved


def _resolve_legacy_speech_authority(
    record: PerceptualVisibilityRecord,
    *,
    structured_move: dict[str, Any] | None,
    acting_character: str | None,
) -> PerceptualVisibilityRecord:
    if not structured_move or not acting_character:
        return record
    units = [
        ensure_unit_authority_resolved(
            unit,
            structured_move=structured_move,
            acting_character=acting_character,
        )
        for unit in record.units
    ]
    return PerceptualVisibilityRecord(
        schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
        record_id=record.record_id,
        source_kind=record.source_kind,
        units=units,
        validation_status=record.validation_status,
        validation_profile=record.validation_profile,
        validation_notes=list(record.validation_notes),
        generation=dict(record.generation),
        recovery=dict(record.recovery),
    )


def perceptual_visibility_record_from_entry_metadata(
    metadata: dict[str, Any] | None,
    *,
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
) -> tuple[PerceptualVisibilityRecord | None, dict[str, Any]]:
    """Load canonical record from entry metadata; normalize legacy shapes at read boundary only."""
    provenance: dict[str, Any] = {
        "historical_normalization": False,
        "legacy_metadata_key": None,
        "legacy_schema_version": None,
    }
    if not isinstance(metadata, dict):
        return None, provenance

    raw = metadata.get(METADATA_KEY)
    legacy = False
    if raw is None:
        raw = metadata.get(LEGACY_METADATA_KEY)
        if raw is not None:
            legacy = True
            provenance["historical_normalization"] = True
            provenance["legacy_metadata_key"] = LEGACY_METADATA_KEY

    if not isinstance(raw, dict):
        return None, provenance

    record = PerceptualVisibilityRecord.from_dict(raw)
    if record is None:
        return None, provenance

    if legacy or record.schema_version < PERCEPTUAL_VISIBILITY_SCHEMA_VERSION:
        provenance["historical_normalization"] = True
        provenance["legacy_schema_version"] = record.schema_version
        if record.schema_version <= LEGACY_NARRATIVE_VISIBILITY_SCHEMA_VERSION:
            record = _resolve_legacy_speech_authority(
                record,
                structured_move=structured_move,
                acting_character=acting_character,
            )
            record = PerceptualVisibilityRecord(
                schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
                record_id=record.record_id,
                source_kind=record.source_kind or ("narrator" if legacy else record.source_kind),
                units=record.units,
                validation_status=record.validation_status,
                validation_profile=record.validation_profile,
                validation_notes=list(record.validation_notes),
                generation=dict(record.generation),
                recovery=dict(record.recovery),
            )

    # Only projectable statuses reach the projector.
    if record.validation_status not in ("valid", "invalid_fallback_structured"):
        if not (
            record.source_kind == "player"
            and record.validation_status == "invalid_excluded"
            and isinstance(record.recovery, dict)
            and record.recovery.get("failure_class")
        ):
            return None, provenance

    return record, provenance

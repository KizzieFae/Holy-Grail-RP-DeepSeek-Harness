"""Host-side perceptual visibility validation and attachment (#90)."""

from __future__ import annotations

from typing import Any

from perceptual_visibility_contract import (
    METADATA_KEY,
    VALIDATION_AUDIT_KEY,
    PerceptualVisibilityRecord,
)
from perceptual_visibility_validation import (
    ValidationProfile,
    validate_perceptual_visibility_record,
)


def validate_and_build_perceptual_visibility(
    *,
    units_raw: list[dict[str, Any]] | list[Any] | None,
    profile: ValidationProfile,
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
    source_kind: str = "unknown",
    generation: dict[str, Any] | None = None,
) -> tuple[PerceptualVisibilityRecord | None, dict[str, Any]]:
    if not units_raw:
        return None, {
            "accepted": False,
            "reason": "missing perceptual_visibility units",
            "validation_profile": profile.value,
        }
    result = validate_perceptual_visibility_record(
        units_raw=list(units_raw),
        profile=profile,
        structured_move=structured_move,
        acting_character=acting_character,
        source_kind=source_kind,
        generation=generation,
    )
    audit = {
        "accepted": result.accepted,
        "reason": result.reason,
        "validation_notes": list(result.validation_notes),
        "validation_profile": profile.value,
        "source_kind": source_kind,
    }
    if not result.accepted or result.record is None:
        return None, audit
    return result.record, audit


def attach_perceptual_visibility_to_entry_metadata(
    metadata: dict[str, Any],
    record: PerceptualVisibilityRecord | None,
    *,
    validation_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(metadata or {})
    if record is not None:
        merged[METADATA_KEY] = record.to_dict()
    if validation_audit:
        merged[VALIDATION_AUDIT_KEY] = dict(validation_audit)
    return merged

"""Host-side NarrativeVisibilityRecord validation and attachment (#81)."""

from __future__ import annotations

from typing import Any

from narrative_visibility_contract import NarrativeVisibilityRecord
from narrative_visibility_validation import validate_narrative_visibility_record


def validate_and_build_narrative_visibility(
    *,
    units_raw: list[dict[str, Any]] | list[Any] | None,
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
    generation: dict[str, Any] | None = None,
) -> tuple[NarrativeVisibilityRecord | None, dict[str, Any]]:
    if not units_raw:
        return None, {
            "accepted": False,
            "reason": "missing narrative_visibility units",
        }
    result = validate_narrative_visibility_record(
        units_raw=list(units_raw),
        structured_move=structured_move,
        acting_character=acting_character,
        generation=generation,
    )
    audit = {
        "accepted": result.accepted,
        "reason": result.reason,
        "validation_notes": list(result.validation_notes),
    }
    if not result.accepted or result.record is None:
        return None, audit
    return result.record, audit


def attach_narrative_visibility_to_entry_metadata(
    metadata: dict[str, Any],
    record: NarrativeVisibilityRecord | None,
    *,
    validation_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(metadata or {})
    if record is not None:
        merged["narrative_visibility"] = record.to_dict()
    if validation_audit:
        merged["narrative_visibility_validation"] = dict(validation_audit)
    return merged

"""Normalization helpers for continuity mutation payloads (#170)."""

from __future__ import annotations

from typing import Any

from continuity_mutation_pipeline_types import (
    ContinuityMutationError,
    MAX_EXCURSION_ID_LEN,
    MAX_EXCURSION_PARTICIPANTS,
    MAX_SPATIAL_LOCATION_LEN,
)


def _normalize_spatial_location(value: Any) -> str:
    if not isinstance(value, str):
        raise ContinuityMutationError("spatial_transition.location must be a string")
    s = value.strip()
    if not s:
        raise ContinuityMutationError(
            "spatial_transition.location must be a non-empty string when spatial_transition is present"
        )
    if len(s) > MAX_SPATIAL_LOCATION_LEN:
        raise ContinuityMutationError("spatial_transition.location exceeds maximum length")
    return s


def _normalize_excursion_id(value: Any, *, required: bool) -> str:
    if value is None or value == "":
        if required:
            raise ContinuityMutationError("excursion_lifecycle.excursion_id is required")
        return ""
    if not isinstance(value, str):
        raise ContinuityMutationError("excursion_lifecycle.excursion_id must be a string")
    s = value.strip()
    if not s:
        if required:
            raise ContinuityMutationError("excursion_lifecycle.excursion_id must be non-empty")
        return ""
    if len(s) > MAX_EXCURSION_ID_LEN:
        raise ContinuityMutationError("excursion_lifecycle.excursion_id exceeds maximum length")
    return s


def _normalize_participant_ids(raw: Any, *, field_label: str) -> list[str]:
    if raw is None:
        raise ContinuityMutationError(f"{field_label} is required")
    if not isinstance(raw, list):
        raise ContinuityMutationError(f"{field_label} must be a list")
    out: list[str] = []
    for x in raw:
        if not isinstance(x, str):
            raise ContinuityMutationError(f"{field_label} entries must be strings")
        s = x.strip()
        if s:
            out.append(s)
    if not out:
        raise ContinuityMutationError(f"{field_label} must be non-empty")
    if len(out) > MAX_EXCURSION_PARTICIPANTS:
        raise ContinuityMutationError(f"{field_label} exceeds maximum length")
    return out

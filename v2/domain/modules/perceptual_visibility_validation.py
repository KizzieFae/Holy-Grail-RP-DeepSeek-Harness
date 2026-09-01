"""Validate and normalize perceptual visibility records (#90)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from character_move_adapters import is_canonical_v2_move, iter_speech_beats
from perceptual_visibility_authority import speech_authority_from_beat
from perceptual_visibility_contract import (
    MAX_PVR_TOTAL_TEXT_CHARS,
    MAX_PVR_UNIT_TEXT_CHARS,
    MAX_PVR_UNITS,
    PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
    PerceptualVisibilityRecord,
    PerceptualVisibilityUnit,
)
from text_comparison_profiles import canonicalize_for_presentation_verbatim


class ValidationProfile(str, Enum):
    NARRATOR_PRESENTATION = "narrator_presentation"
    OPENING = "opening"


@dataclass
class PerceptualVisibilityValidationResult:
    accepted: bool
    record: PerceptualVisibilityRecord | None = None
    reason: str = ""
    validation_notes: list[str] = field(default_factory=list)


def _scope_is_public(recipients: dict[str, Any]) -> bool:
    scope = str(recipients.get("scope", "") or "").strip().lower()
    return scope == "public"


def _normalize_units_payload(units_raw: list[Any]) -> list[PerceptualVisibilityUnit]:
    units: list[PerceptualVisibilityUnit] = []
    for index, item in enumerate(units_raw):
        if not isinstance(item, dict):
            continue
        unit = PerceptualVisibilityUnit.from_dict(item)
        if unit is None:
            continue
        if not unit.unit_id:
            unit = PerceptualVisibilityUnit(
                unit_id=f"u{index + 1}",
                kind=unit.kind,
                text=unit.text,
                recipients=unit.recipients,
                authority=unit.authority,
                source_provenance=unit.source_provenance,
                source=unit.source,
            )
        units.append(unit)
    return units


def _attach_speech_authority(
    unit: PerceptualVisibilityUnit,
    *,
    structured_move: dict[str, Any],
    acting_character: str,
) -> PerceptualVisibilityUnit | None:
    raw_beat = unit.source_provenance.get("beat_index")
    if raw_beat is None:
        return None
    beats = structured_move.get("beats")
    if not isinstance(beats, list):
        return None
    idx = int(raw_beat)
    if idx < 0 or idx >= len(beats):
        return None
    beat = beats[idx]
    if not isinstance(beat, dict) or beat.get("type") != "speech":
        return None
    authority = speech_authority_from_beat(beat, acting_character=acting_character)
    provenance = dict(unit.source_provenance)
    provenance["beat_index"] = idx
    return PerceptualVisibilityUnit(
        unit_id=unit.unit_id,
        kind=unit.kind,
        text=unit.text,
        recipients=dict(unit.recipients),
        authority=authority,
        source_provenance=provenance,
        source=unit.source,
    )


def validate_perceptual_visibility_record(
    *,
    units_raw: list[dict[str, Any]] | list[Any],
    profile: ValidationProfile,
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
    source_kind: str = "unknown",
    generation: dict[str, Any] | None = None,
) -> PerceptualVisibilityValidationResult:
    notes: list[str] = []
    units = _normalize_units_payload(list(units_raw))
    if not units:
        return PerceptualVisibilityValidationResult(
            accepted=False,
            reason="no valid perceptual visibility units",
        )

    if len(units) > MAX_PVR_UNITS:
        return PerceptualVisibilityValidationResult(
            accepted=False,
            reason=f"unit count exceeds {MAX_PVR_UNITS}",
        )

    total_chars = 0
    speech_dialogues: list[str] = []
    if isinstance(structured_move, dict) and is_canonical_v2_move(structured_move):
        for _, beat in iter_speech_beats(structured_move):
            dialogue = str(beat.get("dialogue", "") or "").strip()
            if dialogue:
                speech_dialogues.append(canonicalize_for_presentation_verbatim(dialogue))

    actor = str(acting_character or "").strip()
    filtered_units: list[PerceptualVisibilityUnit] = []
    for unit in units:
        if len(unit.text) > MAX_PVR_UNIT_TEXT_CHARS:
            return PerceptualVisibilityValidationResult(
                accepted=False,
                reason=f"unit {unit.unit_id} exceeds per-unit text bound",
            )
        total_chars += len(unit.text)
        if total_chars > MAX_PVR_TOTAL_TEXT_CHARS:
            return PerceptualVisibilityValidationResult(
                accepted=False,
                reason=f"total unit text exceeds {MAX_PVR_TOTAL_TEXT_CHARS}",
            )

        if unit.kind == "internal" and _scope_is_public(unit.recipients):
            return PerceptualVisibilityValidationResult(
                accepted=False,
                reason="internal unit cannot be public",
            )

        if unit.kind == "presentation_only":
            notes.append(f"{unit.unit_id}: presentation_only excluded from character cognition")
            continue

        working = unit
        if unit.kind == "speech":
            beat_index = unit.source_provenance.get("beat_index")
            if beat_index is None:
                return PerceptualVisibilityValidationResult(
                    accepted=False,
                    reason=f"speech unit {unit.unit_id} missing beat_index",
                )
            if profile == ValidationProfile.NARRATOR_PRESENTATION:
                if not isinstance(structured_move, dict) or not is_canonical_v2_move(structured_move):
                    return PerceptualVisibilityValidationResult(
                        accepted=False,
                        reason=f"speech unit {unit.unit_id} requires structured move",
                    )
                if not actor:
                    return PerceptualVisibilityValidationResult(
                        accepted=False,
                        reason=f"speech unit {unit.unit_id} missing acting character",
                    )
                beats = structured_move.get("beats")
                idx = int(beat_index)
                if not isinstance(beats, list) or idx < 0 or idx >= len(beats):
                    return PerceptualVisibilityValidationResult(
                        accepted=False,
                        reason=f"speech unit {unit.unit_id} invalid beat_index",
                    )
                beat = beats[idx]
                if not isinstance(beat, dict) or beat.get("type") != "speech":
                    return PerceptualVisibilityValidationResult(
                        accepted=False,
                        reason=f"speech unit {unit.unit_id} beat_index not speech",
                    )
                dialogue = str(beat.get("dialogue", "") or "").strip()
                unit_cmp = canonicalize_for_presentation_verbatim(unit.text)
                dlg_cmp = canonicalize_for_presentation_verbatim(dialogue)
                if dlg_cmp and dlg_cmp not in unit_cmp and unit_cmp not in dlg_cmp:
                    return PerceptualVisibilityValidationResult(
                        accepted=False,
                        reason=f"speech unit {unit.unit_id} dialogue mismatch",
                    )
                provenance = dict(unit.source_provenance)
                provenance["beat_index"] = idx
                working = PerceptualVisibilityUnit(
                    unit_id=unit.unit_id,
                    kind=unit.kind,
                    text=unit.text,
                    recipients=dict(unit.recipients),
                    authority=speech_authority_from_beat(beat, acting_character=actor),
                    source_provenance=provenance,
                    source=unit.source,
                )

        if working.kind in ("observable_scene", "observable_event") and speech_dialogues:
            unit_cmp = canonicalize_for_presentation_verbatim(working.text).lower()
            for dlg in speech_dialogues:
                if dlg and dlg.lower() in unit_cmp:
                    notes.append(
                        f"{working.unit_id}: observable unit contains restricted dialogue text"
                    )
                    working = None
                    break
            if working is None:
                continue

        filtered_units.append(working)

    if not filtered_units:
        return PerceptualVisibilityValidationResult(
            accepted=False,
            reason="no character-eligible units after validation",
            validation_notes=notes,
        )

    record = PerceptualVisibilityRecord(
        schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
        record_id=f"pvr-{uuid.uuid4()}",
        source_kind=source_kind,
        units=filtered_units,
        validation_status="valid",
        validation_profile=profile.value,
        validation_notes=notes,
        generation=dict(generation or {}),
    )
    return PerceptualVisibilityValidationResult(
        accepted=True,
        record=record,
        validation_notes=notes,
    )


def build_degraded_perceptual_record_from_structured_move(
    structured_move: dict[str, Any],
    *,
    acting_character: str,
    source_kind: str = "narrator",
    generation: dict[str, Any] | None = None,
) -> PerceptualVisibilityRecord | None:
    """Authoritative structured recovery only — never narrator prose or rejected LLM units."""
    if not is_canonical_v2_move(structured_move):
        return None
    actor = str(acting_character or "").strip()
    if not actor:
        return None
    units: list[PerceptualVisibilityUnit] = []
    beats = structured_move.get("beats")
    if not isinstance(beats, list):
        return None
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            continue
        beat_type = beat.get("type")
        if beat_type == "action":
            action = str(beat.get("action", "") or "").strip()
            if not action:
                continue
            units.append(
                PerceptualVisibilityUnit(
                    unit_id=f"structured-action-{index}",
                    kind="observable_event",
                    text=action,
                    recipients={"scope": "public"},
                    source="structured_recovery",
                    source_provenance={"beat_index": index, "beat_type": "action"},
                )
            )
        elif beat_type == "speech":
            dialogue = str(beat.get("dialogue", "") or "").strip()
            if not dialogue:
                continue
            units.append(
                PerceptualVisibilityUnit(
                    unit_id=f"structured-speech-{index}",
                    kind="speech",
                    text=dialogue,
                    recipients={"scope": "public"},
                    authority=speech_authority_from_beat(beat, acting_character=actor),
                    source="structured_recovery",
                    source_provenance={"beat_index": index, "beat_type": "speech"},
                )
            )
    if not units:
        return None
    return PerceptualVisibilityRecord(
        schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
        record_id=f"pvr-degraded-{uuid.uuid4()}",
        source_kind=source_kind,
        units=units,
        validation_status="invalid_fallback_structured",
        validation_profile=ValidationProfile.NARRATOR_PRESENTATION.value,
        validation_notes=["degraded structured recovery from authoritative structured_move"],
        generation=dict(generation or {}),
        recovery={
            "kind": "authoritative_structured_move",
            "acting_character": actor,
        },
    )


def ensure_unit_authority_resolved(
    unit: PerceptualVisibilityUnit,
    *,
    structured_move: dict[str, Any] | None,
    acting_character: str | None,
) -> PerceptualVisibilityUnit:
    if unit.kind != "speech" or unit.authority is not None:
        return unit
    if not isinstance(structured_move, dict) or not acting_character:
        return unit
    beat_index = unit.source_provenance.get("beat_index")
    if beat_index is None:
        return unit
    attached = _attach_speech_authority(
        unit,
        structured_move=structured_move,
        acting_character=acting_character,
    )
    return attached if attached is not None else unit

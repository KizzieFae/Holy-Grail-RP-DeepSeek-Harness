"""Validate NarrativeVisibilityRecord and reconcile with structured move authority (#81)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from character_move_adapters import is_canonical_v2_move, iter_speech_beats
from narrative_visibility_contract import (
    MAX_NVR_TOTAL_TEXT_CHARS,
    MAX_NVR_UNIT_TEXT_CHARS,
    MAX_NVR_UNITS,
    NARRATIVE_VISIBILITY_SCHEMA_VERSION,
    NarrativeVisibilityRecord,
    NarrativeVisibilityUnit,
)
from perception_audibility_visibility import speech_beat_viewer_may_perceive
from text_comparison_profiles import canonicalize_for_presentation_verbatim


@dataclass
class NarrativeVisibilityValidationResult:
    accepted: bool
    record: NarrativeVisibilityRecord | None = None
    reason: str = ""
    validation_notes: list[str] = field(default_factory=list)


def _scope_is_public(recipients: dict[str, Any]) -> bool:
    scope = str(recipients.get("scope", "") or "").strip().lower()
    return scope == "public"


def _normalize_units_payload(units_raw: list[Any]) -> list[NarrativeVisibilityUnit]:
    units: list[NarrativeVisibilityUnit] = []
    for index, item in enumerate(units_raw):
        if not isinstance(item, dict):
            continue
        unit = NarrativeVisibilityUnit.from_dict(item)
        if unit is None:
            continue
        if not unit.unit_id:
            unit = NarrativeVisibilityUnit(
                unit_id=f"u{index + 1}",
                kind=unit.kind,
                text=unit.text,
                recipients=unit.recipients,
                beat_index=unit.beat_index,
                source=unit.source,
            )
        units.append(unit)
    return units


def validate_narrative_visibility_record(
    *,
    units_raw: list[dict[str, Any]] | list[Any],
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
    generation: dict[str, Any] | None = None,
) -> NarrativeVisibilityValidationResult:
    notes: list[str] = []
    units = _normalize_units_payload(list(units_raw))
    if not units:
        return NarrativeVisibilityValidationResult(
            accepted=False,
            reason="no valid narrative visibility units",
        )

    if len(units) > MAX_NVR_UNITS:
        return NarrativeVisibilityValidationResult(
            accepted=False,
            reason=f"unit count exceeds {MAX_NVR_UNITS}",
        )

    total_chars = 0
    speech_dialogues: list[str] = []
    if isinstance(structured_move, dict) and is_canonical_v2_move(structured_move):
        for _, beat in iter_speech_beats(structured_move):
            dialogue = str(beat.get("dialogue", "") or "").strip()
            if dialogue:
                speech_dialogues.append(canonicalize_for_presentation_verbatim(dialogue))

    filtered_units: list[NarrativeVisibilityUnit] = []
    for unit in units:
        if len(unit.text) > MAX_NVR_UNIT_TEXT_CHARS:
            return NarrativeVisibilityValidationResult(
                accepted=False,
                reason=f"unit {unit.unit_id} exceeds per-unit text bound",
            )
        total_chars += len(unit.text)
        if total_chars > MAX_NVR_TOTAL_TEXT_CHARS:
            return NarrativeVisibilityValidationResult(
                accepted=False,
                reason=f"total unit text exceeds {MAX_NVR_TOTAL_TEXT_CHARS}",
            )

        if unit.kind == "internal" and _scope_is_public(unit.recipients):
            return NarrativeVisibilityValidationResult(
                accepted=False,
                reason="internal unit cannot be public",
            )

        if unit.kind == "presentation_only":
            notes.append(f"{unit.unit_id}: presentation_only excluded from character cognition")
            continue

        if unit.kind == "speech":
            if unit.beat_index is None:
                return NarrativeVisibilityValidationResult(
                    accepted=False,
                    reason=f"speech unit {unit.unit_id} missing beat_index",
                )
            if not isinstance(structured_move, dict) or not is_canonical_v2_move(structured_move):
                return NarrativeVisibilityValidationResult(
                    accepted=False,
                    reason=f"speech unit {unit.unit_id} requires structured move",
                )
            beats = structured_move.get("beats")
            if not isinstance(beats, list) or unit.beat_index < 0 or unit.beat_index >= len(beats):
                return NarrativeVisibilityValidationResult(
                    accepted=False,
                    reason=f"speech unit {unit.unit_id} invalid beat_index",
                )
            beat = beats[unit.beat_index]
            if not isinstance(beat, dict) or beat.get("type") != "speech":
                return NarrativeVisibilityValidationResult(
                    accepted=False,
                    reason=f"speech unit {unit.unit_id} beat_index not speech",
                )
            dialogue = str(beat.get("dialogue", "") or "").strip()
            unit_cmp = canonicalize_for_presentation_verbatim(unit.text)
            dlg_cmp = canonicalize_for_presentation_verbatim(dialogue)
            if dlg_cmp and dlg_cmp not in unit_cmp and unit_cmp not in dlg_cmp:
                return NarrativeVisibilityValidationResult(
                    accepted=False,
                    reason=f"speech unit {unit.unit_id} dialogue mismatch",
                )

        if unit.kind in ("observable_scene", "observable_event") and speech_dialogues:
            unit_cmp = canonicalize_for_presentation_verbatim(unit.text).lower()
            for dlg in speech_dialogues:
                if dlg and dlg.lower() in unit_cmp:
                    notes.append(
                        f"{unit.unit_id}: observable unit contains restricted dialogue text"
                    )
                    unit = None
                    break
            if unit is None:
                continue

        filtered_units.append(unit)

    if not filtered_units:
        return NarrativeVisibilityValidationResult(
            accepted=False,
            reason="no character-eligible units after validation",
            validation_notes=notes,
        )

    record = NarrativeVisibilityRecord(
        schema_version=NARRATIVE_VISIBILITY_SCHEMA_VERSION,
        record_id=f"nvr-{uuid.uuid4()}",
        units=filtered_units,
        validation_status="valid",
        validation_notes=notes,
        generation=dict(generation or {}),
    )
    return NarrativeVisibilityValidationResult(
        accepted=True,
        record=record,
        validation_notes=notes,
    )


def viewer_may_receive_speech_unit(
    *,
    beat: dict[str, Any],
    acting_character: str,
    viewer_character: str,
) -> bool:
    return speech_beat_viewer_may_perceive(
        beat,
        acting_character=acting_character,
        viewer_character=viewer_character,
    )

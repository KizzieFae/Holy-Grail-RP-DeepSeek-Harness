"""Deterministic Character perceptual visibility derivation (#92)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from character_move_adapters import is_canonical_v2_move
from perceptual_visibility_authority import speech_authority_from_beat
from perceptual_visibility_contract import (
    METADATA_KEY,
    PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
    VALIDATION_AUDIT_KEY,
    PerceptualVisibilityRecord,
    PerceptualVisibilityUnit,
)
from perceptual_visibility_validation import (
    ValidationProfile,
    PerceptualVisibilityValidationResult,
    validate_perceptual_visibility_record,
)

CHARACTER_SOURCE_KIND = "character"
CHARACTER_UNIT_SOURCE = "character_derivation"
CHARACTER_DERIVATION_PROFILE = "character_move_v1"

ACTION_RECIPIENT_SCOPES = frozenset(
    {
        "public",
        "present",
        "directed",
        "private",
        "environmental",
    }
)

HISTORICAL_PARTIAL_FAILURE_CLASS = "historical_missing_character_perceptual_derivation"


@dataclass
class CharacterPerceptualDerivationResult:
    accepted: bool
    record: PerceptualVisibilityRecord | None = None
    reason: str = ""
    validation_notes: list[str] = field(default_factory=list)


def normalize_action_recipients(beat: dict[str, Any]) -> dict[str, Any]:
    """Normalize action-beat recipients; omitted => present scope."""
    raw = beat.get("recipients")
    if raw is None:
        return {"scope": "present", "characters": [], "roles": []}
    if not isinstance(raw, dict):
        raise ValueError("action beat recipients must be an object")
    scope = str(raw.get("scope", "") or "").strip().lower()
    if scope not in ACTION_RECIPIENT_SCOPES:
        raise ValueError(f"invalid action recipients scope: {scope!r}")
    characters_raw = raw.get("characters", [])
    if not isinstance(characters_raw, list):
        raise ValueError("action beat recipients.characters must be an array")
    characters = [str(name).strip() for name in characters_raw if str(name).strip()]
    if scope in ("directed", "private") and not characters:
        raise ValueError(f"{scope} action requires non-empty recipients.characters")
    if scope in ("public", "present", "environmental") and characters:
        raise ValueError(f"{scope} action must not include non-empty recipients.characters")
    roles_raw = raw.get("roles", [])
    roles = (
        [str(role).strip() for role in roles_raw if str(role).strip()]
        if isinstance(roles_raw, list)
        else []
    )
    return {"scope": scope, "characters": characters, "roles": roles}


def _speech_recipients_from_beat(beat: dict[str, Any]) -> dict[str, Any]:
    aud = str(beat.get("audibility", "public") or "public").strip().lower()
    audience_raw = beat.get("audience")
    audience = (
        [str(name).strip() for name in audience_raw if str(name).strip()]
        if isinstance(audience_raw, list)
        else []
    )
    if aud == "public":
        return {"scope": "present", "characters": [], "roles": []}
    if aud == "directed":
        return {"scope": "directed", "characters": audience, "roles": []}
    return {"scope": "private", "characters": audience, "roles": []}


def _build_units_from_move(
    move: dict[str, Any],
    *,
    acting_character: str,
) -> list[PerceptualVisibilityUnit]:
    actor = str(acting_character or "").strip()
    beats = move.get("beats")
    if not isinstance(beats, list):
        return []
    units: list[PerceptualVisibilityUnit] = []
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            continue
        beat_type = beat.get("type")
        if beat_type == "action":
            action = str(beat.get("action", "") or "").strip()
            if not action:
                continue
            recipients = normalize_action_recipients(beat)
            units.append(
                PerceptualVisibilityUnit(
                    unit_id=f"c-action-{index}",
                    kind="observable_event",
                    text=action,
                    recipients=recipients,
                    source_provenance={
                        "beat_index": index,
                        "beat_type": "action",
                        "derivation_profile": CHARACTER_DERIVATION_PROFILE,
                    },
                    source=CHARACTER_UNIT_SOURCE,
                )
            )
        elif beat_type == "speech":
            dialogue = str(beat.get("dialogue", "") or "").strip()
            if not dialogue:
                continue
            units.append(
                PerceptualVisibilityUnit(
                    unit_id=f"c-speech-{index}",
                    kind="speech",
                    text=dialogue,
                    recipients=_speech_recipients_from_beat(beat),
                    authority=speech_authority_from_beat(beat, acting_character=actor),
                    source_provenance={
                        "beat_index": index,
                        "beat_type": "speech",
                        "derivation_profile": CHARACTER_DERIVATION_PROFILE,
                    },
                    source=CHARACTER_UNIT_SOURCE,
                )
            )
    return units


def derive_character_perceptual_record(
    move: dict[str, Any],
    *,
    acting_character: str,
) -> CharacterPerceptualDerivationResult:
    """Derive and validate canonical Character PVR from a structured move."""
    if not is_canonical_v2_move(move):
        return CharacterPerceptualDerivationResult(
            accepted=False,
            reason="structured move is not canonical v2",
        )
    actor = str(acting_character or "").strip()
    if not actor:
        return CharacterPerceptualDerivationResult(
            accepted=False,
            reason="acting character required for perceptual derivation",
        )
    try:
        units = _build_units_from_move(move, acting_character=actor)
    except ValueError as exc:
        return CharacterPerceptualDerivationResult(
            accepted=False,
            reason=str(exc),
        )
    if not units:
        return CharacterPerceptualDerivationResult(
            accepted=False,
            reason="no perceptual units derivable from character move",
        )

    validation: PerceptualVisibilityValidationResult = validate_perceptual_visibility_record(
        units_raw=[unit.to_dict() for unit in units],
        profile=ValidationProfile.CHARACTER_MOVE,
        structured_move=move,
        acting_character=actor,
        source_kind=CHARACTER_SOURCE_KIND,
        generation={"derivation_profile": CHARACTER_DERIVATION_PROFILE},
    )
    if not validation.accepted or validation.record is None:
        return CharacterPerceptualDerivationResult(
            accepted=False,
            reason=validation.reason or "character perceptual validation failed",
            validation_notes=list(validation.validation_notes),
        )
    record = validation.record
    record = PerceptualVisibilityRecord(
        schema_version=record.schema_version,
        record_id=f"pvr-character-{uuid.uuid4()}",
        source_kind=CHARACTER_SOURCE_KIND,
        units=record.units,
        validation_status=record.validation_status,
        validation_profile=record.validation_profile,
        validation_notes=list(record.validation_notes),
        generation=dict(record.generation),
        recovery=dict(record.recovery),
    )
    return CharacterPerceptualDerivationResult(
        accepted=True,
        record=record,
        validation_notes=list(validation.validation_notes),
    )


def build_historical_partial_character_record(
    structured_move: dict[str, Any],
    *,
    acting_character: str,
) -> PerceptualVisibilityRecord | None:
    """Safe-partial recovery for pre-#92 Character commits without canonical PVR."""
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
        if beat_type == "speech":
            dialogue = str(beat.get("dialogue", "") or "").strip()
            if not dialogue:
                continue
            units.append(
                PerceptualVisibilityUnit(
                    unit_id=f"historical-speech-{index}",
                    kind="speech",
                    text=dialogue,
                    recipients=_speech_recipients_from_beat(beat),
                    authority=speech_authority_from_beat(beat, acting_character=actor),
                    source="historical_partial_recovery",
                    source_provenance={
                        "beat_index": index,
                        "beat_type": "speech",
                        "derivation_profile": CHARACTER_DERIVATION_PROFILE,
                    },
                )
            )
        elif beat_type == "action":
            action = str(beat.get("action", "") or "").strip()
            if not action:
                continue
            units.append(
                PerceptualVisibilityUnit(
                    unit_id=f"historical-action-{index}",
                    kind="observable_event",
                    text=action,
                    recipients={"scope": "private", "characters": [actor], "roles": []},
                    source="historical_partial_recovery",
                    source_provenance={
                        "beat_index": index,
                        "beat_type": "action",
                        "derivation_profile": CHARACTER_DERIVATION_PROFILE,
                    },
                )
            )
    if not units:
        return None
    return PerceptualVisibilityRecord(
        schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
        record_id=f"pvr-character-historical-{uuid.uuid4()}",
        source_kind=CHARACTER_SOURCE_KIND,
        units=units,
        validation_status="historical_partial",
        validation_profile=ValidationProfile.CHARACTER_MOVE.value,
        validation_notes=["historical safe-partial recovery"],
        generation={"derivation_profile": CHARACTER_DERIVATION_PROFILE},
        recovery={"failure_class": HISTORICAL_PARTIAL_FAILURE_CLASS},
    )


def attach_character_perceptual_metadata(
    metadata: dict[str, Any],
    *,
    record: PerceptualVisibilityRecord,
    validation_audit: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(metadata or {})
    merged[METADATA_KEY] = record.to_dict()
    merged[VALIDATION_AUDIT_KEY] = dict(validation_audit)
    return merged


def build_character_validation_audit(
    result: CharacterPerceptualDerivationResult,
) -> dict[str, Any]:
    return {
        "accepted": result.accepted,
        "reason": result.reason,
        "validation_profile": ValidationProfile.CHARACTER_MOVE.value,
        "validation_notes": list(result.validation_notes),
    }

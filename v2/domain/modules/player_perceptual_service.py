"""Player perceptual decomposition validation and failure records (#91)."""

from __future__ import annotations

import uuid
from typing import Any

from perceptual_visibility_authority import speech_authority_from_player_recipients
from perceptual_visibility_contract import (
    METADATA_KEY,
    MAX_PVR_UNIT_TEXT_CHARS,
    PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
    VALIDATION_AUDIT_KEY,
    PerceptualVisibilityRecord,
    PerceptualVisibilityUnit,
)
from perceptual_visibility_validation import (
    ValidationProfile,
    PerceptualVisibilityValidationResult,
    _normalize_units_payload,
)
from player_source_accounting import (
    SOURCE_ACCOUNTING_NORMALIZATION,
    normalize_source_for_indexing,
    normalized_source_sha256,
    validate_source_accounting,
)
from player_uniform_projection import (
    UNIFORM_PROJECTION_KIND,
    UNIFORM_PROJECTION_DERIVATION_PROFILE,
    UNIFORM_PROJECTION_SYNTHESIS_ROUTE,
    UNIFORM_PROJECTION_SYNTHESIS_SOURCE,
    is_uniform_projection_synthesis_decomposition,
)

PLAYER_SOURCE_KIND = "player"
PLAYER_UNIT_SOURCE = "player_decomposition"

FAILURE_INFERENCE_UNAVAILABLE = "inference_unavailable"
FAILURE_MALFORMED_OUTPUT = "malformed_output"
FAILURE_VALIDATION_REJECTED = "validation_rejected"
FAILURE_SOURCE_ACCOUNTING_INCOMPLETE = "source_accounting_incomplete"
FAILURE_MISSING_DECOMPOSITION = "missing_decomposition"


def build_player_failure_record(
    *,
    failure_class: str,
    generation: dict[str, Any] | None = None,
    validation_notes: list[str] | None = None,
) -> PerceptualVisibilityRecord:
    return PerceptualVisibilityRecord(
        schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
        record_id=f"pvr-player-fail-{uuid.uuid4()}",
        source_kind=PLAYER_SOURCE_KIND,
        units=[],
        validation_status="invalid_excluded",
        validation_profile=ValidationProfile.PLAYER_SUBMIT.value,
        validation_notes=list(validation_notes or []),
        generation=dict(generation or {}),
        recovery={"failure_class": failure_class},
    )


def _build_source_accounting_payload(
    *,
    normalized_source: str,
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source_length": len(normalized_source),
        "source_sha256": normalized_source_sha256(normalized_source),
        "normalization": SOURCE_ACCOUNTING_NORMALIZATION,
        "segments": segments,
    }


def _segment_unit_linkage_ok(
    segments: list[dict[str, Any]],
    units: list[PerceptualVisibilityUnit],
) -> tuple[bool, str]:
    unit_ids = {unit.unit_id for unit in units}
    segment_to_units: dict[str, set[str]] = {}
    for segment in segments:
        segment_id = str(segment.get("segment_id", "") or "").strip()
        if not segment_id:
            return False, "segment missing segment_id"
        linked = {
            str(item).strip()
            for item in list(segment.get("unit_ids") or [])
            if str(item).strip()
        }
        segment_to_units[segment_id] = linked

    for unit in units:
        segment_ids = {
            str(item).strip()
            for item in list(unit.source_provenance.get("segment_ids") or [])
            if str(item).strip()
        }
        if not segment_ids:
            return False, f"unit {unit.unit_id} missing segment_ids"
        for segment_id in segment_ids:
            if segment_id not in segment_to_units:
                return False, f"unit {unit.unit_id} references unknown segment {segment_id}"
            if unit.unit_id not in segment_to_units[segment_id]:
                return False, f"unit {unit.unit_id} not linked from segment {segment_id}"
    return True, ""


def _validate_uniform_projection_decomposition(
    *,
    normalized_source: str,
    units: list[PerceptualVisibilityUnit],
    accounting_segments: list[dict[str, Any]],
    generation: dict[str, Any],
) -> tuple[list[PerceptualVisibilityUnit], str]:
    if len(units) != 1:
        return [], "uniform projection requires exactly one unit"
    unit = units[0]
    if unit.kind != UNIFORM_PROJECTION_KIND:
        return [], "uniform projection unit kind mismatch"
    if unit.source != UNIFORM_PROJECTION_SYNTHESIS_SOURCE:
        return [], "uniform projection requires synthesis source provenance"
    scope = str(unit.recipients.get("scope", "") or "").strip().lower()
    if scope != "present":
        return [], "uniform projection requires present scope"
    characters = unit.recipients.get("characters")
    roles = unit.recipients.get("roles")
    if not isinstance(characters, list) or characters:
        return [], "uniform projection cannot name character subset"
    if not isinstance(roles, list) or roles:
        return [], "uniform projection cannot name role subset"
    if unit.text != normalized_source:
        return [], "uniform projection unit text must equal normalized source"
    if len(unit.text) > MAX_PVR_UNIT_TEXT_CHARS:
        return [], "uniform projection unit exceeds per-unit text bound"
    if generation.get("derivation_profile") != UNIFORM_PROJECTION_DERIVATION_PROFILE:
        return [], "uniform projection missing derivation_profile"
    if generation.get("synthesis_route") != UNIFORM_PROJECTION_SYNTHESIS_ROUTE:
        return [], "uniform projection missing synthesis_route"
    checker = generation.get("checker")
    if not isinstance(checker, dict) or checker.get("uniform_projection_safe") is not True:
        return [], "uniform projection requires affirmative checker safety"
    inference_id = str(checker.get("inference_id", "") or "").strip()
    if not inference_id.startswith("player-visibility-triage-"):
        return [], "uniform projection requires checker inference provenance"
    if len(accounting_segments) != 1:
        return [], "uniform projection requires single accounting segment"
    segment = accounting_segments[0]
    if int(segment.get("char_start", -1)) != 0:
        return [], "uniform projection segment must start at 0"
    if int(segment.get("char_end", -1)) != len(normalized_source):
        return [], "uniform projection segment must cover full source"
    if str(segment.get("disposition", "")) != "projects":
        return [], "uniform projection segment must project"
    linked = {
        str(item).strip()
        for item in list(segment.get("unit_ids") or [])
        if str(item).strip()
    }
    if linked != {unit.unit_id}:
        return [], "uniform projection segment unit linkage mismatch"
    return [unit], ""


def validate_player_perceptual_decomposition(
    *,
    content: str,
    speaker: str,
    decomposition: dict[str, Any] | None,
) -> tuple[PerceptualVisibilityRecord, dict[str, Any]]:
    normalized_source = normalize_source_for_indexing(content)
    generation: dict[str, Any] = {}

    if not isinstance(decomposition, dict):
        record = build_player_failure_record(
            failure_class=FAILURE_MISSING_DECOMPOSITION,
            generation=generation,
            validation_notes=["player_decomposition missing"],
        )
        return record, {
            "accepted": False,
            "reason": "player_decomposition missing",
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": FAILURE_MISSING_DECOMPOSITION,
        }

    failure_class = str(decomposition.get("failure_class", "") or "").strip()
    generation = dict(decomposition.get("generation") or {})
    if failure_class:
        record = build_player_failure_record(
            failure_class=failure_class,
            generation=generation,
            validation_notes=[str(decomposition.get("reason", "") or failure_class)],
        )
        return record, {
            "accepted": False,
            "reason": str(decomposition.get("reason", "") or failure_class),
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": failure_class,
        }

    units_raw = []
    perceptual_visibility = decomposition.get("perceptual_visibility")
    if isinstance(perceptual_visibility, dict):
        units_raw = perceptual_visibility.get("units") or []
    if not isinstance(units_raw, list):
        record = build_player_failure_record(
            failure_class=FAILURE_MALFORMED_OUTPUT,
            generation=generation,
            validation_notes=["perceptual_visibility.units not a list"],
        )
        return record, {
            "accepted": False,
            "reason": "perceptual_visibility.units not a list",
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": FAILURE_MALFORMED_OUTPUT,
        }

    units = _normalize_units_payload(list(units_raw))
    generation = dict(decomposition.get("generation") or generation)

    if is_uniform_projection_synthesis_decomposition(decomposition):
        accounting_segments = []
        source_accounting = decomposition.get("source_accounting")
        if isinstance(source_accounting, dict):
            raw_segments = source_accounting.get("segments")
            if isinstance(raw_segments, list):
                accounting_segments = [dict(item) for item in raw_segments if isinstance(item, dict)]
        uniform_units, uniform_reason = _validate_uniform_projection_decomposition(
            normalized_source=normalized_source,
            units=units,
            accounting_segments=accounting_segments,
            generation=generation,
        )
        if not uniform_units:
            record = build_player_failure_record(
                failure_class=FAILURE_VALIDATION_REJECTED,
                generation=generation,
                validation_notes=[uniform_reason],
            )
            return record, {
                "accepted": False,
                "reason": uniform_reason,
                "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
                "failure_class": FAILURE_VALIDATION_REJECTED,
                "route": "uniform_projection",
            }

        accounting_ok, accounting_reason = validate_source_accounting(
            normalized_source=normalized_source,
            accounting={"segments": accounting_segments, **(source_accounting or {})},
            unit_ids={unit.unit_id for unit in uniform_units},
        )
        if not accounting_ok:
            record = build_player_failure_record(
                failure_class=FAILURE_SOURCE_ACCOUNTING_INCOMPLETE,
                generation=generation,
                validation_notes=[accounting_reason],
            )
            return record, {
                "accepted": False,
                "reason": accounting_reason,
                "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
                "failure_class": FAILURE_SOURCE_ACCOUNTING_INCOMPLETE,
                "route": "uniform_projection",
            }

        generation = dict(generation)
        generation["source_accounting"] = _build_source_accounting_payload(
            normalized_source=normalized_source,
            segments=accounting_segments,
        )
        record = PerceptualVisibilityRecord(
            schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
            record_id=f"pvr-player-{uuid.uuid4()}",
            source_kind=PLAYER_SOURCE_KIND,
            units=uniform_units,
            validation_status="valid",
            validation_profile=ValidationProfile.PLAYER_SUBMIT.value,
            validation_notes=[],
            generation=generation,
        )
        return record, {
            "accepted": True,
            "reason": "",
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": None,
            "route": "uniform_projection",
        }

    if any(unit.kind == UNIFORM_PROJECTION_KIND for unit in units):
        record = build_player_failure_record(
            failure_class=FAILURE_VALIDATION_REJECTED,
            generation=generation,
            validation_notes=["uniform_projection not permitted on semantic decomposition path"],
        )
        return record, {
            "accepted": False,
            "reason": "uniform_projection not permitted on semantic decomposition path",
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": FAILURE_VALIDATION_REJECTED,
            "route": "semantic_decomposition",
        }

    for unit in units:
        if unit.source != PLAYER_UNIT_SOURCE and unit.source == "narrator_generation":
            unit.source = PLAYER_UNIT_SOURCE

    accounting_segments = []
    source_accounting = decomposition.get("source_accounting")
    if isinstance(source_accounting, dict):
        raw_segments = source_accounting.get("segments")
        if isinstance(raw_segments, list):
            accounting_segments = [dict(item) for item in raw_segments if isinstance(item, dict)]

    accounting_ok, accounting_reason = validate_source_accounting(
        normalized_source=normalized_source,
        accounting={"segments": accounting_segments, **(source_accounting or {})},
        unit_ids={unit.unit_id for unit in units},
    )
    if not accounting_ok:
        record = build_player_failure_record(
            failure_class=FAILURE_SOURCE_ACCOUNTING_INCOMPLETE,
            generation=generation,
            validation_notes=[accounting_reason],
        )
        return record, {
            "accepted": False,
            "reason": accounting_reason,
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": FAILURE_SOURCE_ACCOUNTING_INCOMPLETE,
        }

    linkage_ok, linkage_reason = _segment_unit_linkage_ok(accounting_segments, units)
    if not linkage_ok:
        record = build_player_failure_record(
            failure_class=FAILURE_SOURCE_ACCOUNTING_INCOMPLETE,
            generation=generation,
            validation_notes=[linkage_reason],
        )
        return record, {
            "accepted": False,
            "reason": linkage_reason,
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": FAILURE_SOURCE_ACCOUNTING_INCOMPLETE,
        }

    if any(unit.kind == "presentation_only" for unit in units):
        record = build_player_failure_record(
            failure_class=FAILURE_VALIDATION_REJECTED,
            generation=generation,
            validation_notes=["presentation_only not permitted for player decomposition"],
        )
        return record, {
            "accepted": False,
            "reason": "presentation_only not permitted for player decomposition",
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": FAILURE_VALIDATION_REJECTED,
        }

    actor = str(speaker or "").strip() or "Player"
    validated_units: list[PerceptualVisibilityUnit] = []
    for unit in units:
        if unit.kind == "internal":
            scope = str(unit.recipients.get("scope", "") or "").strip().lower()
            if scope == "public":
                record = build_player_failure_record(
                    failure_class=FAILURE_VALIDATION_REJECTED,
                    generation=generation,
                    validation_notes=[f"{unit.unit_id}: internal cannot be public"],
                )
                return record, {
                    "accepted": False,
                    "reason": f"{unit.unit_id}: internal cannot be public",
                    "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
                    "failure_class": FAILURE_VALIDATION_REJECTED,
                }
        working = unit
        if unit.kind == "speech":
            if "order_index" not in unit.source_provenance:
                record = build_player_failure_record(
                    failure_class=FAILURE_VALIDATION_REJECTED,
                    generation=generation,
                    validation_notes=[f"{unit.unit_id}: speech missing order_index"],
                )
                return record, {
                    "accepted": False,
                    "reason": f"{unit.unit_id}: speech missing order_index",
                    "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
                    "failure_class": FAILURE_VALIDATION_REJECTED,
                }
            authority = speech_authority_from_player_recipients(
                unit.recipients,
                acting_character=actor,
            )
            working = PerceptualVisibilityUnit(
                unit_id=unit.unit_id,
                kind=unit.kind,
                text=unit.text,
                recipients=dict(unit.recipients),
                authority=authority,
                source_provenance=dict(unit.source_provenance),
                source=PLAYER_UNIT_SOURCE,
            )
        elif unit.source != PLAYER_UNIT_SOURCE:
            working = PerceptualVisibilityUnit(
                unit_id=unit.unit_id,
                kind=unit.kind,
                text=unit.text,
                recipients=dict(unit.recipients),
                authority=unit.authority,
                source_provenance=dict(unit.source_provenance),
                source=PLAYER_UNIT_SOURCE,
            )
        validated_units.append(working)

    if not validated_units and normalized_source:
        record = build_player_failure_record(
            failure_class=FAILURE_VALIDATION_REJECTED,
            generation=generation,
            validation_notes=["no valid player perceptual units"],
        )
        return record, {
            "accepted": False,
            "reason": "no valid player perceptual units",
            "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
            "failure_class": FAILURE_VALIDATION_REJECTED,
        }

    generation = dict(generation)
    generation["source_accounting"] = _build_source_accounting_payload(
        normalized_source=normalized_source,
        segments=accounting_segments,
    )

    record = PerceptualVisibilityRecord(
        schema_version=PERCEPTUAL_VISIBILITY_SCHEMA_VERSION,
        record_id=f"pvr-player-{uuid.uuid4()}",
        source_kind=PLAYER_SOURCE_KIND,
        units=validated_units,
        validation_status="valid",
        validation_profile=ValidationProfile.PLAYER_SUBMIT.value,
        validation_notes=[],
        generation=generation,
    )
    return record, {
        "accepted": True,
        "reason": "",
        "validation_profile": ValidationProfile.PLAYER_SUBMIT.value,
        "failure_class": None,
    }


def attach_player_perceptual_metadata(
    metadata: dict[str, Any],
    *,
    record: PerceptualVisibilityRecord,
    validation_audit: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(metadata or {})
    merged[METADATA_KEY] = record.to_dict()
    merged[VALIDATION_AUDIT_KEY] = dict(validation_audit)
    return merged

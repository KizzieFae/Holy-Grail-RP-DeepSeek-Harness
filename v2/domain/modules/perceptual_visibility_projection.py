"""Deterministic viewer-specific perceptual visibility projection (#90)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from perceptual_visibility_authority import speech_authority_allows_viewer
from perceptual_visibility_contract import (
    CHARACTER_SOURCE_KIND,
    PLAYER_PERCEPT_UNAVAILABLE_MARKER,
    PLAYER_SOURCE_KIND,
    PerceptualVisibilityRecord,
)
from perceptual_visibility_legacy import perceptual_visibility_record_from_entry_metadata
from perceptual_visibility_validation import (
    ValidationProfile,
    build_degraded_perceptual_record_from_structured_move,
    validate_perceptual_visibility_record,
)
from perception_audibility_visibility import (
    character_in_recipient_scope,
    resolve_recipient_scope,
)

PERCEPTUAL_PROJECTOR_ID = "hg.perceptual_visibility.v1"
PERCEPTUAL_PROJECTOR_VERSION = 1


@dataclass
class PerceptualVisibilityAssemblyResult:
    content: str | None
    included_unit_ids: list[str] = field(default_factory=list)
    excluded_unit_ids: list[str] = field(default_factory=list)
    exclusion_reasons: dict[str, str] = field(default_factory=dict)
    authority_narrowed_unit_ids: list[str] = field(default_factory=list)
    degraded_path: str | None = None
    source_entry_id: str | None = None
    viewer_character: str | None = None
    record_validation_status: str | None = None
    source_kind: str | None = None
    validation_profile: str | None = None
    historical_normalization: bool = False
    legacy_metadata_key: str | None = None
    projector_id: str = PERCEPTUAL_PROJECTOR_ID
    projector_version: int = PERCEPTUAL_PROJECTOR_VERSION


def _unit_eligible_for_viewer(
    unit: Any,
    *,
    viewer_character: str,
    present_characters: list[str],
) -> bool:
    scope = resolve_recipient_scope(unit.recipients)
    return character_in_recipient_scope(
        viewer_character,
        scope,
        present_characters=present_characters,
        recipients=unit.recipients,
    )


def _sorted_units_for_record(record: PerceptualVisibilityRecord) -> list[Any]:
    if record.source_kind != PLAYER_SOURCE_KIND:
        return list(record.units)
    return sorted(
        record.units,
        key=lambda unit: int(unit.source_provenance.get("order_index", 0)),
    )


def _player_internal_ineligible(unit: Any, *, record: PerceptualVisibilityRecord) -> bool:
    return record.source_kind == PLAYER_SOURCE_KIND and unit.kind == "internal"


def _character_actor_entitled_to_unit(
    unit: Any,
    *,
    record: PerceptualVisibilityRecord,
    viewer_character: str,
    acting_character: str | None,
) -> bool:
    if record.source_kind != CHARACTER_SOURCE_KIND:
        return False
    actor = str(acting_character or "").strip()
    viewer = str(viewer_character or "").strip()
    if not actor or viewer != actor:
        return False
    return unit.kind in ("observable_event", "speech")


def assemble_perceptual_visibility_for_viewer(
    record: PerceptualVisibilityRecord,
    *,
    viewer_character: str,
    present_characters: list[str],
    source_entry_id: str | None = None,
    historical_normalization: bool = False,
    legacy_metadata_key: str | None = None,
    acting_character: str | None = None,
) -> PerceptualVisibilityAssemblyResult:
    included: list[str] = []
    excluded: list[str] = []
    reasons: dict[str, str] = {}
    narrowed: list[str] = []
    fragments: list[str] = []

    degraded_path: str | None = None
    if record.validation_status == "invalid_fallback_structured":
        degraded_path = "invalid_fallback_structured"
    elif (
        record.validation_status == "invalid_excluded"
        and isinstance(record.recovery, dict)
        and record.recovery.get("failure_class")
    ):
        degraded_path = "decomposition_failed"
        return PerceptualVisibilityAssemblyResult(
            content=PLAYER_PERCEPT_UNAVAILABLE_MARKER,
            excluded_unit_ids=[],
            exclusion_reasons={},
            authority_narrowed_unit_ids=[],
            degraded_path=degraded_path,
            source_entry_id=source_entry_id,
            viewer_character=viewer_character,
            record_validation_status=record.validation_status,
            source_kind=record.source_kind,
            validation_profile=record.validation_profile,
            historical_normalization=historical_normalization,
            legacy_metadata_key=legacy_metadata_key,
        )

    for unit in _sorted_units_for_record(record):
        if _player_internal_ineligible(unit, record=record):
            excluded.append(unit.unit_id)
            reasons[unit.unit_id] = "player_internal_ineligible"
            continue
        if _character_actor_entitled_to_unit(
            unit,
            record=record,
            viewer_character=viewer_character,
            acting_character=acting_character,
        ):
            included.append(unit.unit_id)
            fragments.append(unit.text.strip())
            continue
        if not _unit_eligible_for_viewer(
            unit,
            viewer_character=viewer_character,
            present_characters=present_characters,
        ):
            excluded.append(unit.unit_id)
            reasons[unit.unit_id] = "recipient_ineligible"
            continue

        if unit.kind == "speech":
            if not speech_authority_allows_viewer(
                unit.authority,
                viewer_character=viewer_character,
            ):
                excluded.append(unit.unit_id)
                reasons[unit.unit_id] = "authority_narrowed"
                narrowed.append(unit.unit_id)
                continue

        included.append(unit.unit_id)
        fragments.append(unit.text.strip())

    content = " ".join(fragment for fragment in fragments if fragment).strip() or None
    if content is None and included:
        content = None
    if content is None and not included and record.validation_status == "valid":
        degraded_path = "all_units_excluded"
    return PerceptualVisibilityAssemblyResult(
        content=content,
        included_unit_ids=included,
        excluded_unit_ids=excluded,
        exclusion_reasons=reasons,
        authority_narrowed_unit_ids=narrowed,
        degraded_path=degraded_path,
        source_entry_id=source_entry_id,
        viewer_character=viewer_character,
        record_validation_status=record.validation_status,
        source_kind=record.source_kind,
        validation_profile=record.validation_profile,
        historical_normalization=historical_normalization,
        legacy_metadata_key=legacy_metadata_key,
    )


def assemble_perceptual_history_entry_for_viewer(
    entry: dict[str, Any],
    *,
    viewer_character: str,
    present_characters: list[str],
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
    source_kind: str = "unknown",
) -> PerceptualVisibilityAssemblyResult:
    entry_id = str(entry.get("entry_id", "") or "")
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}

    record, load_provenance = perceptual_visibility_record_from_entry_metadata(
        metadata,
        structured_move=structured_move,
        acting_character=acting_character,
    )

    if (
        record is None
        and source_kind == "narrator"
        and structured_move is not None
        and acting_character
    ):
        record = build_degraded_perceptual_record_from_structured_move(
            structured_move,
            acting_character=acting_character,
            source_kind=source_kind,
            generation={"recovery_trigger": "missing_or_invalid_perceptual_record"},
        )
        load_provenance = {
            "historical_normalization": False,
            "legacy_metadata_key": None,
            "degraded_recovery": True,
        }

    if record is None:
        if source_kind == "character":
            move = structured_move
            if move is None and isinstance(metadata, dict):
                move = metadata.get("structured_move")
            actor = str(entry.get("actor_id") or acting_character or "").strip()
            if isinstance(move, dict) and actor:
                from character_perceptual_service import (
                    build_historical_partial_character_record,
                )

                record = build_historical_partial_character_record(
                    move,
                    acting_character=actor,
                )
                if record is not None:
                    load_provenance = {
                        "historical_normalization": True,
                        "legacy_metadata_key": None,
                        "historical_partial": True,
                    }
        if record is None and source_kind == PLAYER_SOURCE_KIND:
            return PerceptualVisibilityAssemblyResult(
                content=None,
                degraded_path="historical_missing_player_decomposition",
                source_entry_id=entry_id,
                viewer_character=viewer_character,
                record_validation_status=None,
                source_kind=source_kind,
            )
        if record is None:
            return PerceptualVisibilityAssemblyResult(
                content=None,
                degraded_path="invalid_excluded",
                source_entry_id=entry_id,
                viewer_character=viewer_character,
                record_validation_status="invalid_excluded",
                source_kind=source_kind,
            )

    result = assemble_perceptual_visibility_for_viewer(
        record,
        viewer_character=viewer_character,
        present_characters=present_characters,
        source_entry_id=entry_id,
        historical_normalization=bool(load_provenance.get("historical_normalization")),
        legacy_metadata_key=load_provenance.get("legacy_metadata_key"),
        acting_character=acting_character or str(entry.get("actor_id") or "").strip() or None,
    )
    if load_provenance.get("degraded_recovery"):
        result.degraded_path = "invalid_fallback_structured"
    return result


def build_perceptual_visibility_audit_metadata(
    result: PerceptualVisibilityAssemblyResult,
    *,
    record: PerceptualVisibilityRecord | None = None,
) -> dict[str, Any]:
    audit: dict[str, Any] = {
        "projector_id": result.projector_id,
        "projector_version": result.projector_version,
        "viewer_character": result.viewer_character,
        "source_entry_id": result.source_entry_id,
        "source_kind": result.source_kind,
        "validation_status": result.record_validation_status,
        "validation_profile": result.validation_profile,
        "degraded_path": result.degraded_path,
        "historical_normalization": result.historical_normalization,
        "legacy_metadata_key": result.legacy_metadata_key,
        "included_unit_ids": list(result.included_unit_ids),
        "excluded_unit_ids": list(result.excluded_unit_ids),
        "exclusion_reasons": dict(result.exclusion_reasons),
        "authority_narrowed_unit_ids": list(result.authority_narrowed_unit_ids),
    }
    if record is not None:
        audit["record_id"] = record.record_id
        audit["schema_version"] = record.schema_version
        audit["unit_ids"] = [unit.unit_id for unit in record.units]
        if record.recovery:
            audit["recovery"] = dict(record.recovery)
    return {"perceptual_visibility_projection": audit}

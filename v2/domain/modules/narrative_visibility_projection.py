"""Viewer-specific rich narrative assembly from NarrativeVisibilityRecord (#81)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from character_move_adapters import is_canonical_v2_move, iter_speech_beats
from narrative_visibility_contract import (
    NarrativeVisibilityRecord,
    narrative_visibility_from_metadata,
)
from narrative_visibility_validation import viewer_may_receive_speech_unit
from perception_audibility_visibility import (
    character_in_recipient_scope,
    resolve_recipient_scope,
)


@dataclass
class NarrativeVisibilityAssemblyResult:
    content: str | None
    included_unit_ids: list[str] = field(default_factory=list)
    excluded_unit_ids: list[str] = field(default_factory=list)
    exclusion_reasons: dict[str, str] = field(default_factory=dict)
    structured_authority_narrowed: list[str] = field(default_factory=list)
    fallback_path: str | None = None
    source_entry_id: str | None = None
    viewer_character: str | None = None


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


def assemble_narrative_visibility_for_viewer(
    record: NarrativeVisibilityRecord,
    *,
    viewer_character: str,
    present_characters: list[str],
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
    source_entry_id: str | None = None,
) -> NarrativeVisibilityAssemblyResult:
    included: list[str] = []
    excluded: list[str] = []
    reasons: dict[str, str] = {}
    narrowed: list[str] = []
    fragments: list[str] = []

    speech_beats_by_index: dict[int, dict[str, Any]] = {}
    if isinstance(structured_move, dict) and is_canonical_v2_move(structured_move):
        for beat_index, beat in iter_speech_beats(structured_move):
            speech_beats_by_index[beat_index] = beat

    actor = str(acting_character or "").strip()

    for unit in record.units:
        if not _unit_eligible_for_viewer(
            unit,
            viewer_character=viewer_character,
            present_characters=present_characters,
        ):
            excluded.append(unit.unit_id)
            reasons[unit.unit_id] = "nvr_recipient_ineligible"
            continue

        if unit.kind == "speech":
            beat_index = unit.beat_index
            if beat_index is None or beat_index not in speech_beats_by_index:
                excluded.append(unit.unit_id)
                reasons[unit.unit_id] = "speech_missing_structured_beat"
                continue
            beat = speech_beats_by_index[beat_index]
            if not actor:
                excluded.append(unit.unit_id)
                reasons[unit.unit_id] = "speech_missing_actor"
                continue
            if not viewer_may_receive_speech_unit(
                beat=beat,
                acting_character=actor,
                viewer_character=viewer_character,
            ):
                excluded.append(unit.unit_id)
                reasons[unit.unit_id] = "structured_authority_narrowed"
                narrowed.append(unit.unit_id)
                continue

        included.append(unit.unit_id)
        fragments.append(unit.text.strip())

    content = " ".join(fragment for fragment in fragments if fragment).strip() or None
    return NarrativeVisibilityAssemblyResult(
        content=content,
        included_unit_ids=included,
        excluded_unit_ids=excluded,
        exclusion_reasons=reasons,
        structured_authority_narrowed=narrowed,
        source_entry_id=source_entry_id,
        viewer_character=viewer_character,
    )


def assemble_history_entry_for_viewer(
    entry: dict[str, Any],
    *,
    viewer_character: str,
    present_characters: list[str],
    structured_move: dict[str, Any] | None = None,
    acting_character: str | None = None,
    committed_observable_fallback_fn: Any | None = None,
) -> NarrativeVisibilityAssemblyResult:
    """Assemble viewer-specific prose for opening/presentation entries."""
    entry_id = str(entry.get("entry_id", "") or "")
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    record = narrative_visibility_from_metadata(metadata)

    if record is not None:
        result = assemble_narrative_visibility_for_viewer(
            record,
            viewer_character=viewer_character,
            present_characters=present_characters,
            structured_move=structured_move,
            acting_character=acting_character,
            source_entry_id=entry_id,
        )
        return result

    if committed_observable_fallback_fn is not None and structured_move is not None:
        fallback_content = committed_observable_fallback_fn()
        if fallback_content and str(fallback_content).strip():
            return NarrativeVisibilityAssemblyResult(
                content=str(fallback_content).strip(),
                fallback_path="structured_observable",
                source_entry_id=entry_id,
                viewer_character=viewer_character,
            )

    return NarrativeVisibilityAssemblyResult(
        content=None,
        fallback_path="excluded_missing_nvr",
        source_entry_id=entry_id,
        viewer_character=viewer_character,
    )


def build_narrative_visibility_audit_metadata(
    result: NarrativeVisibilityAssemblyResult,
) -> dict[str, Any]:
    return {
        "narrative_visibility_projection": {
            "viewer_character": result.viewer_character,
            "source_entry_id": result.source_entry_id,
            "included_unit_ids": list(result.included_unit_ids),
            "excluded_unit_ids": list(result.excluded_unit_ids),
            "exclusion_reasons": dict(result.exclusion_reasons),
            "structured_authority_narrowed": list(result.structured_authority_narrowed),
            "fallback_path": result.fallback_path,
        }
    }

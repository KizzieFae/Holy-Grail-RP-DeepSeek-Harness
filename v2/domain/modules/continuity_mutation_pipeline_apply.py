"""Apply resolved mutations to SceneState and ContinuityManager (#170)."""

from __future__ import annotations

from typing import Any

from continuity_state import SceneState

from continuity_mutation_pipeline_normalize import (
    _normalize_excursion_id,
    _normalize_participant_ids,
    _normalize_spatial_location,
)
from continuity_mutation_pipeline_types import (
    CanonicalAtom,
    ContinuityMutationError,
    ContinuityMutationType,
    MutationRequest,
    MutationResolutionKey,
)


def _sorted_resolution_items(
    resolved: dict[MutationResolutionKey, MutationRequest],
) -> list[tuple[MutationResolutionKey, MutationRequest]]:
    items = list(resolved.items())

    def sort_key(
        item: tuple[MutationResolutionKey, MutationRequest],
    ) -> tuple[int, str]:
        k, _req = item
        if k.atom == CanonicalAtom.LOCATION:
            return (0, "")
        return (1, k.excursion_scope)

    items.sort(key=sort_key)
    return items


def apply_resolved_mutations(
    resolved: dict[MutationResolutionKey, MutationRequest],
    *,
    scene_state: SceneState | None,
    continuity_manager: Any | None = None,
    commit_turn_index: int | None = None,
    commit_timestamp: Any | None = None,
) -> None:
    """Apply winning mutations (location on ``scene_state``; excursions on manager)."""
    if not resolved:
        return
    needs_excursion = any(
        k.atom == CanonicalAtom.EXCURSION_LIFECYCLE for k in resolved
    )
    if needs_excursion:
        if continuity_manager is None:
            raise ContinuityMutationError(
                "continuity_manager is required to apply excursion lifecycle mutations"
            )
        if commit_turn_index is None:
            raise ContinuityMutationError(
                "commit_turn_index is required to apply excursion lifecycle mutations"
            )

    for key, req in _sorted_resolution_items(resolved):
        if key.atom == CanonicalAtom.LOCATION:
            if scene_state is None:
                continue
            if req.mutation_type != ContinuityMutationType.SPATIAL_TRANSITION:
                raise ContinuityMutationError("LOCATION atom requires SPATIAL_TRANSITION")
            loc = _normalize_spatial_location(req.payload.get("location"))
            scene_state.location = loc
        elif key.atom == CanonicalAtom.EXCURSION_LIFECYCLE:
            assert continuity_manager is not None
            assert commit_turn_index is not None
            turn_i = int(commit_turn_index)
            if req.mutation_type == ContinuityMutationType.EXCURSION_OPEN:
                parts = _normalize_participant_ids(
                    req.payload.get("participant_character_ids"),
                    field_label="participant_character_ids",
                )
                explicit = _normalize_excursion_id(
                    req.payload.get("excursion_id"), required=False
                )
                continuity_manager.open_excursion(
                    participant_character_ids=list(parts),
                    excursion_id=explicit if explicit else None,
                    opened_at_turn=turn_i,
                )
            elif req.mutation_type == ContinuityMutationType.EXCURSION_UPDATE:
                eid = _normalize_excursion_id(req.payload.get("excursion_id"), required=True)
                parts = _normalize_participant_ids(
                    req.payload.get("participant_character_ids"),
                    field_label="participant_character_ids",
                )
                continuity_manager.update_excursion(
                    eid,
                    participant_character_ids=list(parts),
                )
            elif req.mutation_type == ContinuityMutationType.EXCURSION_CLOSE:
                from continuity_reintegration import (
                    apply_excursion_close_reintegration_mutation,
                )
                from datetime import datetime, timezone

                ts = commit_timestamp
                if ts is None:
                    ts = datetime.now(timezone.utc)
                apply_excursion_close_reintegration_mutation(
                    continuity_manager,
                    _normalize_excursion_id(req.payload.get("excursion_id"), required=True),
                    req.payload,
                    commit_turn_index=turn_i,
                    timestamp=ts,
                )
            else:
                raise ContinuityMutationError(
                    f"unsupported excursion mutation {req.mutation_type!r}"
                )

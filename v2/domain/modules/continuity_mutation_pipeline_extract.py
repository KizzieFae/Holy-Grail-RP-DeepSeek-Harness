"""D/S/M mutation candidate extraction (#170)."""

from __future__ import annotations

from typing import Any, Optional

from continuity_reintegration import extract_and_validate_reintegration_block

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
    MutationSourceClass,
)


def extract_m_spatial_candidates(move: dict[str, Any]) -> list[MutationRequest]:
    """Extract M-class spatial transition candidates from structured move."""
    raw = move.get("spatial_transition")
    if raw is None:
        return []
    if not isinstance(raw, dict):
        raise ContinuityMutationError("spatial_transition must be an object when present")
    if "location" not in raw:
        raise ContinuityMutationError("spatial_transition requires location when present")
    loc = _normalize_spatial_location(raw.get("location"))
    return [
        MutationRequest(
            mutation_type=ContinuityMutationType.SPATIAL_TRANSITION,
            atom=CanonicalAtom.LOCATION,
            source=MutationSourceClass.M,
            payload={"location": loc},
        )
    ]


def _parse_excursion_lifecycle_move(move: dict[str, Any]) -> MutationRequest:
    raw = move.get("excursion_lifecycle")
    if raw is None:
        raise ContinuityMutationError("internal: excursion_lifecycle missing")
    if not isinstance(raw, dict):
        raise ContinuityMutationError("excursion_lifecycle must be an object when present")
    op = raw.get("operation")
    if not isinstance(op, str):
        raise ContinuityMutationError("excursion_lifecycle.operation must be a string")
    op_norm = op.strip().lower()
    if "reintegration" in raw and op_norm not in ("close",):
        raise ContinuityMutationError(
            "excursion_lifecycle.reintegration is only allowed with operation close"
        )
    if op_norm == "open":
        eid = _normalize_excursion_id(raw.get("excursion_id"), required=False)
        parts = _normalize_participant_ids(
            raw.get("participant_character_ids"),
            field_label="participant_character_ids",
        )
        payload: dict[str, Any] = {
            "operation": "open",
            "participant_character_ids": list(parts),
        }
        if eid:
            payload["excursion_id"] = eid
        return MutationRequest(
            mutation_type=ContinuityMutationType.EXCURSION_OPEN,
            atom=CanonicalAtom.EXCURSION_LIFECYCLE,
            source=MutationSourceClass.M,
            payload=payload,
        )
    if op_norm == "update":
        eid = _normalize_excursion_id(raw.get("excursion_id"), required=True)
        parts = _normalize_participant_ids(
            raw.get("participant_character_ids"),
            field_label="participant_character_ids",
        )
        return MutationRequest(
            mutation_type=ContinuityMutationType.EXCURSION_UPDATE,
            atom=CanonicalAtom.EXCURSION_LIFECYCLE,
            source=MutationSourceClass.M,
            payload={
                "operation": "update",
                "excursion_id": eid,
                "participant_character_ids": list(parts),
            },
        )
    if op_norm == "close":
        eid = _normalize_excursion_id(raw.get("excursion_id"), required=True)
        payload_close: dict[str, Any] = {"operation": "close", "excursion_id": eid}
        reint = extract_and_validate_reintegration_block(raw, operation=op_norm)
        if reint is not None:
            payload_close["reintegration"] = reint
        return MutationRequest(
            mutation_type=ContinuityMutationType.EXCURSION_CLOSE,
            atom=CanonicalAtom.EXCURSION_LIFECYCLE,
            source=MutationSourceClass.M,
            payload=payload_close,
        )
    raise ContinuityMutationError(
        "excursion_lifecycle.operation must be one of: open, update, close"
    )


def extract_m_excursion_candidates(move: dict[str, Any]) -> list[MutationRequest]:
    raw = move.get("excursion_lifecycle")
    if raw is None:
        return []
    return [_parse_excursion_lifecycle_move(move)]


def extract_d_spatial_candidates(
    _director_decision: dict[str, Any],
    _scene_state: Any,
) -> list[MutationRequest]:
    """Deterministic spatial candidates (Slice A: none; hook for future D-class rules)."""
    return []


def extract_d_excursion_candidates(
    _director_decision: dict[str, Any],
    _scene_state: Any,
) -> list[MutationRequest]:
    """Deterministic excursion candidates (Slice B: none)."""
    return []


def extract_s_candidates(
    session_mutation_candidates: Optional[list[MutationRequest]],
) -> list[MutationRequest]:
    """S-class: explicit session/harness proposals (pre-parsed)."""
    if not session_mutation_candidates:
        return []
    out: list[MutationRequest] = []
    for item in session_mutation_candidates:
        if not isinstance(item, MutationRequest):
            raise ContinuityMutationError(
                "session_mutation_candidates must contain only MutationRequest instances"
            )
        out.append(item)
    return out

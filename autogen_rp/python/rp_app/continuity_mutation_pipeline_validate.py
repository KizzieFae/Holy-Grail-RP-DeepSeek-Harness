"""Move-shape and global resolved-mutation validation (#170)."""

from __future__ import annotations

from typing import Any

from continuity_reintegration import (
    extract_and_validate_reintegration_block,
    validate_close_reintegration_globally,
)
from continuity_state import ExcursionStatus

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


def validate_spatial_transition_move_shape(move: dict[str, Any] | None) -> tuple[bool, str]:
    """Structural check for character validation (non-throwing)."""
    if not move or not isinstance(move, dict):
        return True, ""
    raw = move.get("spatial_transition")
    if raw is None:
        return True, ""
    if not isinstance(raw, dict):
        return False, "[SPATIAL_TRANSITION] spatial_transition must be an object"
    if "location" not in raw:
        return False, "[SPATIAL_TRANSITION] spatial_transition requires location"
    try:
        _normalize_spatial_location(raw.get("location"))
    except ContinuityMutationError as exc:
        return False, f"[SPATIAL_TRANSITION] {exc}"
    return True, ""


def validate_excursion_lifecycle_move_shape(move: dict[str, Any] | None) -> tuple[bool, str]:
    """Structural check for character validation (non-throwing)."""
    if not move or not isinstance(move, dict):
        return True, ""
    raw = move.get("excursion_lifecycle")
    if raw is None:
        return True, ""
    if not isinstance(raw, dict):
        return False, "[EXCURSION_LIFECYCLE] excursion_lifecycle must be an object"
    op = raw.get("operation")
    if not isinstance(op, str):
        return False, "[EXCURSION_LIFECYCLE] operation must be a string"
    op_norm = op.strip().lower()
    if op_norm not in ("open", "update", "close"):
        return (
            False,
            "[EXCURSION_LIFECYCLE] operation must be one of: open, update, close",
        )
    try:
        if op_norm == "open":
            _normalize_excursion_id(raw.get("excursion_id"), required=False)
            _normalize_participant_ids(
                raw.get("participant_character_ids"),
                field_label="participant_character_ids",
            )
        elif op_norm == "update":
            _normalize_excursion_id(raw.get("excursion_id"), required=True)
            _normalize_participant_ids(
                raw.get("participant_character_ids"),
                field_label="participant_character_ids",
            )
        else:
            _normalize_excursion_id(raw.get("excursion_id"), required=True)
    except ContinuityMutationError as exc:
        return False, f"[EXCURSION_LIFECYCLE] {exc}"
    return True, ""


def _validate_excursion_payload_consistency(req: MutationRequest) -> None:
    if req.atom != CanonicalAtom.EXCURSION_LIFECYCLE:
        return
    mt = req.mutation_type
    if mt == ContinuityMutationType.EXCURSION_OPEN:
        _normalize_participant_ids(
            req.payload.get("participant_character_ids"),
            field_label="participant_character_ids",
        )
        _normalize_excursion_id(req.payload.get("excursion_id"), required=False)
    elif mt == ContinuityMutationType.EXCURSION_UPDATE:
        _normalize_excursion_id(req.payload.get("excursion_id"), required=True)
        _normalize_participant_ids(
            req.payload.get("participant_character_ids"),
            field_label="participant_character_ids",
        )
    elif mt == ContinuityMutationType.EXCURSION_CLOSE:
        _normalize_excursion_id(req.payload.get("excursion_id"), required=True)
        r = req.payload.get("reintegration")
        if r is not None:
            if not isinstance(r, dict):
                raise ContinuityMutationError("reintegration must be an object")
            extract_and_validate_reintegration_block(
                {**req.payload, "reintegration": r},
                operation="close",
            )


def validate_resolved_mutations_globally(
    resolved: dict[MutationResolutionKey, MutationRequest],
    scene_state: Any,
    acting_character: str,
    *,
    continuity_manager: Any | None = None,
) -> None:
    """Cross-atom / scene invariants after precedence."""
    del acting_character  # reserved for future focal checks
    for _key, req in resolved.items():
        if req.mutation_type == ContinuityMutationType.SPATIAL_TRANSITION:
            if req.atom != CanonicalAtom.LOCATION:
                raise ContinuityMutationError(
                    "LOCATION resolution must use SPATIAL_TRANSITION"
                )
            _normalize_spatial_location(req.payload.get("location"))
        elif req.mutation_type in (
            ContinuityMutationType.EXCURSION_OPEN,
            ContinuityMutationType.EXCURSION_UPDATE,
            ContinuityMutationType.EXCURSION_CLOSE,
        ):
            _validate_excursion_payload_consistency(req)
        else:
            raise ContinuityMutationError(f"unsupported mutation_type {req.mutation_type!r}")

    excursion_keys = [
        k for k in resolved if k.atom == CanonicalAtom.EXCURSION_LIFECYCLE
    ]
    if not excursion_keys:
        return
    if continuity_manager is None:
        raise ContinuityMutationError(
            "continuity_manager is required to validate excursion lifecycle mutations"
        )

    anchor_raw = getattr(continuity_manager, "anchor_character_id", None)
    anchor_id = str(anchor_raw).strip() if anchor_raw else ""

    def active_union_excluding_excursion(skip_excursion_id: str | None) -> set[str]:
        out: set[str] = set()
        ex_store = getattr(continuity_manager, "excursions", {}) or {}
        for eid, rec in ex_store.items():
            if skip_excursion_id is not None and str(eid) == skip_excursion_id:
                continue
            st = getattr(rec, "status", None)
            if st != ExcursionStatus.ACTIVE:
                continue
            for pid in getattr(rec, "participant_character_ids", []) or []:
                n = str(pid).strip()
                if n:
                    out.add(n)
        return out

    for ek in excursion_keys:
        req = resolved[ek]
        if req.mutation_type == ContinuityMutationType.EXCURSION_OPEN:
            parts = _normalize_participant_ids(
                req.payload.get("participant_character_ids"),
                field_label="participant_character_ids",
            )
            if anchor_id and anchor_id in parts:
                raise ContinuityMutationError(
                    "anchor character cannot be an excursion participant "
                    "(focal/excursion boundary)"
                )
            occupied = active_union_excluding_excursion(skip_excursion_id=None)
            overlap = sorted(p for p in parts if p in occupied)
            if overlap:
                raise ContinuityMutationError(
                    "excursion open conflicts with existing active excursion membership: "
                    + ", ".join(overlap)
                )
            explicit_id = _normalize_excursion_id(
                req.payload.get("excursion_id"), required=False
            )
            if explicit_id:
                ex_store = getattr(continuity_manager, "excursions", {}) or {}
                if explicit_id in ex_store:
                    raise ContinuityMutationError(
                        f"excursion_id already exists: {explicit_id!r}"
                    )

        elif req.mutation_type == ContinuityMutationType.EXCURSION_UPDATE:
            eid = _normalize_excursion_id(req.payload.get("excursion_id"), required=True)
            ex_store = getattr(continuity_manager, "excursions", {}) or {}
            rec = ex_store.get(eid)
            if rec is None:
                raise ContinuityMutationError(f"unknown excursion_id: {eid!r}")
            if getattr(rec, "status", None) != ExcursionStatus.ACTIVE:
                raise ContinuityMutationError("cannot update a closed excursion")
            old_set = frozenset(
                str(x).strip()
                for x in (getattr(rec, "participant_character_ids", []) or [])
                if str(x or "").strip()
            )
            parts = _normalize_participant_ids(
                req.payload.get("participant_character_ids"),
                field_label="participant_character_ids",
            )
            if anchor_id and anchor_id in parts:
                raise ContinuityMutationError(
                    "anchor character cannot be an excursion participant "
                    "(focal/excursion boundary)"
                )
            occupied = active_union_excluding_excursion(skip_excursion_id=eid)
            for p in parts:
                if p in occupied and p not in old_set:
                    raise ContinuityMutationError(
                        f"participant {p!r} is already on another active excursion"
                    )

        elif req.mutation_type == ContinuityMutationType.EXCURSION_CLOSE:
            eid = _normalize_excursion_id(req.payload.get("excursion_id"), required=True)
            ex_store = getattr(continuity_manager, "excursions", {}) or {}
            if eid not in ex_store:
                raise ContinuityMutationError(f"unknown excursion_id: {eid!r}")
            validate_close_reintegration_globally(
                excursion_id=eid,
                reintegration=req.payload.get("reintegration"),
                continuity_manager=continuity_manager,
            )

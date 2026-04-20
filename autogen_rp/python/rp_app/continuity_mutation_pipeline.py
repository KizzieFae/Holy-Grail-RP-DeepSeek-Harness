"""Continuity mutation pipeline (Issue #81 — spatial + excursion lifecycle).

Typed mutation requests, composer with D → S → M precedence per canonical atom,
global validation, and atomic application to ``SceneState`` / excursion store
inside ``process_turn``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from continuity_reintegration import (
    extract_and_validate_reintegration_block,
    validate_close_reintegration_globally,
)
from continuity_state import ExcursionStatus, SceneState


class ContinuityMutationError(ValueError):
    """Invalid mutation proposal or resolution; continuity commit must abort."""


class CanonicalAtom(str, Enum):
    """v1 canonical atoms; extend with new enum members only when adding slices."""

    LOCATION = "location"
    EXCURSION_LIFECYCLE = "excursion_lifecycle"


class MutationSourceClass(str, Enum):
    """Proposal source class for precedence (D wins over S wins over M)."""

    D = "D"
    S = "S"
    M = "M"


class ContinuityMutationType(str, Enum):
    """Closed mutation family set."""

    SPATIAL_TRANSITION = "SPATIAL_TRANSITION"
    EXCURSION_OPEN = "EXCURSION_OPEN"
    EXCURSION_UPDATE = "EXCURSION_UPDATE"
    EXCURSION_CLOSE = "EXCURSION_CLOSE"


_SOURCE_RANK = {
    MutationSourceClass.D: 3,
    MutationSourceClass.S: 2,
    MutationSourceClass.M: 1,
}

MAX_SPATIAL_LOCATION_LEN = 500
MAX_EXCURSION_ID_LEN = 200
MAX_EXCURSION_PARTICIPANTS = 64
_PENDING_OPEN_SCOPE = "__pending_open__"


@dataclass(frozen=True)
class MutationResolutionKey:
    """One canonical mutation slot per commit (one D/S/M winner per key)."""

    atom: CanonicalAtom
    """For ``EXCURSION_LIFECYCLE``, non-empty scope (excursion_id or pending-open sentinel)."""

    excursion_scope: str = ""

    @staticmethod
    def for_location() -> MutationResolutionKey:
        return MutationResolutionKey(CanonicalAtom.LOCATION, "")

    @staticmethod
    def for_excursion_scope(scope: str) -> MutationResolutionKey:
        sk = str(scope or "").strip()
        if not sk:
            raise ContinuityMutationError("excursion resolution scope must be non-empty")
        if len(sk) > MAX_EXCURSION_ID_LEN:
            raise ContinuityMutationError("excursion id exceeds maximum length")
        return MutationResolutionKey(CanonicalAtom.EXCURSION_LIFECYCLE, sk)

    def audit_slug(self) -> str:
        if self.atom == CanonicalAtom.LOCATION:
            return CanonicalAtom.LOCATION.value
        return f"{CanonicalAtom.EXCURSION_LIFECYCLE.value}:{self.excursion_scope}"


@dataclass(frozen=True)
class MutationRequest:
    mutation_type: ContinuityMutationType
    atom: CanonicalAtom
    source: MutationSourceClass
    payload: dict[str, Any]


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


def mutation_resolution_key(req: MutationRequest) -> MutationResolutionKey:
    if req.mutation_type == ContinuityMutationType.SPATIAL_TRANSITION:
        if req.atom != CanonicalAtom.LOCATION:
            raise ContinuityMutationError("SPATIAL_TRANSITION must use LOCATION atom")
        return MutationResolutionKey.for_location()
    if req.atom != CanonicalAtom.EXCURSION_LIFECYCLE:
        raise ContinuityMutationError("excursion mutations must use EXCURSION_LIFECYCLE atom")
    if req.mutation_type == ContinuityMutationType.EXCURSION_OPEN:
        eid = _normalize_excursion_id(req.payload.get("excursion_id"), required=False)
        scope = eid if eid else _PENDING_OPEN_SCOPE
        return MutationResolutionKey.for_excursion_scope(scope)
    if req.mutation_type in (
        ContinuityMutationType.EXCURSION_UPDATE,
        ContinuityMutationType.EXCURSION_CLOSE,
    ):
        eid = _normalize_excursion_id(req.payload.get("excursion_id"), required=True)
        return MutationResolutionKey.for_excursion_scope(eid)
    raise ContinuityMutationError(f"unknown mutation_type {req.mutation_type!r}")


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


def compose_resolved_mutations(
    *,
    move: dict[str, Any],
    director_decision: dict[str, Any],
    scene_state: Any,
    session_mutation_candidates: Optional[list[MutationRequest]] = None,
) -> dict[MutationResolutionKey, MutationRequest]:
    """Collect, group by canonical key, apply D → S → M precedence; one winner per key."""
    candidates: list[MutationRequest] = []
    candidates.extend(
        extract_d_spatial_candidates(director_decision, scene_state)
    )
    candidates.extend(
        extract_d_excursion_candidates(director_decision, scene_state)
    )
    candidates.extend(extract_s_candidates(session_mutation_candidates))
    candidates.extend(extract_m_spatial_candidates(move))
    candidates.extend(extract_m_excursion_candidates(move))

    by_key: dict[MutationResolutionKey, list[MutationRequest]] = {}
    for req in candidates:
        key = mutation_resolution_key(req)
        by_key.setdefault(key, []).append(req)

    resolved: dict[MutationResolutionKey, MutationRequest] = {}
    for res_key, group in by_key.items():
        by_source: dict[MutationSourceClass, list[MutationRequest]] = {}
        for m in group:
            by_source.setdefault(m.source, []).append(m)
        for src, items in by_source.items():
            if len(items) > 1:
                raise ContinuityMutationError(
                    f"multiple mutations for {res_key.audit_slug()} from source {src.value} in one commit"
                )

        winner: MutationRequest | None = None
        best_rank = -1
        for m in group:
            rank = _SOURCE_RANK[m.source]
            if rank > best_rank:
                best_rank = rank
                winner = m
        assert winner is not None
        resolved[res_key] = winner

    return resolved


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


def resolved_mutations_audit_payload(
    resolved: dict[MutationResolutionKey, MutationRequest],
) -> dict[str, Any]:
    """Structured snapshot for ``turn_metadata`` / audits."""
    out: dict[str, Any] = {}
    for key, req in resolved.items():
        out[key.audit_slug()] = {
            "mutation_type": req.mutation_type.value,
            "source": req.source.value,
            "payload": dict(req.payload),
        }
    return out

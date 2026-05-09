"""Mutation resolution composer (D → S → M per key) (#170)."""

from __future__ import annotations

from typing import Any, Optional

from continuity_mutation_pipeline_extract import (
    extract_d_excursion_candidates,
    extract_d_spatial_candidates,
    extract_m_excursion_candidates,
    extract_m_spatial_candidates,
    extract_s_candidates,
)
from continuity_mutation_pipeline_normalize import _normalize_excursion_id
from continuity_mutation_pipeline_types import (
    CanonicalAtom,
    ContinuityMutationError,
    ContinuityMutationType,
    MutationRequest,
    MutationResolutionKey,
    MutationSourceClass,
    _PENDING_OPEN_SCOPE,
    _SOURCE_RANK,
)


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

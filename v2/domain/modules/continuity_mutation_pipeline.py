"""Continuity mutation pipeline (Issue #81 — spatial + excursion lifecycle).

Typed mutation requests, composer with D → S → M precedence per canonical atom,
global validation, and atomic application to ``SceneState`` / excursion store
inside ``process_turn``.

**#170:** Mechanical split across ``continuity_mutation_pipeline_*`` modules; this
file is the stable public façade — import from here only unless an explicit
exemption is recorded.
"""

from __future__ import annotations

from continuity_mutation_pipeline_apply import apply_resolved_mutations
from continuity_mutation_pipeline_audit import resolved_mutations_audit_payload
from continuity_mutation_pipeline_compose import (
    compose_resolved_mutations,
    mutation_resolution_key,
)
from continuity_mutation_pipeline_extract import (
    extract_d_excursion_candidates,
    extract_d_spatial_candidates,
    extract_m_excursion_candidates,
    extract_m_spatial_candidates,
    extract_s_candidates,
)
from continuity_mutation_pipeline_types import (
    MAX_EXCURSION_ID_LEN,
    MAX_EXCURSION_PARTICIPANTS,
    MAX_SPATIAL_LOCATION_LEN,
    CanonicalAtom,
    ContinuityMutationError,
    ContinuityMutationType,
    MutationRequest,
    MutationResolutionKey,
    MutationSourceClass,
)
from continuity_mutation_pipeline_validate import (
    validate_excursion_lifecycle_move_shape,
    validate_resolved_mutations_globally,
    validate_spatial_transition_move_shape,
)

__all__ = [
    "MAX_EXCURSION_ID_LEN",
    "MAX_EXCURSION_PARTICIPANTS",
    "MAX_SPATIAL_LOCATION_LEN",
    "CanonicalAtom",
    "ContinuityMutationError",
    "ContinuityMutationType",
    "MutationRequest",
    "MutationResolutionKey",
    "MutationSourceClass",
    "apply_resolved_mutations",
    "compose_resolved_mutations",
    "extract_d_excursion_candidates",
    "extract_d_spatial_candidates",
    "extract_m_excursion_candidates",
    "extract_m_spatial_candidates",
    "extract_s_candidates",
    "mutation_resolution_key",
    "resolved_mutations_audit_payload",
    "validate_excursion_lifecycle_move_shape",
    "validate_resolved_mutations_globally",
    "validate_spatial_transition_move_shape",
]

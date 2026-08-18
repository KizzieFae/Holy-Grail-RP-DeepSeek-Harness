"""Registry for resolved continuity outcomes (aspect-scoped, deterministic).

`ResolvedOutcome` rows (see `continuity_state`) are **slot-scoped** continuity facts: row
`status` is `active` / `superseded` / `revoked`; **domain** state (e.g. transactional
**phase** for `transaction.scene_commitment`, GitHub #127) lives in `value`, not the
English word *resolved* on the type name.

Implementation is split across `resolved_outcome_*` modules (GitHub #163); this file is the
stable import facade (`ASPECT_REGISTRY` + symbols consumed by callers).
"""

from __future__ import annotations

from resolved_outcome_access_location_entry import (
    ACCESS_LOCATION_ENTRY_ALLOWED_RULE_ID,
    ACCESS_LOCATION_ENTRY_ASPECT_ID,
    ACCESS_LOCATION_ENTRY_DENIED_RULE_ID,
    ACCESS_LOCATION_ENTRY_SPEC,
    LOCATION_ENTRY_STATUSES,
    AccessLocationEntryPromotionPolicy,
    get_valid_location_entry_ids,
    parse_location_entry_outcome_candidates,
)
from resolved_outcome_communication_housing_call import (
    COMMUNICATION_HOUSING_CALL_ASPECT_ID,
    COMMUNICATION_HOUSING_CALL_SPEC,
    HOUSING_CALL_COMPLETED_RULE_ID,
    HOUSING_CALL_FAILED_RULE_ID,
    HOUSING_CALL_ISSUE_RULE_ID,
    HOUSING_CALL_TERMINAL_STATUSES,
    CommunicationHousingCallPromotionPolicy,
    parse_housing_call_outcome_candidates,
)
from resolved_outcome_lodging_sleep_surface import (
    FALLBACK_SLEEPING_SURFACE_IDS,
    LODGING_SLEEP_SURFACE_ASPECT_ID,
    LODGING_SLEEP_SURFACE_SPEC,
    SLEEPING_SURFACE_CONSEQUENCE_RULE_ID,
    SLEEPING_SURFACE_ISSUE_PREFIX,
    SLEEPING_SURFACE_ISSUE_RULE_ID,
    LodgingSleepSurfacePromotionPolicy,
    get_valid_sleeping_surface_ids,
    parse_lodging_sleep_surface_candidates,
)
from resolved_outcome_medical_suppressant_formulation import (
    MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID,
    MEDICAL_SUPPRESSANT_FORMULATION_SPEC,
    SUPPRESSANT_FORMULATION_COMPATIBLE_RULE_ID,
    SUPPRESSANT_FORMULATION_INCOMPATIBLE_RULE_ID,
    SUPPRESSANT_FORMULATION_STATUSES,
    MedicalSuppressantFormulationPromotionPolicy,
    parse_suppressant_formulation_outcome_candidates,
)
from resolved_outcome_normalize import encode_slot_key
from resolved_outcome_spec import (
    AspectSpec,
    NormalizedCandidate,
    PromotionContext,
    PromotionDecision,
    PromotionPolicy,
)
from resolved_outcome_transaction_scene_commitment import (
    SCENE_COMMITMENT_AWAITING_RULE_ID,
    SCENE_COMMITMENT_COMMITTED_RULE_ID,
    SCENE_COMMITMENT_FAILED_RULE_ID,
    SCENE_COMMITMENT_FULFILLED_RULE_ID,
    SCENE_COMMITMENT_KINDS,
    SCENE_COMMITMENT_PHASES,
    TRANSACTION_SCENE_COMMITMENT_ASPECT_ID,
    TRANSACTION_SCENE_COMMITMENT_SPEC,
    TransactionSceneCommitmentPromotionPolicy,
    merge_transaction_commitment_value_for_apply,
    parse_scene_commitment_outcome_candidates,
    transaction_commitment_semantic_equal,
)

ASPECT_REGISTRY: dict[str, AspectSpec] = {
    LODGING_SLEEP_SURFACE_ASPECT_ID: LODGING_SLEEP_SURFACE_SPEC,
    COMMUNICATION_HOUSING_CALL_ASPECT_ID: COMMUNICATION_HOUSING_CALL_SPEC,
    MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID: MEDICAL_SUPPRESSANT_FORMULATION_SPEC,
    ACCESS_LOCATION_ENTRY_ASPECT_ID: ACCESS_LOCATION_ENTRY_SPEC,
    TRANSACTION_SCENE_COMMITMENT_ASPECT_ID: TRANSACTION_SCENE_COMMITMENT_SPEC,
}

__all__ = [
    "ASPECT_REGISTRY",
    "AspectSpec",
    "NormalizedCandidate",
    "PromotionContext",
    "PromotionDecision",
    "PromotionPolicy",
    "encode_slot_key",
    "LODGING_SLEEP_SURFACE_ASPECT_ID",
    "COMMUNICATION_HOUSING_CALL_ASPECT_ID",
    "MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID",
    "ACCESS_LOCATION_ENTRY_ASPECT_ID",
    "TRANSACTION_SCENE_COMMITMENT_ASPECT_ID",
    "SLEEPING_SURFACE_ISSUE_RULE_ID",
    "SLEEPING_SURFACE_CONSEQUENCE_RULE_ID",
    "SLEEPING_SURFACE_ISSUE_PREFIX",
    "HOUSING_CALL_ISSUE_RULE_ID",
    "HOUSING_CALL_COMPLETED_RULE_ID",
    "HOUSING_CALL_FAILED_RULE_ID",
    "SUPPRESSANT_FORMULATION_COMPATIBLE_RULE_ID",
    "SUPPRESSANT_FORMULATION_INCOMPATIBLE_RULE_ID",
    "ACCESS_LOCATION_ENTRY_ALLOWED_RULE_ID",
    "ACCESS_LOCATION_ENTRY_DENIED_RULE_ID",
    "SCENE_COMMITMENT_COMMITTED_RULE_ID",
    "SCENE_COMMITMENT_AWAITING_RULE_ID",
    "SCENE_COMMITMENT_FULFILLED_RULE_ID",
    "SCENE_COMMITMENT_FAILED_RULE_ID",
    "FALLBACK_SLEEPING_SURFACE_IDS",
    "HOUSING_CALL_TERMINAL_STATUSES",
    "SUPPRESSANT_FORMULATION_STATUSES",
    "LOCATION_ENTRY_STATUSES",
    "SCENE_COMMITMENT_KINDS",
    "SCENE_COMMITMENT_PHASES",
    "LodgingSleepSurfacePromotionPolicy",
    "CommunicationHousingCallPromotionPolicy",
    "MedicalSuppressantFormulationPromotionPolicy",
    "AccessLocationEntryPromotionPolicy",
    "TransactionSceneCommitmentPromotionPolicy",
    "LODGING_SLEEP_SURFACE_SPEC",
    "COMMUNICATION_HOUSING_CALL_SPEC",
    "MEDICAL_SUPPRESSANT_FORMULATION_SPEC",
    "ACCESS_LOCATION_ENTRY_SPEC",
    "TRANSACTION_SCENE_COMMITMENT_SPEC",
    "get_valid_sleeping_surface_ids",
    "get_valid_location_entry_ids",
    "parse_lodging_sleep_surface_candidates",
    "parse_housing_call_outcome_candidates",
    "parse_suppressant_formulation_outcome_candidates",
    "parse_location_entry_outcome_candidates",
    "parse_scene_commitment_outcome_candidates",
    "merge_transaction_commitment_value_for_apply",
    "transaction_commitment_semantic_equal",
]

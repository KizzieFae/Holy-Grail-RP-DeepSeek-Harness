/**
 * Issue #201 LH-0 — persistent obligation lifecycle state codes.
 * @see governance/records/issue-201-long-horizon-refined-experimental-design-2026-09-15.md §10
 */

export const LIFECYCLE_STATES = Object.freeze({
  GEN_UNUSED: 'GEN_UNUSED',
  PERSIST_INACCESSIBLE: 'PERSIST_INACCESSIBLE',
  PROJECT_IGNORED: 'PROJECT_IGNORED',
  CONSUMED_INERT: 'CONSUMED_INERT',
  DEFERRED_VALID: 'DEFERRED_VALID',
  ACTIVATED_CONSEQUENTIAL: 'ACTIVATED_CONSEQUENTIAL',
  ACTIVATED_PREMATURE: 'ACTIVATED_PREMATURE',
  TRACKED_DEAD: 'TRACKED_DEAD',
});

export const TRANSPORT_LEVELS = Object.freeze({
  L0_GENERATED: 'L0',
  L1_PERSISTED: 'L1',
  L2_PROJECTED: 'L2',
  L3_CONSUMER_REFERENCED: 'L3',
  L4_CONSEQUENTIAL: 'L4',
});

export const LIFECYCLE_EVENT_TYPES = Object.freeze({
  GENERATED: 'generated',
  PERSISTED: 'persisted',
  PROJECTED: 'projected',
  CONSUMER_RECEIVED: 'consumer_received',
  CONSUMER_USED: 'consumer_used',
  DECISION_INFLUENCED: 'decision_influenced',
  DEFERRED_VALID: 'deferred_valid',
  ACTIVATED: 'activated',
  OBSERVABLE_CONSEQUENCE: 'observable_consequence',
  PREMATURE_ACTIVATION: 'premature_activation',
  EXPIRED_DEAD: 'expired_dead',
  ENTITLEMENT_VIOLATION: 'entitlement_violation',
  PROJECTION_OMISSION: 'projection_omission',
});

export const SEAM_FAILURE_CLASSES = Object.freeze({
  PRODUCER_COGNITION: 'producer_cognition_failure',
  PERSISTENCE: 'persistence_failure',
  RETRIEVAL: 'retrieval_failure',
  ENTITLEMENT: 'entitlement_failure',
  PROJECTION: 'projection_failure',
  CONSUMPTION: 'consumption_failure',
  DECISION_INFLUENCE: 'decision_influence_failure',
  NARRATIVE_CONSEQUENCE: 'narrative_consequence_failure',
  K6_MULTI_ANCHOR: 'k6_multi_anchor_projection_failure',
});

export const PRESERVATION_MECHANISMS = Object.freeze([
  'continuity_only',
  'retrieval',
  'plot_overlay',
  'storyteller_state',
  'consolidated_state',
  'transcript_echo',
]);

export const LH0_SCHEMAS = Object.freeze({
  OBLIGATION: 'issue201_lh0_obligation_v1',
  LIFECYCLE_EVENT: 'issue201_lh0_lifecycle_event_v1',
  OBLIGATION_TRACE: 'issue201_lh0_obligation_trace_v1',
  ARM_CONFIG: 'issue201_lh0_arm_config_v1',
  FIXTURE_MANIFEST: 'issue201_lh0_fixture_manifest_v1',
  APPARATUS_VALIDATION: 'issue201_lh0_apparatus_validation_v1',
  ARCHAEOLOGY_RECORD: 'issue201_lh0_archaeology_record_v1',
  COST_ATTRIBUTION: 'issue201_lh0_cost_attribution_v1',
});

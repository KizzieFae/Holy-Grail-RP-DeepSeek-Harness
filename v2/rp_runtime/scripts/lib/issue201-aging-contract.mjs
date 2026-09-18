/**
 * Issue #201 — information-aging long-horizon apparatus contract.
 */
export const AGING_SCHEMAS = Object.freeze({
  FIXTURE_MANIFEST: 'issue201_aging_fixture_manifest_v1',
  PLAYER_POLICY: 'issue201_aging_player_policy_v1',
  TRACKED_ITEM_REGISTRY: 'issue201_aging_tracked_item_registry_v1',
  AGING_TIMELINE: 'issue201_aging_timeline_v1',
  QUALIFICATION: 'issue201_aging_apparatus_qualification_v1',
});

export const AGING_STATES = Object.freeze({
  PRESENT_RAW: 'PRESENT_RAW',
  PRESENT_LEAN_OTHER: 'PRESENT_LEAN_OTHER',
  AGED_OUT: 'AGED_OUT',
  PERSISTED_AVAILABLE: 'PERSISTED_AVAILABLE',
  OPPORTUNITY_PENDING: 'OPPORTUNITY_PENDING',
  TESTED: 'TESTED',
});

export const AGING_LEAN_CHANNELS = Object.freeze([
  'transcript',
  'continuity',
  'retrieval',
  'memory_summary',
  'role_private',
  'scene_context',
  'director_context',
  'other_lean',
  'stimulus',
]);

export const AGING_QUALIFIED_R5_APPARATUS_SHA = '8c4c32a327e51e47067bb32673f98b3a1d3954fb';
export const AGING_QUALIFIED_R5_RUNNER_SHA = '1b482d7803fed6a3ca97a5ab10ffc1fe520078e7';

export const AGING_DEFAULT_MAX_TURNS = 80;

export const AGING_STOP_REASONS = Object.freeze({
  STOP_A_CLEAN_RESULT: 'stop_a_clean_primary_result',
  STOP_B_MAX_BOUNDARY: 'stop_b_max_boundary_no_aging',
  STOP_C_FAIL_CLOSED: 'stop_c_fail_closed',
});

/**
 * Issue #201 LH-1A — frozen experimental contract constants.
 * @see governance/records/issue-201-long-horizon-refined-experimental-design-2026-09-15.md
 */
import { LH0_ARMS } from './issue201-lh0-arms.mjs';

export const LH1A_SCHEMAS = Object.freeze({
  FIXTURE_MANIFEST: 'issue201_lh1a_fixture_manifest_v1',
  PLAYER_POLICY: 'issue201_lh1a_player_policy_v1',
  CAMPAIGN_PLAN: 'issue201_lh1a_campaign_plan_v1',
  CHECKPOINT_SLICE: 'issue201_lh1a_checkpoint_slice_v1',
  BLIND_PACKET: 'issue201_lh1a_blind_sequence_packet_v1',
  BLIND_RUBRIC: 'issue201_lh1a_blind_rubric_v1',
  ARCHAEOLOGY_DOSSIER: 'issue201_lh1a_archaeology_dossier_v1',
  COST_ROLLUP: 'issue201_lh1a_cost_rollup_v1',
  VALIDATION: 'issue201_lh1a_apparatus_validation_v1',
});

export const LH1A_ARMS = LH0_ARMS;

export const LH1A_SCENARIO_FAMILIES = Object.freeze({
  AYAME: 'ayame_controlled',
  ARKHAM: 'arkham_stress',
});

export const LH1A_SCENARIO_IDS = Object.freeze({
  ayame_controlled: 'ayame_household_entry_evaluation',
  arkham_stress: 'arkham_asylum_mess_hall_arena',
});

export const LH1A_TURN_COUNT = 22;
export const LH1A_TURN_MIN = 20;
export const LH1A_TURN_MAX = 24;
export const LH1A_SCENE_COUNT = 2;
export const LH1A_SCENE_TRANSITION_TURN = 12;

export const LH1A_CHECKPOINTS = Object.freeze({
  C1: 8,
  C2: 16,
  C3: 22,
});

export const LH1A_OBLIGATION_CLASSES = Object.freeze([
  'dormant_thread',
  'competing_threads',
  'delayed_consequence',
  'promise_commitment',
  'foreshadow_payoff',
  'relationship_evolution',
  'old_information_resurface',
  'non_resolution_pressure',
  'premature_resolution_trap',
  'cross_scene_continuity',
]);

export const LH1A_FORBIDDEN_MODEL_FACING = Object.freeze([
  'obligation_id',
  'LH1A-',
  'LH0-OBL',
  'evaluator',
  'blind rubric',
  'behavior_markers',
  'arm_id',
  'lh_a',
  'lh_b',
  'lh_c',
  'lh_d',
  'plot_scribe',
  'storyteller',
  'consolidated',
]);

export const LH1A_BLIND_FORBIDDEN_PATTERNS = [
  /\blh_[abcd]\b/i,
  /\bplot[\s/_-]?scribe\b/i,
  /\bstoryteller\b/i,
  /\bconsolidated\b/i,
  /\bnarrative[\s_-]?intel\b/i,
  /\binference[\s_-]?count\b/i,
  /\btoken[\s_-]?count\b/i,
  /\barm[\s_-]?id\b/i,
  /\bpersistent[\s_-]?cognition\b/i,
];

export const LH1A_CORE_RUBRIC_DIMENSIONS = Object.freeze([
  'character_fidelity',
  'agency',
  'coherence',
  'responsiveness',
  'naturalness',
  'narrative_progression',
  'continuity_consistency',
]);

export const LH1A_LONG_HORIZON_RUBRIC_DIMENSIONS = Object.freeze([
  'thread_management',
  'delayed_payoff_quality',
  'cross_scene_coherence',
  'old_information_integration',
  'relationship_evolution',
  'premature_resolution_avoidance',
  'repetition_overtracking',
  'appropriate_dormancy',
  'dark_tone_preservation',
  'forced_payoff_avoidance',
  'long_horizon_narrative_progression',
  'competing_thread_handling',
]);

export const LH1A_DARK_STORY_SAFEGUARDS = Object.freeze([
  'Do not reward redemption merely because it resolves a thread.',
  'Do not reward wholesome reconciliation or tension smoothing.',
  'Do not reward moral lessons or forced happy arcs.',
  'Do not reward tidy closure or activation of every tracked item.',
  'Evaluate fidelity to scenario tone contract, including unresolved conflict where appropriate.',
]);

export function buildLh1aCampaignMatrix() {
  const arms = Object.values(LH1A_ARMS);
  const scenarios = Object.values(LH1A_SCENARIO_FAMILIES);
  return arms.flatMap((arm) => scenarios.map((scenarioKey) => ({
    arm,
    scenario_key: scenarioKey,
    scenario_id: LH1A_SCENARIO_IDS[scenarioKey],
    sequence_slot: `${arm}__${scenarioKey}`,
  })));
}

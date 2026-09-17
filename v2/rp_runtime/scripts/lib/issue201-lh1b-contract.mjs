/**
 * Issue #201 LH-1B — frozen causal replication contract constants.
 */
import { LH0_ARMS } from './issue201-lh0-arms.mjs';

export const LH1B_SCHEMAS = Object.freeze({
  FIXTURE_MANIFEST: 'issue201_lh1b_fixture_manifest_v1',
  PLAYER_POLICY: 'issue201_lh1b_player_policy_v1',
  CAMPAIGN_PLAN: 'issue201_lh1b_campaign_plan_v1',
  CHECKPOINT_SLICE: 'issue201_lh1b_checkpoint_slice_v1',
  BLIND_PACKET: 'issue201_lh1b_blind_sequence_packet_v1',
  ARCHAEOLOGY_DOSSIER: 'issue201_lh1b_archaeology_dossier_v1',
  COST_ROLLUP: 'issue201_lh1b_cost_rollup_v1',
  VALIDATION: 'issue201_lh1b_apparatus_validation_v1',
  CAUSAL_TRACE: 'issue201_lh1b_causal_trace_v1',
  SUBSTRATE_UNIQUENESS: 'issue201_lh1b_substrate_uniqueness_v1',
});

export const LH1B_ARMS = Object.freeze({
  LH_A: LH0_ARMS.LH_A,
  LH_B: LH0_ARMS.LH_B,
  LH_D: LH0_ARMS.LH_D,
});

export const LH1B_SCENARIO_FAMILIES = Object.freeze({
  AYAME: 'ayame_controlled',
});

export const LH1B_SCENARIO_IDS = Object.freeze({
  ayame_controlled: 'ayame_household_entry_evaluation',
});

export const LH1B_TURN_COUNT = 18;
export const LH1B_SCENE_TRANSITION_TURN = 10;

export const LH1B_CHECKPOINTS = Object.freeze({
  C1: 6,
  C2: 12,
  C3: 18,
});

/** Diagnostic only — not authoritative for R5 uniqueness. */
export const LH1B_TRANSCRIPT_WINDOW_TURNS = 6;

export const LH1B_LIVE_EXECUTION_ORDER = Object.freeze([
  { arm: 'lh_a', scenario_key: 'ayame_controlled', blind_label: 'S1' },
  { arm: 'lh_b', scenario_key: 'ayame_controlled', blind_label: 'S2' },
  { arm: 'lh_a', scenario_key: 'ayame_controlled', blind_label: 'S3' },
  { arm: 'lh_b', scenario_key: 'ayame_controlled', blind_label: 'S4' },
  { arm: 'lh_d', scenario_key: 'ayame_controlled', blind_label: 'S5' },
  { arm: 'lh_a', scenario_key: 'ayame_controlled', blind_label: 'S6' },
]);

export const LH1B_SUBSTRATE_SUFFICIENCY = Object.freeze([
  'persistence_unique',
  'transcript_sufficient',
  'continuity_sufficient',
  'retrieval_sufficient',
  'memory_or_summary_sufficient',
  'stimulus_sufficient',
  'other_substrate_sufficient',
  'ambiguous',
]);

export const LH1B_R_STAGES = Object.freeze([
  'R0_generated',
  'R1_projected',
  'R2_semantically_received',
  'R3_used',
  'R4_decision_influence',
  'R5_marginal_persistence_value',
]);

export const LH1B_BLIND_FORBIDDEN_PATTERNS = [
  /\blh_[abd]\b/i,
  /\bplot[\s/_-]?scribe\b/i,
  /\bstoryteller\b/i,
  /\bconsolidated\b/i,
  /\bnarrative[\s_-]?intel\b/i,
  /\barm[\s_-]?id\b/i,
  /\bpersistent[\s_-]?cognition\b/i,
  /\bbehavior_markers\b/i,
];

export function buildLh1bCampaignMatrix() {
  return LH1B_LIVE_EXECUTION_ORDER.map((slot) => ({
    arm: slot.arm,
    scenario_key: slot.scenario_key,
    blind_label: slot.blind_label,
    sequence_slot: `${slot.blind_label}__${slot.arm}`,
  }));
}

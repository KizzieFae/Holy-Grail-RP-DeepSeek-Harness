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
  LIVE_SEQUENCE: 'issue201_lh1b_live_sequence_v1',
  LIVE_CAMPAIGN_REPORT: 'issue201_lh1b_live_campaign_report_v1',
  LIVE_PREFLIGHT: 'issue201_lh1b_live_preflight_v1',
  RUNNER_QUALIFICATION: 'issue201_lh1b_runner_qualification_v1',
  FAILURE_POLICY: 'issue201_lh1b_live_failure_policy_v1',
  COST_ENVELOPE: 'issue201_lh1b_cost_envelope_v1',
});

/** Frozen apparatus candidate accepted before live-path wiring. */
export const LH1B_APPARATUS_CANDIDATE_SHA = 'ec4c82c';

/** Live runner wiring qualified via mock runner qualification (see governance record). */
export const LH1B_LIVE_RUNNER_BASE_SHA = LH1B_APPARATUS_CANDIDATE_SHA;

export const LH1B_FROZEN_HASHES = Object.freeze({
  fixture_hash: '96b8ef4fa90ab27f0956b4da8edba1a090b5efd22df28825d4e1a05ea9918a64',
  policy_hash: '362207fa89fa89b87765c5aa78ca5d554c7ae67264eda99463feb09d36514fa3',
  causal_design_hash: '78bc5ff240f08d8658df9645e4b862366c0a02d8ff3fa96cf18044d436484c58',
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

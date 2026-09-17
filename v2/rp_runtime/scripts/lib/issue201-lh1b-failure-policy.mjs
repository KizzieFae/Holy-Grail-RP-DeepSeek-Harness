/**
 * Issue #201 LH-1B — live campaign failure / retry policy (pre-authorization).
 */
import { LH1B_SCHEMAS } from './issue201-lh1b-contract.mjs';

export const LH1B_LIVE_FAILURE_POLICY = Object.freeze({
  schema: LH1B_SCHEMAS.FAILURE_POLICY,
  campaign_fail_closed: true,
  sequence_terminal_failure: {
    action: 'halt_sequence',
    continue_later_sequences: false,
    forensic_evidence: 'preserved',
    evaluable_evidence: 'sequence_marked_failed',
    replacement_requires_governance: true,
  },
  sequence_restart: {
    allowed: false,
    reason: 'Dedicated session isolation; restart would confound causal replication.',
    governance_override_required: true,
  },
  partial_sequence: {
    turns_committed_before_failure: 'forensic_only',
    included_in_causal_matrix: false,
    archaeology_export: 'observation_only',
  },
  campaign_partial: {
    completed_sequences: 'forensic_and_evaluable_if_full_18_turns',
    incomplete_sequences: 'forensic_only',
    blind_secondary: 'excludes_incomplete_sequences',
  },
  structural_retry: {
    uses_existing_bounded_repair: true,
    no_quality_retry_campaign: true,
    terminal_beat_failure_budget: 'existing_a2_character_budget',
  },
  hash_drift: {
    action: 'halt_before_inference',
    replacement_requires_governance: true,
  },
  stop_conditions: [
    'preflight_incomplete',
    'provenance_identity_lost',
    'classifier_unrecognized_obligation_ids',
    'director_projection_qualification_failed',
    'fixture_policy_hash_drift',
    'projection_seam_failed',
    'terminal_beat_failure_budget_exceeded',
    'arm_leakage_detected',
    'evidence_write_failure',
  ],
});

export function describeLh1bFailurePolicy() {
  return { ...LH1B_LIVE_FAILURE_POLICY };
}

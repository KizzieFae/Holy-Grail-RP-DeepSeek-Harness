/**
 * Issue #201 LH-1B — preflight gate wrapper.
 */
import { runLh1bApparatusValidationSuite } from './issue201-lh1b-validation-lib.mjs';

export const LH1B_STOP_CONDITIONS = Object.freeze([
  'preflight_incomplete',
  'provenance_identity_lost',
  'classifier_unrecognized_obligation_ids',
  'director_projection_qualification_failed',
  'fixture_policy_hash_drift',
  'projection_seam_failed',
  'terminal_beat_failure_budget_exceeded',
]);

export function runLh1bPreflight({ blockLive = true } = {}) {
  const validation = runLh1bApparatusValidationSuite();
  const stopConditions = [];
  if (!validation.pass) stopConditions.push('preflight_incomplete');
  if (!validation.synthetic?.proofs?.find((p) => p.name === 'provenance_round_trip')?.pass) {
    stopConditions.push('provenance_identity_lost');
  }
  if (!validation.synthetic?.proofs?.find((p) => p.name === 'director_projection_semantic_receipt')?.pass) {
    stopConditions.push('director_projection_qualification_failed');
  }
  return {
    ready_for_live_authorization: validation.pass && stopConditions.length === 0 && !blockLive,
    live_authorized: false,
    validation,
    stop_conditions: stopConditions,
  };
}

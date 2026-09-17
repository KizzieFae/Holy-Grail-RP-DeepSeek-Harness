/**
 * Issue #201 LH-1B — preflight gate wrapper (apparatus + optional live path).
 */
import { runLh1bApparatusValidationSuite } from './issue201-lh1b-validation-lib.mjs';
import { runLh1bLivePreflight } from './issue201-lh1b-live-preflight-lib.mjs';
import { LH1B_LIVE_FAILURE_POLICY } from './issue201-lh1b-failure-policy.mjs';

export const LH1B_STOP_CONDITIONS = LH1B_LIVE_FAILURE_POLICY.stop_conditions;

export function runLh1bPreflight({ blockLive = true, runnerQualification = null } = {}) {
  const validation = runLh1bApparatusValidationSuite();
  const livePreflight = runLh1bLivePreflight({
    requireRunnerQualification: Boolean(runnerQualification),
    runnerQualification,
  });
  const stopConditions = [];
  if (!validation.pass) stopConditions.push('preflight_incomplete');
  if (!livePreflight.all_pass) stopConditions.push('preflight_incomplete');
  if (!validation.synthetic?.proofs?.find((p) => p.name === 'provenance_round_trip')?.pass) {
    stopConditions.push('provenance_identity_lost');
  }
  if (!validation.synthetic?.proofs?.find((p) => p.name === 'director_projection_semantic_receipt')?.pass) {
    stopConditions.push('director_projection_qualification_failed');
  }
  if (runnerQualification && !runnerQualification.pass) {
    stopConditions.push('projection_seam_failed');
  }
  return {
    ready_for_live_authorization: validation.pass
      && livePreflight.all_pass
      && stopConditions.length === 0
      && !blockLive
      && (runnerQualification?.pass ?? false),
    live_authorized: false,
    validation,
    live_preflight: livePreflight,
    failure_policy: LH1B_LIVE_FAILURE_POLICY,
    stop_conditions: stopConditions,
  };
}

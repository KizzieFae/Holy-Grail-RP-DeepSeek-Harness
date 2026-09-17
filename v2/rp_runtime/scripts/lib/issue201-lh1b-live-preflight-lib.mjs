/**
 * Issue #201 LH-1B — mandatory preflight before live campaign execution.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import { runLh0ConsumerValueValidationSuite } from './issue201-lh0-consumer-value-validation-lib.mjs';
import { runLh0TimingValidationSuite } from './issue201-lh0-timing-validation-lib.mjs';
import {
  LH1B_APPARATUS_CANDIDATE_SHA,
  LH1B_FROZEN_HASHES,
  LH1B_SCHEMAS,
  LH1B_TURN_COUNT,
} from './issue201-lh1b-contract.mjs';
import { fixturePathForScenario, loadLh1bFixtureManifest } from './issue201-lh1b-fixtures.mjs';
import { loadLh1bPolicy, sha256File } from './issue201-lh1b-player-policy.mjs';
import { buildLh1bCampaignPlan, validateLh1bIsolation } from './issue201-lh1b-orchestrator.mjs';
import { runLh1bApparatusValidationSuite } from './issue201-lh1b-validation-lib.mjs';
import { LH1B_LIVE_FAILURE_POLICY } from './issue201-lh1b-failure-policy.mjs';
import { buildLh1bCostEnvelope } from './issue201-lh1b-cost-envelope.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LIVE_LIB_PATH = path.join(__dirname, 'issue201-lh1b-live-lib.mjs');
const RUNNER_QUAL_PATH = path.join(__dirname, 'issue201-lh1b-runner-qualification-lib.mjs');

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

export function runLh1bLivePreflight({
  apparatusCandidateSha = LH1B_APPARATUS_CANDIDATE_SHA,
  requireRunnerQualification = false,
  runnerQualification = null,
  liveExecutionAuthorized = false,
} = {}) {
  const checks = [];
  const campaignPlan = buildLh1bCampaignPlan();
  const apparatus = runLh1bApparatusValidationSuite();
  const lh0Consumer = runLh0ConsumerValueValidationSuite();
  const lh0Timing = runLh0TimingValidationSuite();
  const liveLibSource = fs.existsSync(LIVE_LIB_PATH) ? fs.readFileSync(LIVE_LIB_PATH, 'utf8') : '';
  const runnerQualSource = fs.existsSync(RUNNER_QUAL_PATH)
    ? fs.readFileSync(RUNNER_QUAL_PATH, 'utf8')
    : '';

  const fixturePath = fixturePathForScenario();
  const { policy, policy_path } = loadLh1bPolicy();
  const fixture = loadLh1bFixtureManifest();
  const measured = {
    fixture_hash: sha256File(fixturePath),
    policy_hash: sha256File(policy_path),
    causal_design_hash: crypto.createHash('sha256')
      .update(JSON.stringify(fixture.causal_design))
      .digest('hex'),
  };

  for (const [key, expected] of Object.entries(LH1B_FROZEN_HASHES)) {
    checks.push(check(`frozen_hash_${key}`, measured[key] === expected, `${measured[key]} vs ${expected}`));
  }
  checks.push(check('apparatus_candidate_identified', apparatusCandidateSha === LH1B_APPARATUS_CANDIDATE_SHA));
  checks.push(check('six_sequences_planned', campaignPlan.sequence_count === 6));
  checks.push(check('eighteen_turns_per_sequence', campaignPlan.sequences.every((s) => s.turn_count === LH1B_TURN_COUNT)));
  checks.push(check('sequence_isolation', validateLh1bIsolation(campaignPlan).pass === true));
  checks.push(check('live_wiring_pvr_record', liveLibSource.includes('runPlayerPvrAndRecord')));
  checks.push(check('live_wiring_a2_beat', liveLibSource.includes('runA2BeatRound')));
  checks.push(check('live_wiring_lh_provenance_audit', liveLibSource.includes('lhProvenanceAudit')));
  checks.push(check('live_wiring_director_force_t15', liveLibSource.includes('lh1bForceDirectorInference')));
  checks.push(check('live_wiring_causal_classifier', liveLibSource.includes('evaluateCharacterForkAtTurn')));
  checks.push(check('live_wiring_frozen_hash_gate', liveLibSource.includes('verifyLh1bFrozenHashes')));
  checks.push(check('live_wiring_arm_isolation', liveLibSource.includes('verifyArmIsolation')));
  checks.push(check('live_wiring_failure_policy', liveLibSource.includes('LH1B_LIVE_FAILURE_POLICY')));
  checks.push(check('runner_qualification_module_present', runnerQualSource.includes('runLh1bRunnerMockQualification')));
  checks.push(check('campaign_fail_closed', campaignPlan.fail_closed === true));
  checks.push(check('lh1b_apparatus_regressions', apparatus.pass === true));
  checks.push(check('lh0_consumer_regressions', lh0Consumer.all_pass === true));
  checks.push(check('lh0_timing_regressions', lh0Timing.all_pass === true));
  checks.push(check('failure_policy_documented', LH1B_LIVE_FAILURE_POLICY.campaign_fail_closed === true));
  checks.push(check('cost_envelope_available', Boolean(buildLh1bCostEnvelope().lh1b_campaign)));

  if (requireRunnerQualification) {
    checks.push(check(
      'runner_mock_qualification_pass',
      runnerQualification?.pass === true,
      runnerQualification?.failures?.join(', ') ?? 'not_run',
    ));
  }

  const lhA = buildLh0ArmConfig('lh_a');
  const lhB = buildLh0ArmConfig('lh_b');
  const lhD = buildLh0ArmConfig('lh_d');
  checks.push(check('lh_a_no_persistent', lhA.persistent_cognition_enabled === false));
  checks.push(check('lh_b_plot_scribe', lhB.persistent_cognition_enabled === true));
  checks.push(check('lh_d_consolidated', lhD.persistent_cognition_enabled === true));

  const allPass = checks.every((c) => c.pass);
  return {
    schema: LH1B_SCHEMAS.LIVE_PREFLIGHT,
    apparatus_candidate_sha: apparatusCandidateSha,
    execution_candidate_sha: gitSha(),
    frozen_hashes: LH1B_FROZEN_HASHES,
    measured_hashes: measured,
    campaign_plan: campaignPlan,
    failure_policy: LH1B_LIVE_FAILURE_POLICY,
    cost_envelope: buildLh1bCostEnvelope(),
    checks,
    all_pass: allPass,
    live_execution_authorized: liveExecutionAuthorized && allPass,
    ready_for_governance_live_authorization: allPass
      && (!requireRunnerQualification || runnerQualification?.pass === true),
  };
}

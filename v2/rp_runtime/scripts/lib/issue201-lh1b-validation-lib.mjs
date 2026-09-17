/**
 * Issue #201 LH-1B — deterministic apparatus validation suite.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';

import { buildLh0ArmConfig } from './issue201-lh0-arms.mjs';
import { runLh0ConsumerValueValidationSuite } from './issue201-lh0-consumer-value-validation-lib.mjs';
import { runLh0TimingValidationSuite } from './issue201-lh0-timing-validation-lib.mjs';
import {
  LH1B_CHECKPOINTS,
  LH1B_LIVE_EXECUTION_ORDER,
  LH1B_SCHEMAS,
  LH1B_TURN_COUNT,
  LH1B_TRANSCRIPT_WINDOW_TURNS,
} from './issue201-lh1b-contract.mjs';
import {
  fixturePathForScenario,
  loadLh1bFixtureManifest,
  listLh1bDecisionForks,
} from './issue201-lh1b-fixtures.mjs';
import {
  buildLh1bCampaignPlan,
  validateLh1bIsolation,
} from './issue201-lh1b-orchestrator.mjs';
import { loadLh1bPolicy, sha256File } from './issue201-lh1b-player-policy.mjs';
import { runLh1bSyntheticProofs } from './issue201-lh1b-synthetic-proofs.mjs';
import { evaluateTurnCausalEvidence } from './issue201-lh0-semantic-content.mjs';

function check(name, pass, detail = null) {
  return { name, pass, detail };
}

export function frozenLh1bHashes() {
  const fixturePath = fixturePathForScenario();
  const { policy_path } = loadLh1bPolicy();
  const fixture = loadLh1bFixtureManifest();
  const causalPayload = JSON.stringify(fixture.causal_design);
  return {
    fixture_hash: sha256File(fixturePath),
    policy_hash: sha256File(policy_path),
    causal_design_hash: crypto.createHash('sha256').update(causalPayload).digest('hex'),
    fixture_id: fixture.fixture_id,
    policy_id: loadLh1bPolicy().policy.policy_id,
  };
}

export function runLh1bApparatusValidationSuite() {
  const checks = [];
  const fixture = loadLh1bFixtureManifest();
  const campaignPlan = buildLh1bCampaignPlan();
  const hashes = frozenLh1bHashes();
  const synthetic = runLh1bSyntheticProofs();
  const lh0Consumer = runLh0ConsumerValueValidationSuite();
  const lh0Timing = runLh0TimingValidationSuite();

  checks.push(check('fixture_schema_valid', fixture.schema === LH1B_SCHEMAS.FIXTURE_MANIFEST));
  checks.push(check('policy_schema_valid', loadLh1bPolicy().policy.schema === LH1B_SCHEMAS.PLAYER_POLICY));
  checks.push(check('fixture_policy_id_match', loadLh1bPolicy().policy.fixture_id === fixture.fixture_id));
  checks.push(check('turn_count_18', fixture.turns === LH1B_TURN_COUNT));
  checks.push(check('two_scenes', fixture.scenes.length === 2));
  checks.push(check('checkpoints_c1_c2_c3', (
    fixture.checkpoints.C1 === LH1B_CHECKPOINTS.C1
    && fixture.checkpoints.C2 === LH1B_CHECKPOINTS.C2
    && fixture.checkpoints.C3 === LH1B_CHECKPOINTS.C3
  )));
  checks.push(check('six_sequence_plan', campaignPlan.sequence_count === 6));
  checks.push(check('execution_order_s1_s6', (
    campaignPlan.sequences.map((s) => s.blind_label).join(',') === 'S1,S2,S3,S4,S5,S6'
  )));
  checks.push(check('ayame_only', campaignPlan.sequences.every((s) => s.scenario_key === 'ayame_controlled')));
  checks.push(check('lh_c_excluded', !campaignPlan.sequences.some((s) => s.arm === 'lh_c')));
  checks.push(check('lh_a_isolation', validateLh1bIsolation(campaignPlan).pass === true));

  const forks = listLh1bDecisionForks(fixture);
  checks.push(check('five_decision_forks', forks.length === 5));
  checks.push(check('four_character_forks', forks.filter((f) => f.consumer === 'character_move').length === 4));
  checks.push(check('one_director_fork', forks.filter((f) => f.consumer === 'director_turn').length === 1));

  const dirFork = forks.find((f) => f.fork_id === 'FORK-LH1B-DIR-TRAJECTORY');
  const dirObl = fixture.obligations.find((o) => o.obligation_id === 'LH1B-AYA-DIR-TRAJECTORY');
  checks.push(check('director_fork_advisory_not_dictation', (
    !String(dirObl?.semantic_content ?? '').toLowerCase().includes('choose ayame')
    && !String(dirObl?.semantic_content ?? '').toLowerCase().includes('prioritize beat')
  ), dirObl?.semantic_content));

  checks.push(check('transcript_window_diagnostic_only', fixture.transcript_window_turns === LH1B_TRANSCRIPT_WINDOW_TURNS));

  const classifier = evaluateTurnCausalEvidence({
    turnIndex: 17,
    moveText: 'trial staff receive only the pantry submaster key',
    presentationText: '',
    receivedObligationIds: ['LH1B-AYA-DEFERRED-KEY'],
    fixture,
  });
  checks.push(check('lh1b_classifier_recognizes_ids', classifier.influenced_obligation_ids.includes('LH1B-AYA-DEFERRED-KEY')));

  checks.push(check('synthetic_seam_qualification', synthetic.pass === true, synthetic.proofs.filter((p) => !p.pass).map((p) => p.name).join(', ')));
  checks.push(check('lh0_consumer_value_suite', lh0Consumer.all_pass === true));
  checks.push(check('lh0_timing_suite', lh0Timing.all_pass === true));

  for (const proof of synthetic.proofs) {
    checks.push(check(`synthetic_${proof.name}`, proof.pass === true));
  }

  checks.push(check('frozen_fixture_hash_recorded', Boolean(hashes.fixture_hash)));
  checks.push(check('frozen_policy_hash_recorded', Boolean(hashes.policy_hash)));
  checks.push(check('frozen_causal_design_hash_recorded', Boolean(hashes.causal_design_hash)));
  checks.push(check('live_not_authorized_flag', campaignPlan.live_authorized === false));

  const passCount = checks.filter((c) => c.pass).length;
  const fail = checks.filter((c) => !c.pass);
  return {
    schema: LH1B_SCHEMAS.VALIDATION,
    pass: fail.length === 0,
    checks,
    pass_count: passCount,
    fail_count: fail.length,
    frozen_hashes: hashes,
    synthetic,
    lh0_consumer: lh0Consumer,
    lh0_timing: lh0Timing,
    campaign_plan: campaignPlan,
  };
}

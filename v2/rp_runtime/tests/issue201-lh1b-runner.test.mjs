import test from 'node:test';
import assert from 'node:assert/strict';

import { runLh1bApparatusValidationSuite } from '../scripts/lib/issue201-lh1b-validation-lib.mjs';
import { runLh1bSyntheticProofs } from '../scripts/lib/issue201-lh1b-synthetic-proofs.mjs';
import { runLh1bRunnerMockQualification } from '../scripts/lib/issue201-lh1b-runner-qualification-lib.mjs';
import { runLh1bLivePreflight } from '../scripts/lib/issue201-lh1b-live-preflight-lib.mjs';
import { buildLh1bCostEnvelope, explainLh1bCostEstimateCorrection } from '../scripts/lib/issue201-lh1b-cost-envelope.mjs';
import { LH1B_FROZEN_HASHES } from '../scripts/lib/issue201-lh1b-contract.mjs';
import { verifyLh1bFrozenHashes } from '../scripts/lib/issue201-lh1b-live-lib.mjs';
import { buildLh1bCampaignPlan } from '../scripts/lib/issue201-lh1b-orchestrator.mjs';
import { runLh0ConsumerValueValidationSuite } from '../scripts/lib/issue201-lh0-consumer-value-validation-lib.mjs';

test('LH-1B frozen hashes unchanged', () => {
  const plan = buildLh1bCampaignPlan();
  const check = verifyLh1bFrozenHashes(plan.sequences[0]);
  assert.equal(check.pass, true, JSON.stringify(check.drift));
  assert.equal(check.measured.fixture_hash, LH1B_FROZEN_HASHES.fixture_hash);
});

test('LH-1B cost envelope uses LH-1A inference-event definition', () => {
  const correction = explainLh1bCostEstimateCorrection();
  assert.ok(correction.lh1a_observed_aggregate.inference_events === 782);
  assert.ok(correction.lh1a_observed_aggregate.events_per_player_turn < 10);
  const envelope = buildLh1bCostEnvelope();
  assert.ok(envelope.lh1b_campaign.expected_inference_events < 800);
  assert.ok(envelope.lh1b_campaign.expected_inference_events > 300);
});

test('LH-1B runner mock qualification through real turn path', { timeout: 1_800_000 }, async () => {
  const qualification = await runLh1bRunnerMockQualification();
  if (!qualification.pass) {
    assert.fail(`Runner qualification failed: ${qualification.failures.join(', ')}`);
  }
  assert.equal(qualification.pass, true);

  const preflight = runLh1bLivePreflight({
    requireRunnerQualification: true,
    runnerQualification: qualification,
  });
  assert.equal(preflight.all_pass, true, preflight.checks.filter((c) => !c.pass).map((c) => c.name).join(', '));
  assert.equal(preflight.live_execution_authorized, false);
});

test('LH-1B apparatus and LH-0 regressions', () => {
  const apparatus = runLh1bApparatusValidationSuite();
  const synthetic = runLh1bSyntheticProofs();
  const lh0 = runLh0ConsumerValueValidationSuite();
  assert.equal(apparatus.pass, true);
  assert.equal(synthetic.pass, true);
  assert.equal(lh0.all_pass, true);
});

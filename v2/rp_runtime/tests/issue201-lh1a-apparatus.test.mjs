import assert from 'node:assert/strict';
import test from 'node:test';

import { buildCampaignPlan, validateLhAIsolation, validateLhDFairness } from '../scripts/lib/issue201-lh1a-orchestrator.mjs';
import { runLh1aApparatusValidationSuite } from '../scripts/lib/issue201-lh1a-validation-lib.mjs';
import { runSyntheticLifecycleProofs } from '../scripts/lib/issue201-lh1a-synthetic-proofs.mjs';
import { buildLh1aBlindPacket, validateLh1aBlindPacketIntegrity } from '../scripts/lib/issue201-lh1a-blind-packet.mjs';
import { loadAllLh1aFixtures } from '../scripts/lib/issue201-lh1a-fixtures.mjs';
import { buildLh0ArmConfig } from '../scripts/lib/issue201-lh0-arms.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

test('LH-1A fixtures load with minimum obligation classes', () => {
  const fixtures = loadAllLh1aFixtures();
  assert.equal(fixtures.length, 2);
  for (const f of fixtures) {
    assert.ok(f.turns >= 20 && f.turns <= 24);
    assert.ok(f.scenes.length >= 2);
    assert.equal(f.obligations.length, 10);
  }
});

test('campaign plan has 8 sequences and LH-A isolation', () => {
  const plan = buildCampaignPlan();
  assert.equal(plan.sequences.length, 8);
  const isolation = validateLhAIsolation(plan);
  assert.equal(isolation.pass, true);
});

test('LH-D fairness controls pass', () => {
  const result = validateLhDFairness(buildLh0ArmConfig('lh_d'));
  assert.equal(result.pass, true);
});

test('blind packet integrity', () => {
  const plan = buildCampaignPlan();
  const rubric = JSON.parse(fs.readFileSync(
    path.join(REPO_ROOT, 'governance/records/issue201-lh1a-rubric/lh1a_blind_rubric_v1.json'),
    'utf8',
  ));
  const packet = buildLh1aBlindPacket({ campaignPlan: plan, rubric });
  const integrity = validateLh1aBlindPacketIntegrity(packet);
  assert.equal(integrity.pass, true);
});

test('synthetic lifecycle proofs pass', () => {
  const result = runSyntheticLifecycleProofs();
  if (!result.all_pass) {
    const failed = result.proofs.filter((p) => !p.pass);
    assert.fail(`synthetic proofs failed: ${failed.map((f) => f.name).join(', ')}`);
  }
});

test('LH-1A apparatus validation suite passes', () => {
  const report = runLh1aApparatusValidationSuite();
  if (!report.all_pass) {
    const failed = report.checks.filter((c) => !c.pass);
    assert.fail(`validation failed: ${failed.map((f) => f.name).join(', ')}`);
  }
});

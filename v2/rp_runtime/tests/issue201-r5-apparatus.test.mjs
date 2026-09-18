import test from 'node:test';
import assert from 'node:assert/strict';

import { runR5ApparatusQualification } from '../scripts/lib/issue201-r5-qualification-lib.mjs';
import { verifyR5FrozenHashes, R5_FROZEN_HASHES } from '../scripts/lib/issue201-r5-frozen-hashes.mjs';
import { buildR5CampaignPlan } from '../scripts/lib/issue201-r5-orchestrator.mjs';
import { proveEstablishmentEquivalence } from '../scripts/lib/issue201-r5-establishment-equivalence.mjs';
import { loadR5FixtureManifest } from '../scripts/lib/issue201-r5-fixtures.mjs';

test('R5 frozen hashes', () => {
  const check = verifyR5FrozenHashes();
  assert.equal(check.pass, true, JSON.stringify(check.drift));
  assert.equal(check.measured.fixture_hash, R5_FROZEN_HASHES.fixture_hash);
});

test('R5 campaign plan is A1/B1 only', () => {
  const plan = buildR5CampaignPlan();
  assert.equal(plan.sequence_count, 2);
  assert.deepEqual(plan.sequences.map((s) => s.blind_label), ['R5-A1', 'R5-B1']);
  assert.equal(plan.a2_replicate_deferred, true);
});

test('R5 establishment equivalence', () => {
  const fixture = loadR5FixtureManifest();
  const equiv = proveEstablishmentEquivalence(fixture);
  assert.equal(equiv.g1_shared_establishment, true);
  assert.equal(equiv.g2_entailment_no_extra_facts, true);
});

test('R5 apparatus qualification G1–G8', () => {
  const report = runR5ApparatusQualification();
  if (!report.pass) {
    assert.fail(`R5 qualification failed: ${report.failures.join(', ')}`);
  }
  assert.equal(report.pass, true);
  assert.equal(report.gates.length, 8);
});

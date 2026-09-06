import assert from 'node:assert/strict';
import test from 'node:test';

import { CampaignLimits } from '../src/scenario-harness/campaign-limits.mjs';
import {
  assertTruthNotInModelPayload,
  detectIssue136ForbiddenLeaks,
  ISSUE136_FIXTURE_IDS,
  listIssue136TruthFixtures,
  loadIssue136TruthFixture,
  loadIssue136ValidationCard,
  validateIssue136TruthSchema,
} from '../src/scenario-harness/issue136-fixture-truth.mjs';
import {
  deriveIssue136SafetyGuard,
  ISSUE136_REPETITIONS,
  runIssue136FixtureCampaign,
} from '../src/scenario-harness/issue136-tier2-campaign.mjs';

test('issue136 truth fixtures load and validate', () => {
  const fixtures = listIssue136TruthFixtures();
  assert.equal(fixtures.length, ISSUE136_FIXTURE_IDS.length);
  for (const { fixture_id } of fixtures) {
    const truth = loadIssue136TruthFixture(fixture_id);
    validateIssue136TruthSchema(truth, fixture_id);
    assert.ok(truth.supported_envelope.summary);
    assert.ok(truth.unsupported_envelope.summary);
  }
});

test('issue136 validation cards load', () => {
  const mara = loadIssue136ValidationCard('mara-slow-forgive');
  assert.equal(mara.name, 'Mara');
  const bob = loadIssue136ValidationCard('bob-default');
  assert.ok(Array.isArray(bob.private_memories));
  assert.ok(bob.private_memories.some((line) => line.includes('9999')));
});

test('issue136 truth records cannot enter model-facing session payloads', () => {
  const truth = loadIssue136TruthFixture('136-T2-E-ENTITLEMENT');
  const sessionPayload = {
    characters: truth.character_cards,
    opening: { mode: 'custom', text: truth.scene_stimulus },
    location: 'Workshop',
  };
  assertTruthNotInModelPayload(sessionPayload, truth);
  assert.throws(
    () => assertTruthNotInModelPayload({ notes: truth.unsupported_envelope.summary }, truth),
    /truth_contamination/,
  );
});

test('issue136 forbidden leak detection flags vault code', () => {
  const truth = loadIssue136TruthFixture('136-T2-E-ENTITLEMENT');
  const leaks = detectIssue136ForbiddenLeaks('Alice typed 9999 at the keypad.', truth, 'Alice');
  assert.ok(leaks.length > 0);
  assert.equal(detectIssue136ForbiddenLeaks('Alice listened at the door.', truth, 'Alice').length, 0);
});

test('issue136 entitlement fixture preserves three-turn live structure', () => {
  const truth = loadIssue136TruthFixture('136-T2-E-ENTITLEMENT');
  assert.equal(truth.turn_structure.rounds, 3);
  assert.deepEqual(truth.turn_structure.live_character_turns, [0, 1, 2]);
  assert.deepEqual(truth.cast, ['Alice', 'Bob']);
});

test('issue136 safety guard is derived not hard-coded', () => {
  const guard = deriveIssue136SafetyGuard();
  assert.ok(guard.max_inferences > 100);
  assert.ok(guard.max_runs >= 16);
  assert.equal(guard.derivation.campaign_runs, 16);
  assert.equal(guard.derivation.live_character_turns, 19);
  assert.ok(guard.derivation.margin > 0);

  const reduced = deriveIssue136SafetyGuard({
    repetitions: { '136-T2-A-STABILITY': 1 },
    includeSentinel: false,
    marginRatio: 0.1,
  });
  assert.ok(reduced.max_inferences < guard.max_inferences);
});

test('issue136 repetition plan matches authorized counts', () => {
  assert.equal(ISSUE136_REPETITIONS['136-T2-A-STABILITY'], 3);
  assert.equal(ISSUE136_REPETITIONS['136-T2-B-POS-CHANGE'], 2);
  assert.equal(ISSUE136_REPETITIONS['136-T2-C-NEG-CHANGE'], 2);
  assert.equal(ISSUE136_REPETITIONS['136-T2-D-INACTION'], 3);
  assert.equal(ISSUE136_REPETITIONS['136-T2-E-ENTITLEMENT'], 2);
  assert.equal(ISSUE136_REPETITIONS['136-T2-F-ACTION-REQUIRED'], 3);
});

test('campaign limits terminate runaway retry behavior', () => {
  const limits = new CampaignLimits({ maxRuns: 1, maxInferences: 1 });
  limits.recordRun();
  assert.throws(() => limits.assertCanRun(), /campaign_run_limit_exceeded/);
  limits.recordInference();
  assert.throws(() => limits.assertCanInfer(), /campaign_inference_limit_exceeded/);
});

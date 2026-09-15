import assert from 'node:assert/strict';
import test from 'node:test';

import { runLh0SemanticValidationSuite } from '../scripts/lib/issue201-lh0-semantic-validation-lib.mjs';
import { runLh0RemediationValidationSuite } from '../scripts/lib/issue201-lh0-remediation-lib.mjs';
import { obligationsForConsumer } from '../scripts/lib/issue201-lh0-persistent-store.mjs';
import { loadLh0FixtureManifest } from '../scripts/lib/issue201-lh0-fixtures.mjs';
import {
  buildLh0FinalizedProjection,
} from '../scripts/lib/issue201-lh0-persistent-store.mjs';
import {
  isBookkeepingOnlySemanticContent,
  seedLh0ObligationFromFixture,
  evaluateTurnCausalEvidence,
} from '../scripts/lib/issue201-lh0-semantic-content.mjs';
import { LH0_ARMS } from '../scripts/lib/issue201-lh0-arms.mjs';

test('LH-0 semantic validation suite passes', () => {
  const report = runLh0SemanticValidationSuite();
  if (!report.all_pass) {
    const failed = report.checks.filter((c) => !c.pass);
    assert.fail(`semantic checks failed: ${failed.map((f) => f.name).join(', ')}`);
  }
});

test('deferred obligations withheld until activation predicate', () => {
  const fixture = loadLh0FixtureManifest();
  const store = {
    obligations: fixture.obligations
      .filter((o) => !o.negative_control)
      .map((o) => seedLh0ObligationFromFixture(o, { mechanism: 'test', source: 'test' })),
    events: [],
  };
  const before = obligationsForConsumer(store, { turn: 4, consumer: 'character_move' });
  assert.equal(before.some((o) => o.obligation_id === 'LH0-OBL-DEFERRED'), false);
  const after = obligationsForConsumer(store, { turn: 5, consumer: 'character_move' });
  assert.equal(after.some((o) => o.obligation_id === 'LH0-OBL-DEFERRED'), true);
});

test('B/C/D projections use semantic model-facing content', () => {
  const fixture = loadLh0FixtureManifest();
  const later = fixture.obligations.find((o) => o.obligation_id === 'LH0-OBL-LATER');
  for (const arm of [LH0_ARMS.LH_B, LH0_ARMS.LH_C, LH0_ARMS.LH_D]) {
    const projection = buildLh0FinalizedProjection([later], {
      batchId: `batch-${arm}`,
      consumer: 'character_move',
      characterId: 'Ayame',
      hgRoundId: 'hg-round-1',
      turnIndex: 5,
    });
    const content = projection.contributions[0].content;
    assert.equal(isBookkeepingOnlySemanticContent(content), false);
    assert.match(content, /overnight guests/i);
  }
});

test('causal evidence uses decision fork classes not obligation IDs', () => {
  const evidence = evaluateTurnCausalEvidence({
    turnIndex: 5,
    moveText: 'Overnight guests are never permitted for live-in staff.',
    receivedObligationIds: ['LH0-OBL-LATER'],
  });
  assert.equal(evidence.consumer_used, true);
  assert.ok(evidence.influenced_obligation_ids.includes('LH0-OBL-LATER'));
});

test('remediation regressions still pass', () => {
  const report = runLh0RemediationValidationSuite();
  assert.equal(report.all_pass, true);
});

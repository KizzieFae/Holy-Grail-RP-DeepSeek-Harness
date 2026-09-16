import assert from 'node:assert/strict';
import test from 'node:test';

import { runLh0TimingValidationSuite } from '../scripts/lib/issue201-lh0-timing-validation-lib.mjs';
import { prepareLh0RoundTransport } from '../scripts/lib/issue201-lh0-transport.mjs';
import { loadLh0FixtureManifest } from '../scripts/lib/issue201-lh0-fixtures.mjs';
import {
  classifyLh0ObligationStates,
  obligationsForConsumer,
} from '../scripts/lib/issue201-lh0-persistent-store.mjs';
import { seedLh0ObligationFromFixture } from '../scripts/lib/issue201-lh0-semantic-content.mjs';
import { LH0_ARMS } from '../scripts/lib/issue201-lh0-arms.mjs';

test('LH-0 timing validation suite passes', () => {
  const report = runLh0TimingValidationSuite();
  if (!report.all_pass) {
    const failed = report.checks.filter((c) => !c.pass);
    assert.fail(`timing checks failed: ${failed.map((f) => f.name).join(', ')}`);
  }
});

test('fixture clock governs eligibility; binding clock is separate', () => {
  const fixture = loadLh0FixtureManifest();
  const store = {
    obligations: fixture.obligations
      .filter((o) => !o.negative_control)
      .map((o) => seedLh0ObligationFromFixture(o, { mechanism: 'test', source: 'test' })),
    events: [],
  };
  for (let turn = 1; turn <= 4; turn += 1) classifyLh0ObligationStates(store, turn);

  assert.equal(obligationsForConsumer(store, { turn: 4, consumer: 'character_move' }).length, 0);
  assert.ok(obligationsForConsumer(store, { turn: 5, consumer: 'character_move' }).length > 0);

  const transport = prepareLh0RoundTransport({
    sessionsDir: '/tmp/unused',
    hgSessionId: 'hg-session-clock',
    hgRoundId: 'hg-round-clock',
    fixtureTurnIndex: 5,
    bindingTurnIndex: 4,
    characterId: 'Ayame',
    arm: LH0_ARMS.LH_B,
    storeOverride: JSON.parse(JSON.stringify(store)),
  });
  assert.equal(transport.fixture_turn_index, 5);
  assert.equal(transport.runtime_binding_turn_index, 4);
  assert.equal(transport.characterDue.length, 2);
  assert.equal(transport.characterProjection.binding.turn_index, 4);
});

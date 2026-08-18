import assert from 'node:assert/strict';
import test from 'node:test';

import { createTestSession, fetchSessionState, startDomainApi } from './helpers/domain-api.mjs';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';

const MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'acts deliberately' }],
  motivation: { goal: 'a', tactic: 'b', emotional_driver: 'c', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const ALICE_OFFSTAGE_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'steps into the hallway' }],
  motivation: { goal: 'withdraw', tactic: 'leave the focal scene', emotional_driver: 'tense', risk_level: 'low' },
  semantic_evaluation: {
    decision: 'covered_change',
    proposals: [{ kind: 'off_focal', character: 'Alice' }],
  },
};

const DIRECTOR_FOR = (name) => ({
  next_actor: name,
  end_round: false,
  reason: `${name} should speak.`,
  environment_event: '',
  tension_shift: '',
});

test('presence: off_focal commit narrows later eligibility to remaining present actor', async (t) => {
  const port = 36765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [
      [JSON.stringify(ALICE_OFFSTAGE_MOVE)],
      [JSON.stringify(MOVE)],
    ],
  });

  assert.equal(result.completion_reason, 'no_eligible_actors');
  assert.equal(result.character_turn_count, 2);
  assert.deepEqual(result.actors_used_this_round, ['Alice', 'Bob']);

  const snapshots = result.scene_events.filter((e) => e.type === 'hg/eligibility-snapshot');
  assert.equal(snapshots.length, 2);
  assert.deepEqual(snapshots[0].data.eligibility_snapshot.eligible_actors, ['Alice', 'Bob']);
  assert.deepEqual(snapshots[1].data.eligibility_snapshot.eligible_actors, ['Bob']);
  assert.ok(snapshots[1].data.eligibility_snapshot.offstage_characters.includes('Alice'));
});

test('presence: director cannot select offstage actor after presence mutation', async (t) => {
  const port = 37765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [
      [JSON.stringify(ALICE_OFFSTAGE_MOVE)],
      [JSON.stringify(MOVE)],
    ],
  });

  const rejected = result.scene_events.filter((e) => e.type === 'hg/director-rejected');
  assert.equal(rejected.length, 1);
  assert.match(rejected[0].data.reason, /ineligible|already_used|offstage/i);
  assert.equal(result.completion_reason, 'no_eligible_actors');
});

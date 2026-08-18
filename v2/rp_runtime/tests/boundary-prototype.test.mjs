import assert from 'node:assert/strict';
import test from 'node:test';

import { createTestSession, fetchSessionState, startDomainApi } from './helpers/domain-api.mjs';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods thoughtfully' }],
  motivation: {
    goal: 'acknowledge',
    tactic: 'subtle gesture',
    emotional_driver: 'calm',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const INVALID_MOVE = {
  move_schema_version: 2,
  beats: [],
  motivation: { goal: 'x', tactic: 'x', emotional_driver: 'x', risk_level: 'x' },
};

const VALID_DIRECTOR = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should speak next.',
  environment_event: '',
  tension_shift: '',
};

const INVALID_DIRECTOR = {
  next_actor: 'Zelda',
  end_round: false,
  reason: 'invalid actor',
  environment_event: '',
  tension_shift: '',
};

test('boundary prototype: reject then commit with correlated hg events', async (t) => {
  const port = 18765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, phaseExecutors } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await phaseExecutors.runCharacterInference({
    domainApi: { baseUrl },
    mockResponses: [JSON.stringify(INVALID_MOVE), JSON.stringify(VALID_MOVE)],
  });

  assert.equal(result.committed, true);
  assert.ok(result.domain_commit_id);
  assert.equal(result.continuity_turn_index, 1);

  const proposed = result.scene_events.filter((e) => e.type === 'hg/move-proposed');
  const rejected = result.scene_events.filter((e) => e.type === 'hg/move-rejected');
  const committed = result.scene_events.filter((e) => e.type === 'hg/move-committed');
  assert.equal(proposed.length, 2);
  assert.equal(rejected.length, 1);
  assert.equal(committed.length, 1);
});

test('boundary prototype: DSH-only proposal does not commit', async (t) => {
  const port = 19765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const created = await createTestSession(baseUrl, ['Alice', 'Bob']);
  const hgSceneId = created.hg_scene_id;

  const { ctx, phaseExecutors } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await phaseExecutors.runCharacterInference({
    domainApi: { baseUrl },
    hgSceneId,
    mockResponses: [JSON.stringify(INVALID_MOVE)],
  });

  assert.equal(result.committed, false);
  const state = await fetchSessionState(baseUrl, created.hg_session_id);
  assert.equal(state.turn_counter, 0);
  assert.equal(state.committed_move_count, 0);
});

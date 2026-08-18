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

const DIRECTOR_FOR = (name) => ({
  next_actor: name,
  end_round: false,
  reason: `${name} should speak.`,
  environment_event: '',
  tension_shift: '',
});

test('participation: forced designation selects Alice without Director inference', async (t) => {
  const port = 38765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    forcedDesignation: 'Alice',
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Bob'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  assert.equal(result.character_turn_count, 1);
  assert.equal(result.actors_used_this_round[0], 'Alice');
  assert.equal(result.scene_events.some((e) => e.type === 'hg/director-proposed'), false);
  const participation = result.scene_events.find((e) => e.type === 'hg/participation-decision');
  assert.ok(participation);
  assert.equal(participation.data.participation.selection_mode, 'direct');
  assert.equal(participation.data.participation.selected_actor, 'Alice');
  assert.deepEqual(participation.data.participation.participation_sources, ['forced_designation']);
});

test('participation: ineligible forced designation falls back to Director', async (t) => {
  const port = 39765 + Math.floor(Math.random() * 1000);
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
    forcedDesignation: 'Carol',
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  const participation = result.scene_events.find((e) => e.type === 'hg/participation-decision');
  assert.ok(participation);
  assert.equal(participation.data.participation.selection_mode, 'director');
  assert.equal(participation.data.participation.forced_designation_ignored, true);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/director-proposed'), true);
});

test('participation: forced designation consumed only once per round invocation', async (t) => {
  const port = 40765 + Math.floor(Math.random() * 1000);
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
    forcedDesignation: 'Alice',
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Bob')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)], [JSON.stringify(MOVE)]],
  });

  const participationEvents = result.scene_events.filter((e) => e.type === 'hg/participation-decision');
  assert.equal(participationEvents.length, 2);
  assert.equal(participationEvents[0].data.participation.selection_mode, 'direct');
  assert.equal(participationEvents[1].data.participation.selection_mode, 'director');
  assert.equal(result.character_turn_count, 2);
});

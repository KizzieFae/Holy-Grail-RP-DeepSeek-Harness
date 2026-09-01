import assert from 'node:assert/strict';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

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

function assertDistinctSessionIds(summaries) {
  const sessionIds = summaries
    .map((entry) => entry.inference_session_id)
    .filter(Boolean);
  assert.equal(new Set(sessionIds).size, sessionIds.length);
}

test('role_inference_summary: participation-direct bypasses Director inference', async (t) => {
  const port = 41765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    forcedDesignation: 'Alice',
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Bob'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  const summary = result.role_inference_summary;
  assert.equal(summary.director.phase_outcome, 'bypassed');
  assert.equal(summary.director.inference_execution, 'not_executed');
  assert.equal(summary.director.inference_trace, null);
  assert.equal(summary.director.inference_session_id, null);
  assert.equal(summary.character.phase_outcome, 'succeeded');
  assert.ok(summary.character.inference_trace?.provider);
  assertDistinctSessionIds([summary.character, summary.narrator]);
});

test('role_inference_summary: normal mock round has inferred Director and Character', async (t) => {
  const port = 42765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  const summary = result.role_inference_summary;
  assert.equal(summary.director.phase_outcome, 'succeeded');
  assert.notEqual(summary.director.inference_execution, 'not_executed');
  assert.ok(summary.director.inference_trace?.provider);
  assert.equal(summary.character.phase_outcome, 'succeeded');
  assert.equal(summary.narrator.phase_outcome, 'succeeded');
  assertDistinctSessionIds([summary.director, summary.character, summary.narrator]);
});

test('role_inference_summary: narrator degradation after inference retains last trace', async (t) => {
  const port = 43765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    forcedDesignation: 'Alice',
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Bob'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    mockNarratorResponses: [''],
  });

  const summary = result.role_inference_summary;
  assert.equal(summary.narrator.phase_outcome, 'degraded');
  assert.notEqual(summary.narrator.inference_execution, 'not_executed');
  assert.ok(summary.narrator.inference_trace?.provider);
  assert.ok(summary.narrator.inference_session_id);
  assert.ok(result.scene_events.some((event) => event.type === 'hg/narrator-failed'));
});

test('role_inference_summary: director failure leaves character and narrator not reached', async (t) => {
  const port = 44765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: ['not-json'],
    liveMaxAttempts: 1,
  });

  const summary = result.role_inference_summary;
  assert.equal(summary.director.phase_outcome, 'failed');
  assert.notEqual(summary.director.inference_execution, 'not_executed');
  assert.equal(summary.character.phase_outcome, 'not_reached');
  assert.equal(summary.narrator.phase_outcome, 'not_reached');
});

import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildDirectorBypassSummary,
  buildDirectorInferenceSummary,
} from '../src/lib/role-inference-summary.mjs';
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

test('role_inference_summary: last director activity replaces earlier inference summary', () => {
  let directorSummary = buildDirectorInferenceSummary({
    accepted: true,
    directorInferenceTrace: { provider: 'hg-mock', failed: false },
    directorInferenceSessionId: 'sess-director-1',
    directorEvidenceId: 'ev-director-1',
  });
  assert.equal(directorSummary.inference_execution, 'completed');
  assert.equal(directorSummary.phase_outcome, 'succeeded');

  directorSummary = buildDirectorBypassSummary();
  assert.equal(directorSummary.inference_execution, 'not_executed');
  assert.equal(directorSummary.phase_outcome, 'bypassed');
  assert.equal(directorSummary.inference_trace, null);
  assert.equal(directorSummary.inference_session_id, null);
});

const BOB_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'responds calmly' }],
  motivation: { goal: 'reply', tactic: 'measured tone', emotional_driver: 'steady', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

test('role_inference_summary: multi-turn director uses last inference activity', async (t) => {
  const port = 45765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [
      [JSON.stringify(MOVE)],
      [JSON.stringify(BOB_MOVE)],
    ],
    mockNarratorTurnResponses: [
      ['Alice acted deliberately.'],
      ['Bob responded calmly.'],
    ],
  });

  assert.equal(result.character_turn_count, 2);
  const participationEvents = result.scene_events.filter((e) => e.type === 'hg/participation-decision');
  assert.equal(participationEvents[0].data.participation.selection_mode, 'director');
  assert.equal(participationEvents[1].data.participation.selection_mode, 'director');
  assert.equal(result.scene_events.filter((e) => e.type === 'hg/director-accepted').length, 2);

  const summary = result.role_inference_summary;
  assert.equal(summary.director.phase_outcome, 'succeeded');
  assert.equal(summary.director.inference_execution, 'completed');
  assert.ok(summary.director.inference_trace?.provider);
  assert.ok(summary.director.inference_session_id);
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

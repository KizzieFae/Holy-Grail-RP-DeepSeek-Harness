import assert from 'node:assert/strict';
import test from 'node:test';

import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import {
  baselineLastTurn,
  extractTurnBoundaryTiming,
  waitForTurnEnd,
  waitForTurnStart,
} from '../src/lib/inference-turn-timing.mjs';
import { HgMockLlmAdapter } from '../src/mock-llm-adapter.mjs';

test('waitForTurnEnd observes paired turn/start and turn/end', async (t) => {
  const { ctx } = await createHolyGrailRpContext({ inferenceMode: 'mock' });
  t.after(async () => {
    await ctx.fiber.dispose();
  });
  const dispose = ctx.llm.registerAdapter(['mock'], new HgMockLlmAdapter(['{"ok":true}']));
  t.after(() => dispose());
  const agent = ctx.agentLoop.create(SessionId('hg-turn-timing-test'));
  const eventsBefore = agent.session.events.length;
  agent.followup(createUserMessage({
    content: [{ type: 'text', text: 'x' }],
    source: { kind: 'user' },
  }));
  const expectedTurn = await waitForTurnStart(agent, { afterEventCount: eventsBefore });
  await waitForTurnEnd(agent, expectedTurn);
  const timing = extractTurnBoundaryTiming(agent.session.events, expectedTurn, String(agent.id));
  assert.equal(timing.timing_observed, true);
  assert.equal(timing.measurement, 'dsh_session_turn_boundary');
  assert.equal(typeof timing.inference_wall_clock_ms, 'number');
  assert.ok(timing.started_at);
  assert.ok(timing.ended_at);
});

test('extractTurnBoundaryTiming returns unavailable without turn/end', () => {
  const timing = extractTurnBoundaryTiming([
    { type: 'turn/start', seq: 1, time: 1000, data: { turn: 1 } },
  ], 1, 'sess');
  assert.equal(timing.timing_observed, false);
  assert.equal(timing.unavailable_reason, 'turn_end_not_observed');
  assert.equal(timing.inference_wall_clock_ms, undefined);
});

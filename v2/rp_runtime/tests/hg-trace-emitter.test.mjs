import assert from 'node:assert/strict';
import test from 'node:test';

import { SessionId } from '@deepseek-ai/dsh-session';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { HG_EVENT_TYPES } from '../src/plugins/hg-trace-emitter/index.mjs';

test('HgTraceEmitter: emits typed events with normalized correlation', async (t) => {
  const { ctx, traceEmitter } = await createHolyGrailRpContext();
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const sceneSessionId = SessionId('hg-scene-trace-test');
  const session = { events: [], append(type, data) { this.events.push({ type, data }); return data; } };
  const scope = {
    hgSessionId: 'session-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    sceneSessionId,
  };

  traceEmitter.emit(session, 'hg/round-started', scope, {
    turn_index: 0,
    defensive_turn_ceiling: 4,
  });

  assert.equal(session.events.length, 1);
  assert.equal(session.events[0].type, 'hg/round-started');
  assert.deepEqual(session.events[0].data, {
    hg_session_id: 'session-1',
    hg_scene_id: 'scene-1',
    hg_round_id: 'round-1',
    dsh_scene_session_id: String(sceneSessionId),
    turn_index: 0,
    defensive_turn_ceiling: 4,
  });
});

test('HgTraceEmitter: rejects unknown event types', async (t) => {
  const { ctx, traceEmitter } = await createHolyGrailRpContext();
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = { append() {} };
  assert.throws(
    () => traceEmitter.emit(session, 'hg/not-a-real-event', {
      hgSceneId: 's',
      hgRoundId: 'r',
      sceneSessionId: 'x',
    }),
    /unknown Holy Grail event type/,
  );
  assert.equal(HG_EVENT_TYPES.length, 36);
  assert.ok(HG_EVENT_TYPES.includes('hg/character-knowledge-cognition'));
  assert.ok(HG_EVENT_TYPES.includes('hg/director-semantic-qa'));
  assert.ok(HG_EVENT_TYPES.includes('hg/narrator-semantic-qa'));
  assert.ok(HG_EVENT_TYPES.includes('hg/semantic-evaluation'));
  assert.ok(HG_EVENT_TYPES.includes('hg/opening-started'));
});

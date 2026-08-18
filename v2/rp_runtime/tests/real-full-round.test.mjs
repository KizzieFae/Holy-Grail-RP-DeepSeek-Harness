import assert from 'node:assert/strict';
import test from 'node:test';

import { createTestSession, fetchSessionState, startDomainApi } from './helpers/domain-api.mjs';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

const LIVE_PROFILE = deepseekInferenceProfile({
  reasoningEffort: 'low',
  maxTokens: 768,
});

function findEvent(events, type) {
  return events.find((event) => event.type === type) ?? null;
}

test('real full round: Director → Character → commit → Narrator on DSH DeepSeek', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 180_000,
}, async (t) => {
  const port = 23765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: { mountDeepSeek: true },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    roleProfiles: {
      director: LIVE_PROFILE,
      character: LIVE_PROFILE,
      narrator: deepseekInferenceProfile({ reasoningEffort: 'off', maxTokens: 384 }),
    },
    liveMaxAttempts: 5,
  });

  assert.equal(result.completion_class, 'semantic');
  assert.equal(result.completion_reason, 'no_eligible_actors');
  assert.equal(result.character_turn_count, 1);
  assert.ok(result.domain_commit_id);
  assert.equal(typeof result.continuity_turn_index, 'number');

  const events = result.scene_events;
  const narratorCompleted = findEvent(events, 'hg/narrator-completed');
  const narratorFailed = findEvent(events, 'hg/narrator-failed');
  assert.ok(
    narratorCompleted || narratorFailed,
    'expected narrator phase to run after commit',
  );
  if (narratorFailed) {
    assert.equal(narratorFailed.data.canon_preserved, true);
  } else {
    assert.ok(result.presentation_rendered || result.presentation_text);
  }

  const traces = result.role_inference_traces;
  assert.equal(traces.director?.provider, 'deepseek-official');
  assert.equal(traces.character?.provider, 'deepseek-official');
  assert.equal(traces.narrator?.provider, 'deepseek-official');
  assert.ok(traces.director?.manifest_id);
  assert.ok(traces.character?.manifest_id);
  assert.ok(traces.narrator?.manifest_id);

  assert.ok(findEvent(events, 'hg/round-started'));
  assert.ok(findEvent(events, 'hg/participation-decision'));
  assert.ok(findEvent(events, 'hg/director-accepted') || findEvent(events, 'hg/director-proposed'));
  assert.ok(findEvent(events, 'hg/move-committed'));
  assert.ok(findEvent(events, 'hg/round-completed'));

  const directorProposed = findEvent(events, 'hg/director-proposed');
  if (directorProposed) {
    assert.equal(directorProposed.data.inference_trace?.provider, 'deepseek-official');
  }

  const moveCommitted = findEvent(events, 'hg/move-committed');
  assert.equal(moveCommitted.data.domain_commit_id, result.domain_commit_id);

  assert.ok(result.round_timing_ms.total > 0);
  assert.equal(result.boundary_metrics.calls.length > 0, true);

  const inferenceSessions = new Set([
    result.director_inference_session_id,
    result.character_inference_session_id,
    result.narrator_inference_session_id,
  ].filter(Boolean));
  assert.equal(inferenceSessions.size, 3, 'expected three distinct inference sessions');
  assert.notEqual(result.dsh_scene_session_id, result.director_inference_session_id);
});

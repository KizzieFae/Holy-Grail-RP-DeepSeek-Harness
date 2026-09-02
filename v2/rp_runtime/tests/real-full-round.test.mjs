import assert from 'node:assert/strict';
import test from 'node:test';

import { startDomainApi } from './helpers/domain-api.mjs';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

const LIVE_PROFILE = deepseekInferenceProfile({
  reasoningEffort: 'low',
  maxTokens: 768,
});

const EVALUATOR_PROFILE = deepseekInferenceProfile({
  reasoningEffort: 'off',
  maxTokens: 2048,
});

function findEvent(events, type) {
  return events.find((event) => event.type === type) ?? null;
}

function assertProviderWhenTracePresent(roleSummary) {
  if (roleSummary.inference_trace) {
    assert.equal(roleSummary.inference_trace.provider, 'deepseek-official');
    assert.ok(roleSummary.inference_trace.manifest_id);
    assert.ok(roleSummary.inference_session_id);
  } else {
    assert.equal(roleSummary.inference_execution, 'not_executed');
    assert.equal(roleSummary.inference_session_id, null);
  }
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
      semantic_evaluator: EVALUATOR_PROFILE,
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

  const summary = result.role_inference_summary;
  const participation = findEvent(events, 'hg/participation-decision');

  if (participation?.data?.participation?.selection_mode === 'direct') {
    assert.equal(summary.director.phase_outcome, 'bypassed');
    assert.equal(summary.director.inference_execution, 'not_executed');
    assert.equal(summary.director.inference_trace, null);
    assert.equal(summary.director.inference_session_id, null);
  } else {
    assert.equal(summary.director.phase_outcome, 'succeeded');
    assert.notEqual(summary.director.inference_execution, 'not_executed');
    assertProviderWhenTracePresent(summary.director);
    assert.ok(findEvent(events, 'hg/director-accepted') || findEvent(events, 'hg/director-proposed'));
  }

  assert.equal(summary.character.phase_outcome, 'succeeded');
  assert.notEqual(summary.character.inference_execution, 'not_executed');
  assertProviderWhenTracePresent(summary.character);

  if (narratorCompleted) {
    assert.equal(summary.narrator.phase_outcome, 'succeeded');
    assert.notEqual(summary.narrator.inference_execution, 'not_executed');
    assertProviderWhenTracePresent(summary.narrator);
  } else {
    assert.equal(summary.narrator.phase_outcome, 'degraded');
    assertProviderWhenTracePresent(summary.narrator);
    if (summary.narrator.inference_execution === 'not_executed') {
      assert.equal(summary.narrator.inference_trace, null);
    }
  }

  assert.ok(findEvent(events, 'hg/round-started'));
  assert.ok(participation);
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

  const inferenceSessions = [
    summary.director.inference_session_id,
    summary.character.inference_session_id,
    summary.narrator.inference_session_id,
  ].filter(Boolean);
  assert.equal(new Set(inferenceSessions).size, inferenceSessions.length);
  assert.ok(inferenceSessions.length >= 2, 'expected at least character and narrator inference sessions');
  assert.notEqual(result.dsh_scene_session_id, summary.director.inference_session_id);
});

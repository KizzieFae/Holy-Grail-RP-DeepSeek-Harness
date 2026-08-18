import assert from 'node:assert/strict';
import test from 'node:test';

import { createTestSession, fetchSessionState, startDomainApi } from './helpers/domain-api.mjs';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

test('real DeepSeek inference: DSH provider boundary with trace evidence', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 120_000,
}, async (t) => {
  const port = 22765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: { mountDeepSeek: true },
  });

  const result = await phaseExecutors.runCharacterInference({
    domainApi: { baseUrl },
    characterId: 'Alice',
    modelProfile: deepseekInferenceProfile({
      reasoningEffort: 'low',
      maxTokens: 512,
    }),
    prompt: [
      'You are Alice in a quiet room. Respond with ONLY one JSON object, no markdown.',
      'Required keys: move_schema_version (2), beats (array with one action beat),',
      'motivation (goal, tactic, emotional_driver, risk_level),',
      'semantic_evaluation (decision: no_covered_change).',
      'Example action: "glances around the room".',
    ].join(' '),
  });

  const trace = result.inference_trace;
  assert.ok(trace, 'expected inference trace');
  assert.equal(trace.provider, 'deepseek-official');
  assert.equal(trace.model, 'deepseek-v4-flash');
  assert.equal(trace.reasoning_effort, 'low');
  assert.ok(trace.manifest_id, 'expected manifest correlation');
  assert.ok(Array.isArray(trace.contribution_ids));
  assert.ok(
    trace.assistant_text.length > 0 || trace.stream.text_delta_count > 0,
    'expected streamed assistant output',
  );
  assert.equal(result.provider_failure, null);

  if (result.committed) {
    assert.ok(result.domain_commit_id);
    assert.equal(typeof result.continuity_turn_index, 'number');
    const commitEvent = result.scene_events.find((event) => event.type === 'hg/move-committed');
    assert.ok(commitEvent);
  } else {
    const proposed = result.scene_events.find((event) => event.type === 'hg/move-proposed');
    assert.ok(proposed, 'expected move proposal even when validation did not commit');
  }
});

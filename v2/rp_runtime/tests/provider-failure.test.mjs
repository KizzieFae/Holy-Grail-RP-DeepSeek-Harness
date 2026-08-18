import assert from 'node:assert/strict';
import test from 'node:test';

import { createTestSession, fetchSessionState, startDomainApi } from './helpers/domain-api.mjs';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';


test('provider failure: missing credential does not mutate domain state', async (t) => {
  const port = 21765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: {
      mountDeepSeek: true,
      deepseek: { apiKeyEnv: 'HG_TEST_MISSING_DEEPSEEK_KEY' },
    },
  });

  const created = await createTestSession(baseUrl, ['Alice']);
  const before = await fetchSessionState(baseUrl, created.hg_session_id);
  const turnBefore = Number(before.turn_counter ?? 0);

  const result = await phaseExecutors.runCharacterInference({
    domainApi: { baseUrl },
    hgSceneId: created.hg_scene_id,
    characterId: 'Alice',
    modelProfile: deepseekInferenceProfile({ reasoningEffort: 'off' }),
  });

  assert.equal(result.committed, false);
  assert.ok(result.provider_failure, 'expected structured provider failure');
  assert.equal(result.inference_trace?.provider, 'deepseek-official');
  assert.equal(result.domain_commit_id, null);

  const after = await fetchSessionState(baseUrl, created.hg_session_id);
  assert.equal(Number(after.turn_counter ?? 0), turnBefore);

  const failureEvent = result.scene_events.find((event) => event.type === 'hg/inference-failed');
  assert.ok(failureEvent, 'expected hg/inference-failed scene event');
  assert.equal(failureEvent.data.failure?.code, 'MISSING_CREDENTIAL');
});

import assert from 'node:assert/strict';
import test from 'node:test';

import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { runStorytellerCognition } from '../src/lib/storyteller-cognition-substrate.mjs';
import { createTestSession, startDomainApi } from './helpers/domain-api.mjs';

const MISSING_SCHEMA_ORIENTATION = JSON.stringify({
  information_gaps: ['What tensions are active in the scene?'],
});

async function mockRunEphemeralInference({ mockResponses = [], inferenceId = 'inf-mock' }) {
  return {
    failed: false,
    raw: mockResponses[0] ?? MISSING_SCHEMA_ORIENTATION,
    evidenceId: `ev-${inferenceId}`,
    inferenceSessionId: `sess-${inferenceId}`,
    trace: {},
  };
}

test('storyteller orientation parse failure degrades without HTTP 400', async (t) => {
  const host = await startDomainApi(undefined, { t });
  const api = createDomainApiClient(host.baseUrl);
  const session = await createTestSession(host.baseUrl);
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });

  const result = await runStorytellerCognition({
    domainApi: api,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    inferenceId: 'inf-storyteller-parse-failure',
    runEphemeralInference: mockRunEphemeralInference,
    mockOrientationResponse: MISSING_SCHEMA_ORIENTATION,
  });

  assert.equal(result.ok, false);
  assert.equal(result.stage, 'orientation_finalize');
  assert.equal(result.orientationFinalize.accepted, false);
  assert.equal(result.orientationFinalize.reason, 'schema_mismatch');
  assert.equal(result.package, null);
  assert.equal(result.audit?.reason, 'schema_mismatch');
});

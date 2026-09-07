import assert from 'node:assert/strict';
import test from 'node:test';

import { runStorytellerCognition } from '../src/lib/storyteller-cognition-substrate.mjs';
import {
  LIVE_INFERENCE_TRANSPORT_PROMPT,
  LIVE_STORYTELLER_ORIENTATION_PROMPT,
} from '../src/lib/live-inference-prompts.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { startDomainApi, createTestSession } from './helpers/domain-api.mjs';

const STORYTELLER_FORBIDDEN = [
  'hg_storyteller_orientation_v1',
  'information_gaps',
  'storyteller orientation',
  'librarian',
  'next_actor',
  'dialogue',
  'narration',
  'structured_move',
];

function assertTransportOnly(prompt, forbidden) {
  const lower = prompt.toLowerCase();
  assert.match(lower, /json object/);
  assert.ok(!lower.includes('manifest'));
  assert.ok(!lower.includes('inference_instruction'));
  for (const token of forbidden) {
    assert.ok(!lower.includes(token), `transport prompt must not include ${token}`);
  }
}

test('issue 144: storyteller orientation DSH prompt is transport-only', () => {
  assert.equal(LIVE_STORYTELLER_ORIENTATION_PROMPT, LIVE_INFERENCE_TRANSPORT_PROMPT);
  assertTransportOnly(LIVE_STORYTELLER_ORIENTATION_PROMPT, STORYTELLER_FORBIDDEN);
});

const MISSING_SCHEMA_ORIENTATION = JSON.stringify({
  information_gaps: ['What tensions are active in the scene?'],
});

async function mockRunEphemeralInference({ mockResponses = [], inferenceId = 'inf-mock', prompt }) {
  assert.equal(prompt, LIVE_INFERENCE_TRANSPORT_PROMPT);
  return {
    failed: false,
    raw: mockResponses[0] ?? MISSING_SCHEMA_ORIENTATION,
    evidenceId: `ev-${inferenceId}`,
    inferenceSessionId: `sess-${inferenceId}`,
    trace: {},
  };
}

test('issue 144: raw provider output reaches Host finalize without DSH pre-check', async (t) => {
  const host = await startDomainApi(undefined, { t });
  const api = createDomainApiClient(host.baseUrl);
  const session = await createTestSession(host.baseUrl);
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });

  const result = await runStorytellerCognition({
    domainApi: api,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    inferenceId: 'inf-storyteller-144-raw',
    runEphemeralInference: mockRunEphemeralInference,
    mockOrientationResponse: MISSING_SCHEMA_ORIENTATION,
  });

  assert.equal(result.ok, false);
  assert.equal(result.stage, 'orientation_finalize');
  assert.equal(result.orientationFinalize.accepted, false);
  assert.equal(result.orientationFinalize.reason, 'schema_mismatch');
});

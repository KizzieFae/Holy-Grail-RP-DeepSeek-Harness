import assert from 'node:assert/strict';
import test from 'node:test';

import { runStorytellerCognition } from '../src/lib/storyteller-cognition-substrate.mjs';
import {
  LIVE_INFERENCE_TRANSPORT_PROMPT,
  LIVE_STORYTELLER_ASSESSMENT_PROMPT,
} from '../src/lib/live-inference-prompts.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { startDomainApi, createTestSession } from './helpers/domain-api.mjs';

const ASSESSMENT_FORBIDDEN = [
  'hg_storyteller_assessment_v1',
  'observations',
  'progression_opportunities',
  'storyteller assessment',
  'librarian bundle digest',
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

test('issue 146: storyteller assessment DSH prompt is transport-only', () => {
  assert.equal(LIVE_STORYTELLER_ASSESSMENT_PROMPT, LIVE_INFERENCE_TRANSPORT_PROMPT);
  assertTransportOnly(LIVE_STORYTELLER_ASSESSMENT_PROMPT, ASSESSMENT_FORBIDDEN);
});

const VALID_ORIENTATION = JSON.stringify({
  schema: 'hg_storyteller_orientation_v1',
  information_gaps: ['What tensions are active in the scene?'],
});

const MISSING_SCHEMA_ASSESSMENT = JSON.stringify({
  observations: [{ text: 'Trust fracture is narratively central.' }],
});

async function mockRunEphemeralInference({
  inferenceId = 'inf-mock',
  prompt,
  evidenceContext,
}) {
  const kind = evidenceContext?.inferenceKind;
  if (kind === 'storyteller_orientation' || kind === 'storyteller_assessment') {
    assert.equal(prompt, LIVE_INFERENCE_TRANSPORT_PROMPT);
  }
  let raw = VALID_ORIENTATION;
  if (kind === 'storyteller_assessment') {
    raw = MISSING_SCHEMA_ASSESSMENT;
  }
  if (kind === 'librarian_mediation') {
    raw = JSON.stringify({
      schema: 'hg_librarian_mediation_result_v1',
      selected_source_ids: [],
    });
  }
  return {
    failed: false,
    raw,
    evidenceId: `ev-${inferenceId}`,
    inferenceSessionId: `sess-${inferenceId}`,
    trace: {},
  };
}

test('issue 146: raw assessment output reaches Host finalize without DSH pre-check', async (t) => {
  const host = await startDomainApi(undefined, { t });
  const api = createDomainApiClient(host.baseUrl);
  const session = await createTestSession(host.baseUrl);
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });

  const result = await runStorytellerCognition({
    domainApi: api,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    inferenceId: 'inf-storyteller-146-raw',
    runEphemeralInference: mockRunEphemeralInference,
    mockOrientationResponse: VALID_ORIENTATION,
    mockAssessmentResponse: MISSING_SCHEMA_ASSESSMENT,
    allowDeterministicFallback: true,
  });

  assert.equal(result.ok, false);
  assert.equal(result.stage, 'assessment_finalize');
  assert.equal(result.assessmentFinalize.accepted, false);
  assert.equal(result.assessmentFinalize.reason, 'schema_mismatch');
});

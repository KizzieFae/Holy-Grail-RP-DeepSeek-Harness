import assert from 'node:assert/strict';
import test from 'node:test';

import {
  PLAYER_DECOMPOSITION_FAILURE_CLASS_CONTEXT_PREPARE,
  PLAYER_DECOMPOSITION_RETRY_HEADER,
  buildPlayerDecompositionUserPrompt,
  runPlayerDecompositionPhase,
} from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { mockInferenceProfile } from '../src/lib/inference-profile.mjs';

const VALID_DECOMPOSITION = JSON.stringify({
  perceptual_visibility: {
    units: [
      {
        unit_id: 'u1',
        kind: 'speech',
        text: 'Hello.',
        recipients: { scope: 'public', characters: [], roles: [] },
        source_provenance: { segment_ids: ['s1'], order_index: 0 },
      },
    ],
  },
  source_accounting: {
    segments: [
      {
        segment_id: 's1',
        char_start: 0,
        char_end: 6,
        disposition: 'projects',
        unit_ids: ['u1'],
      },
    ],
  },
});

const CANONICAL_OUTPUT_MARKERS = [
  'OUTPUT FORMAT — return ONLY valid JSON',
  '"perceptual_visibility"',
  '"source_accounting"',
];

function createTrackingApi() {
  const prepareCalls = [];
  const manifest = {
    manifest_id: 'manifest-player-decomposition-test',
    inference_id: 'player-decomposition-test',
    hg_scene_id: 'hg-session-test',
    hg_round_id: 'hg-round-test',
    role: 'player_decomposition',
    character_id: null,
    turn_index: 0,
    attempt_index: 0,
    contributions: [
      {
        contribution_id: 'manifest-player-decomposition-test-instruction',
        source_kind: 'inference_instruction',
        authority_class: 'derived',
        priority: 30,
        content: `Task framing\n${CANONICAL_OUTPUT_MARKERS.join('\n')}`,
      },
    ],
  };
  return {
    prepareCalls,
    api: {
      preparePlayerDecompositionContext(body) {
        prepareCalls.push(body);
        return Promise.resolve({
          ...manifest,
          manifest_id: `manifest-player-decomposition-${body.inference_id}`,
          inference_id: body.inference_id,
          attempt_index: body.attempt_index ?? 0,
          contributions: [
            {
              ...manifest.contributions[0],
              contribution_id: `manifest-player-decomposition-${body.inference_id}-instruction`,
              content: `Task framing\n${CANONICAL_OUTPUT_MARKERS.join('\n')}`,
            },
          ],
        });
      },
    },
  };
}

function createInferenceRecorder(responses) {
  const calls = [];
  let index = 0;
  async function runEphemeralInference(params) {
    calls.push(params);
    const raw = responses[index] ?? responses[responses.length - 1];
    index += 1;
    return {
      raw,
      failed: false,
      evidenceId: `evidence-${calls.length}`,
      inferenceSessionId: `session-${calls.length}`,
      trace: {},
    };
  }
  return { runEphemeralInference, calls };
}

test('player decomposition phase wires canonical contract manifest into inference', async () => {
  const { api, prepareCalls } = createTrackingApi();
  const { runEphemeralInference, calls } = createInferenceRecorder([VALID_DECOMPOSITION]);
  const playerContent = 'Hello.';

  const result = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: 'hg-session-test',
    hgSceneId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    inferenceId: 'player-decomposition-test',
    playerContent,
    modelProfile: mockInferenceProfile(),
  });

  assert.equal(prepareCalls.length, 1);
  assert.equal(prepareCalls[0].hg_session_id, 'hg-session-test');
  assert.equal(prepareCalls[0].inference_id, 'player-decomposition-test');

  assert.equal(calls.length, 1);
  const instruction = calls[0].manifest.contributions.find(
    (item) => item.source_kind === 'inference_instruction',
  );
  assert.ok(instruction);
  for (const marker of CANONICAL_OUTPUT_MARKERS) {
    assert.match(instruction.content, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.equal(
    instruction.contribution_id,
    'manifest-player-decomposition-player-decomposition-test-instruction',
  );
  assert.match(calls[0].prompt, /PLAYER SOURCE:\nHello\./);
  assert.ok(!instruction.content.includes('Hello.'));
  assert.equal(result.playerDecomposition.perceptual_visibility.units.length, 1);
});

test('player decomposition keeps player source in user prompt only', () => {
  const prompt = buildPlayerDecompositionUserPrompt('She waved and smiled.');
  assert.match(prompt, /PLAYER SOURCE:\nShe waved and smiled\./);
  assert.doesNotMatch(prompt, /OUTPUT FORMAT/);
});

test('player decomposition retry adds bounded failure feedback without replaying assistant output', async () => {
  const { api } = createTrackingApi();
  const prose = 'Here is a markdown decomposition of the turn.';
  const { runEphemeralInference, calls } = createInferenceRecorder([prose, VALID_DECOMPOSITION]);

  const result = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: 'hg-session-test',
    hgSceneId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    inferenceId: 'player-decomposition-retry',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });

  assert.equal(calls.length, 2);
  assert.match(calls[0].prompt, /PLAYER SOURCE:\nHello\./);
  assert.doesNotMatch(calls[0].prompt, new RegExp(PLAYER_DECOMPOSITION_RETRY_HEADER));
  assert.match(calls[1].prompt, new RegExp(PLAYER_DECOMPOSITION_RETRY_HEADER));
  assert.match(calls[1].prompt, /not json object/);
  assert.ok(!calls[1].prompt.includes(prose));
  assert.equal(calls[1].evidenceContext.attemptIndex, 1);
  assert.equal(calls[1].evidenceContext.priorAttemptId, 'evidence-1');
  assert.equal(result.playerDecomposition.perceptual_visibility.units.length, 1);
});

test('player decomposition context prepare failure is attributed before inference', async () => {
  const prepareCalls = [];
  const api = {
    preparePlayerDecompositionContext(body) {
      prepareCalls.push(body);
      return Promise.reject(new Error('domain host unavailable'));
    },
  };
  const { runEphemeralInference, calls } = createInferenceRecorder([VALID_DECOMPOSITION]);

  const result = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: 'hg-session-test',
    hgSceneId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    inferenceId: 'player-decomposition-prepare-fail',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });

  assert.equal(prepareCalls.length, 1);
  assert.equal(calls.length, 0);
  assert.equal(
    result.playerDecomposition.failure_class,
    PLAYER_DECOMPOSITION_FAILURE_CLASS_CONTEXT_PREPARE,
  );
  assert.equal(result.playerDecomposition.reason, 'domain host unavailable');
  assert.equal(result.playerDecomposition.generation.attempt_index, 0);
  assert.equal(result.evidenceId, null);
  assert.equal(result.playerDecomposition.perceptual_visibility, undefined);
});

test('player decomposition context prepare failure on retry attempt stays attributed', async () => {
  const { api, prepareCalls } = createTrackingApi();
  const prose = 'Still prose.';
  const { runEphemeralInference, calls } = createInferenceRecorder([prose]);
  const originalPrepare = api.preparePlayerDecompositionContext.bind(api);
  let prepareAttempts = 0;
  api.preparePlayerDecompositionContext = async (body) => {
    prepareAttempts += 1;
    if (body.attempt_index === 1) {
      throw new Error('domain host unavailable on retry');
    }
    return originalPrepare(body);
  };

  const result = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: 'hg-session-test',
    hgSceneId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    inferenceId: 'player-decomposition-prepare-retry-fail',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });

  assert.equal(prepareAttempts, 2);
  assert.equal(prepareCalls.length, 1);
  assert.equal(calls.length, 1);
  assert.equal(
    result.playerDecomposition.failure_class,
    PLAYER_DECOMPOSITION_FAILURE_CLASS_CONTEXT_PREPARE,
  );
  assert.equal(result.playerDecomposition.reason, 'domain host unavailable on retry');
  assert.equal(result.playerDecomposition.generation.attempt_index, 1);
  assert.equal(result.evidenceId, null);
});

test('player decomposition malformed output fails closed after two attempts', async () => {
  const { api } = createTrackingApi();
  const prose = 'Still prose.';
  const { runEphemeralInference, calls } = createInferenceRecorder([prose, prose]);

  const result = await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: 'hg-session-test',
    hgSceneId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    inferenceId: 'player-decomposition-fail',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });

  assert.equal(calls.length, 2);
  assert.equal(result.playerDecomposition.failure_class, 'malformed_output');
  assert.equal(result.playerDecomposition.reason, 'not json object');
  assert.equal(result.playerDecomposition.perceptual_visibility, undefined);
});

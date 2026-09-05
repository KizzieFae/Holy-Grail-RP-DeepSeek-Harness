import assert from 'node:assert/strict';
import test from 'node:test';

import {
  PLAYER_DECOMPOSITION_FAILURE_CLASS_CONTEXT_PREPARE,
  PLAYER_DECOMPOSITION_RETRY_HEADER,
  buildPlayerDecompositionUserPrompt,
  runPlayerDecompositionPhase,
} from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import { mockInferenceProfile } from '../src/lib/inference-profile.mjs';

const VALID_SIR = JSON.stringify({
  semantic_decomposition: {
    units: [
      {
        kind: 'speech',
        text: 'Hello.',
        recipients: { scope: 'public', characters: [], roles: [] },
      },
    ],
  },
});

const CANONICAL_OUTPUT_MARKERS = [
  'OUTPUT FORMAT — return ONLY valid JSON',
  '"semantic_decomposition"',
  'verbatim semantic excerpt',
];

const CANONICAL_DECOMPOSITION = {
  perceptual_visibility: {
    units: [
      {
        unit_id: 'u1',
        kind: 'speech',
        text: 'Hello.',
        recipients: { scope: 'public', characters: [], roles: [] },
        source_provenance: { segment_ids: ['s1'], order_index: 0 },
        source: 'player_decomposition',
      },
    ],
  },
  source_accounting: {
    source_length: 6,
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
  generation: {},
};

function createTrackingApi({ normalizeResult } = {}) {
  const prepareCalls = [];
  const normalizeCalls = [];
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
    normalizeCalls,
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
      normalizePlayerDecomposition(body) {
        normalizeCalls.push(body);
        if (normalizeResult) {
          return Promise.resolve(normalizeResult(body));
        }
        return Promise.resolve({
          accepted: true,
          player_decomposition: {
            ...CANONICAL_DECOMPOSITION,
            generation: body.generation ?? {},
          },
          normalization_audit: { version: 1, ambiguity_class: 'unique' },
          validation_audit: { accepted: true },
          retry_eligible: false,
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

test('player decomposition phase wires semantic contract manifest into inference', async () => {
  const { api, prepareCalls, normalizeCalls } = createTrackingApi();
  const { runEphemeralInference, calls } = createInferenceRecorder([VALID_SIR]);
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
  assert.equal(normalizeCalls.length, 1);
  assert.equal(normalizeCalls[0].semantic_decomposition.units.length, 1);
  assert.equal(calls.length, 1);
  const instruction = calls[0].manifest.contributions.find(
    (item) => item.source_kind === 'inference_instruction',
  );
  assert.ok(instruction);
  for (const marker of CANONICAL_OUTPUT_MARKERS) {
    assert.match(instruction.content, new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
  assert.equal(result.playerDecomposition.perceptual_visibility.units.length, 1);
});

test('player decomposition keeps player source in user prompt only', () => {
  const prompt = buildPlayerDecompositionUserPrompt('She waved and smiled.');
  assert.match(prompt, /PLAYER SOURCE:\nShe waved and smiled\./);
  assert.doesNotMatch(prompt, /OUTPUT FORMAT/);
});

test('player decomposition retry adds bounded failure feedback without replaying assistant output', async () => {
  const { api } = createTrackingApi({
    normalizeResult: (body) => (
      body.attempt_index === 0
        ? {
          accepted: false,
          failure_class: 'sir_malformed',
          reason: 'not json object',
          retry_eligible: true,
          normalization_audit: {},
        }
        : {
          accepted: true,
          player_decomposition: {
            ...CANONICAL_DECOMPOSITION,
            generation: body.generation ?? {},
          },
          normalization_audit: {},
          validation_audit: { accepted: true },
          retry_eligible: false,
        }
    ),
  });
  const prose = 'Here is a markdown decomposition of the turn.';
  const { runEphemeralInference, calls } = createInferenceRecorder([prose, VALID_SIR]);

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
  assert.match(calls[1].prompt, new RegExp(PLAYER_DECOMPOSITION_RETRY_HEADER));
  assert.match(calls[1].prompt, /sir_malformed/);
  assert.ok(!calls[1].prompt.includes(prose));
  assert.equal(result.playerDecomposition.perceptual_visibility.units.length, 1);
});

test('player decomposition context prepare failure is attributed before inference', async () => {
  const prepareCalls = [];
  const api = {
    preparePlayerDecompositionContext(body) {
      prepareCalls.push(body);
      return Promise.reject(new Error('domain host unavailable'));
    },
    normalizePlayerDecomposition() {
      throw new Error('normalize should not be called');
    },
  };
  const { runEphemeralInference, calls } = createInferenceRecorder([VALID_SIR]);

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
  assert.equal(result.playerDecomposition.failure_class, 'sir_malformed');
  assert.equal(result.playerDecomposition.perceptual_visibility, undefined);
});

test('player decomposition delegates normalization to domain host', async () => {
  const { api, normalizeCalls } = createTrackingApi();
  const { runEphemeralInference } = createInferenceRecorder([VALID_SIR]);

  await runPlayerDecompositionPhase({
    api,
    runEphemeralInference,
    hgSessionId: 'hg-session-test',
    hgSceneId: 'hg-session-test',
    hgRoundId: 'hg-round-test',
    inferenceId: 'player-decomposition-normalize',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });

  assert.equal(normalizeCalls.length, 1);
  assert.equal(normalizeCalls[0].content, 'Hello.');
  assert.ok(normalizeCalls[0].semantic_decomposition);
});

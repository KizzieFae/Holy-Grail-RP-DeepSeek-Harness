import assert from 'node:assert/strict';
import test from 'node:test';

import { parsePlayerVisibilityTriageEnvelope } from '../src/lib/perceptual-visibility-parse.mjs';
import {
  buildUniformProjectionDecomposition,
  UNIFORM_PROJECTION_KIND,
} from '../src/lib/player-uniform-projection.mjs';
import {
  isAffirmativeUniformProjectionSafe,
  runPlayerVisibilityTriagePhase,
} from '../src/plugins/hg-phase-executors/player-visibility-triage-phase.mjs';
import { mockInferenceProfile } from '../src/lib/inference-profile.mjs';

test('parsePlayerVisibilityTriageEnvelope accepts affirmative safety', () => {
  const parsed = parsePlayerVisibilityTriageEnvelope(
    JSON.stringify({ uniform_projection_safe: true, reason: 'affirmative_uniform_present' }),
  );
  assert.equal(parsed.parseError, null);
  assert.equal(parsed.uniformProjectionSafe, true);
  assert.equal(isAffirmativeUniformProjectionSafe(parsed), true);
});

test('parsePlayerVisibilityTriageEnvelope rejects malformed output', () => {
  const parsed = parsePlayerVisibilityTriageEnvelope('not-json');
  assert.ok(parsed.parseError);
  assert.equal(parsed.uniformProjectionSafe, null);
});

test('parsePlayerVisibilityTriageEnvelope rejects missing boolean', () => {
  const parsed = parsePlayerVisibilityTriageEnvelope(JSON.stringify({ reason: 'uncertain' }));
  assert.ok(parsed.parseError);
});

test('buildUniformProjectionDecomposition matches checker contract', () => {
  const content = 'The player nods.';
  const decomposition = buildUniformProjectionDecomposition(content, {
    checkerAudit: { uniform_projection_safe: true, reason: 'affirmative_uniform_present' },
    inferenceId: 'checker-test',
  });
  assert.equal(decomposition.generation.derivation_profile, 'uniform_projection');
  assert.equal(decomposition.generation.semantic_decomposition, 'not_performed');
  assert.equal(decomposition.perceptual_visibility.units[0].kind, UNIFORM_PROJECTION_KIND);
  assert.equal(decomposition.perceptual_visibility.units[0].recipients.scope, 'present');
});

test('checker failure routes to full_pvr without uniform synthesis', async () => {
  const result = await runPlayerVisibilityTriagePhase({
    api: {
      preparePlayerVisibilityTriageContext: async () => {
        throw new Error('context prepare failed');
      },
    },
    runEphemeralInference: async () => ({ failed: true, failure: { message: 'unavailable' } }),
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-1',
    inferenceId: 'triage-test',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'full_pvr');
  assert.equal(result.checkerResult.uniform_projection_safe, false);
  assert.equal(result.playerDecomposition, undefined);
});

test('malformed checker output routes to full_pvr', async () => {
  const result = await runPlayerVisibilityTriagePhase({
    api: {
      preparePlayerVisibilityTriageContext: async () => ({ manifest_id: 'm1', contributions: [] }),
    },
    runEphemeralInference: async () => ({ failed: false, raw: 'not-json', evidenceId: 'e1' }),
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-1',
    inferenceId: 'triage-test',
    playerContent: 'Hello.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'full_pvr');
});

test('affirmative checker routes to uniform synthesis', async () => {
  const result = await runPlayerVisibilityTriagePhase({
    api: {
      preparePlayerVisibilityTriageContext: async () => ({ manifest_id: 'm1', contributions: [] }),
    },
    runEphemeralInference: async () => ({
      failed: false,
      raw: JSON.stringify({ uniform_projection_safe: true, reason: 'affirmative_uniform_present' }),
      evidenceId: 'e1',
    }),
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-1',
    inferenceId: 'triage-test',
    playerContent: 'The player waves.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'uniform_projection');
  assert.ok(result.playerDecomposition);
  assert.equal(
    result.playerDecomposition.perceptual_visibility.units[0].kind,
    UNIFORM_PROJECTION_KIND,
  );
});

test('negative checker routes to full_pvr', async () => {
  const result = await runPlayerVisibilityTriagePhase({
    api: {
      preparePlayerVisibilityTriageContext: async () => ({ manifest_id: 'm1', contributions: [] }),
    },
    runEphemeralInference: async () => ({
      failed: false,
      raw: JSON.stringify({ uniform_projection_safe: false, reason: 'requires_semantic_decomposition' }),
      evidenceId: 'e1',
    }),
    trace: { emit: () => {} },
    sceneAgent: { session: {} },
    hgSessionId: 'hg-test',
    hgSceneId: 'hg-test',
    hgRoundId: 'round-1',
    inferenceId: 'triage-test',
    playerContent: 'Secret thought.',
    modelProfile: mockInferenceProfile(),
  });
  assert.equal(result.route, 'full_pvr');
  assert.equal(result.playerDecomposition, undefined);
});

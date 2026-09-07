import assert from 'node:assert/strict';
import test from 'node:test';

import {
  resolveManifestInferenceKind,
  validateBridgeManifest,
} from '../src/lib/manifest-validation.mjs';

test('validateBridgeManifest: PromptContributionManifest missing inference_kind rejects even with caller fallback', () => {
  const manifest = {
    manifest_id: 'manifest-missing-kind',
    inference_id: 'inf-1',
    contributions: [
      {
        contribution_id: 'c-1',
        source_kind: 'inference_instruction',
        content: 'x',
      },
    ],
  };

  assert.throws(
    () => validateBridgeManifest({ manifest, inferenceKind: 'narrator_presentation' }),
    /missing required inference_kind/,
  );
});

test('validateBridgeManifest: unknown inference_kind rejects', () => {
  const manifest = {
    manifest_id: 'manifest-unknown-kind',
    inference_id: 'inf-1',
    inference_kind: 'not_a_real_inference',
    contributions: [
      {
        contribution_id: 'c-1',
        source_kind: 'inference_instruction',
        content: 'x',
      },
    ],
  };

  assert.throws(
    () => validateBridgeManifest({ manifest }),
    /unknown inference_kind/,
  );
});

test('validateBridgeManifest: inference_kind mismatch rejects', () => {
  const manifest = {
    manifest_id: 'manifest-mismatch',
    inference_id: 'inf-1',
    inference_kind: 'narrator_presentation',
    contributions: [
      {
        contribution_id: 'c-1',
        source_kind: 'inference_instruction',
        content: 'x',
      },
    ],
  };

  assert.throws(
    () => validateBridgeManifest({ manifest, inferenceKind: 'director_turn' }),
    /inference_kind mismatch/,
  );
});

test('validateBridgeManifest: non-manifest package accepts explicit caller inference kind', () => {
  const resolved = resolveManifestInferenceKind(
    {
      contributions: [
        {
          contribution_id: 'c-1',
          source_kind: 'inference_instruction',
        },
      ],
    },
    'player_visibility_triage',
  );
  assert.equal(resolved, 'player_visibility_triage');
});

test('validateBridgeManifest: provenance.visibility does not authorize projection', () => {
  const manifest = {
    manifest_id: 'manifest-visibility',
    inference_id: 'inf-1',
    inference_kind: 'narrator_presentation',
    contributions: [
      {
        contribution_id: 'bad-env-cog',
        source_kind: 'narrator_environment_cognition',
        provenance: { visibility: 'model' },
        content: '{}',
      },
    ],
  };

  assert.throws(
    () => validateBridgeManifest({ manifest }),
    /model-context package rejected/,
  );
});

test('validateBridgeManifest: infrastructure_provider_probe accepts empty non-manifest package', () => {
  const resolved = validateBridgeManifest({
    manifest: { contributions: [] },
    inferenceKind: 'infrastructure_provider_probe',
  });
  assert.equal(resolved, 'infrastructure_provider_probe');
});

test('validateBridgeManifest: infrastructure_provider_probe rejects any contribution', () => {
  assert.throws(
    () => validateBridgeManifest({
      manifest: {
        contributions: [{
          contribution_id: 'c-1',
          source_kind: 'inference_instruction',
          content: 'x',
        }],
      },
      inferenceKind: 'infrastructure_provider_probe',
    }),
    /disallowed source_kind/,
  );
});

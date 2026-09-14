import assert from 'node:assert/strict';
import test from 'node:test';

import {
  assertValidModelContextPackage,
} from '../src/lib/manifest-projection-policy.mjs';
import { validateBridgeManifest } from '../src/lib/manifest-validation.mjs';

const CHARACTER_INFERENCE_KINDS = [
  'character_orientation',
  'character_turn',
  'character_semantic_evaluation',
];

function inventoryContribution(contributionId = 'c-inventory') {
  return {
    contribution_id: contributionId,
    source_kind: 'authoritative_perceptual_inventory',
    authority_class: 'authoritative',
    priority: 17,
    content: 'AUTHORITATIVE PERCEPTUAL INVENTORY (test)',
    knowledge_ids: [],
    provenance: {},
  };
}

function instructionContribution(contributionId = 'c-instruction') {
  return {
    contribution_id: contributionId,
    source_kind: 'inference_instruction',
    authority_class: 'derived',
    priority: 100,
    content: 'instruction',
    knowledge_ids: [],
    provenance: {},
  };
}

for (const inferenceKind of CHARACTER_INFERENCE_KINDS) {
  test(`assertValidModelContextPackage: ${inferenceKind} accepts authoritative_perceptual_inventory`, () => {
    assertValidModelContextPackage(inferenceKind, [
      inventoryContribution(`${inferenceKind}-inventory`),
      instructionContribution(`${inferenceKind}-instruction`),
    ]);
  });
}

test('assertValidModelContextPackage: character_orientation rejects disallowed source_kind', () => {
  assert.throws(
    () => assertValidModelContextPackage('character_orientation', [{
      contribution_id: 'c-bad',
      source_kind: 'narrator_environment_cognition',
      content: '{}',
    }]),
    /disallowed source_kind 'narrator_environment_cognition'/,
  );
});

test('validateBridgeManifest: director_turn rejects authoritative_perceptual_inventory', () => {
  assert.throws(
    () => validateBridgeManifest({
      manifest: {
        manifest_id: 'manifest-director-boundary',
        inference_id: 'inf-director',
        inference_kind: 'director_turn',
        contributions: [
          instructionContribution('c-director-instruction'),
          inventoryContribution('c-director-inventory'),
        ],
      },
    }),
    /disallowed source_kind 'authoritative_perceptual_inventory'/,
  );
});

test('validateBridgeManifest: character_orientation Host manifest with inventory passes bridge validation', () => {
  const resolved = validateBridgeManifest({
    manifest: {
      manifest_id: 'manifest-char-orient',
      inference_id: 'inf-orient',
      inference_kind: 'character_orientation',
      contributions: [
        inventoryContribution('c-orient-inventory'),
        instructionContribution('c-orient-instruction'),
      ],
    },
  });
  assert.equal(resolved, 'character_orientation');
});

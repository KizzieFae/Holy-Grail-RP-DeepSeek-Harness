import assert from 'node:assert/strict';
import test from 'node:test';

import {
  bridgeManifestFromHostPrepare,
  normalizeBridgeContributions,
} from '../src/lib/bridge-manifest.mjs';

test('bridgeManifestFromHostPrepare preserves authoritative Host metadata and contributions', () => {
  const contributions = [
    {
      contribution_id: 'c-1',
      source_kind: 'inference_instruction',
      authority_class: 'derived',
      priority: 1,
      content: 'x',
      knowledge_ids: [],
      provenance: {},
    },
  ];
  const manifest = bridgeManifestFromHostPrepare(
    {
      manifest_id: 'manifest-host',
      inference_id: 'inf-1',
      inference_kind: 'character_orientation',
      hg_scene_id: 'scene-1',
      hg_round_id: 'round-1',
      role: 'character',
      character_id: 'Alice',
      turn_index: 2,
      attempt_index: 0,
      contributions: [{ contribution_id: 'ignored' }],
      schema: 'hg_character_orientation_v1',
    },
    contributions,
  );

  assert.equal(manifest.manifest_id, 'manifest-host');
  assert.equal(manifest.inference_kind, 'character_orientation');
  assert.equal(manifest.inference_id, 'inf-1');
  assert.equal(manifest.hg_scene_id, 'scene-1');
  assert.equal(manifest.hg_round_id, 'round-1');
  assert.equal(manifest.role, 'character');
  assert.equal(manifest.character_id, 'Alice');
  assert.equal(manifest.turn_index, 2);
  assert.equal(manifest.attempt_index, 0);
  assert.deepEqual(manifest.contributions, contributions);
  assert.equal(manifest.schema, undefined);
});

test('bridgeManifestFromHostPrepare unwraps nested Host manifest objects', () => {
  const manifest = bridgeManifestFromHostPrepare(
    {
      manifest: {
        manifest_id: 'manifest-nested',
        inference_kind: 'narrator_environment_cognition',
        inference_id: 'inf-nar',
        contributions: [{ contribution_id: 'c-nested' }],
      },
    },
    undefined,
  );
  assert.equal(manifest.manifest_id, 'manifest-nested');
  assert.equal(manifest.inference_kind, 'narrator_environment_cognition');
  assert.deepEqual(manifest.contributions, [{ contribution_id: 'c-nested' }]);
});

test('normalizeBridgeContributions preserves order', () => {
  const normalized = normalizeBridgeContributions([
    { contribution_id: 'a', source_kind: 'scene_state', priority: 2 },
    { contribution_id: 'b', source_kind: 'inference_instruction', priority: 1 },
  ]);
  assert.deepEqual(normalized.map((c) => c.contribution_id), ['a', 'b']);
});

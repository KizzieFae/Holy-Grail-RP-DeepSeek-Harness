import assert from 'node:assert/strict';
import test from 'node:test';

import {
  appendEffectiveConfigurationEpoch,
  buildEffectiveConfigurationSnapshot,
  canonicalJsonString,
  captureBuildProvenance,
  computeEffectiveConfigurationFingerprint,
  createEffectiveConfigurationEpoch,
  sha256CanonicalFingerprint,
} from '../src/lib/runtime-configuration-provenance.mjs';

test('effective configuration fingerprint is stable for identical resolved config', () => {
  const settings = { inferenceMode: 'mock', roleRouting: 'simple' };
  const left = createEffectiveConfigurationEpoch({ settings, options: { inferenceMode: 'mock' } });
  const right = createEffectiveConfigurationEpoch({ settings, options: { inferenceMode: 'mock' } });
  assert.equal(left.effective_configuration_fingerprint, right.effective_configuration_fingerprint);
});

test('effective configuration fingerprint changes for meaningful config change', () => {
  const mock = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'mock' },
    options: { inferenceMode: 'mock' },
  });
  const live = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'live', model: 'deepseek-chat' },
    options: { inferenceMode: 'live' },
  });
  assert.notEqual(mock.effective_configuration_fingerprint, live.effective_configuration_fingerprint);
});

test('canonical JSON ignores key ordering', () => {
  const left = sha256CanonicalFingerprint({ b: 1, a: { z: 2, y: 3 } });
  const right = sha256CanonicalFingerprint({ a: { y: 3, z: 2 }, b: 1 });
  assert.equal(left, right);
});

test('build provenance excludes secrets and captures descriptive metadata', () => {
  const provenance = captureBuildProvenance({
    ...process.env,
    DEEPSEEK_API_KEY: 'secret-value',
    HG_REPO_COMMIT_SHA: 'abc123',
  });
  assert.equal(provenance.schema, 'hg_runtime_build_provenance_v1');
  assert.equal(provenance.repository_commit_sha, 'abc123');
  assert.equal(provenance.commit_sha_source, 'env');
  assert.ok(provenance.captured_at);
  assert.ok(!JSON.stringify(provenance).includes('secret-value'));
});

test('configuration epochs append only on fingerprint change', () => {
  const epochA = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'mock' },
    options: { inferenceMode: 'mock' },
    effectiveFrom: 'session_open',
    epochId: 'epoch-a',
  });
  let config = appendEffectiveConfigurationEpoch(null, epochA);
  config = appendEffectiveConfigurationEpoch(config, {
    ...epochA,
    epoch_id: 'epoch-a-dup',
    effective_from: 'round_options_override',
  });
  assert.equal(config.epochs.length, 1);

  const epochB = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'live', model: 'deepseek-reasoner' },
    options: { inferenceMode: 'live' },
    effectiveFrom: 'settings_update',
    epochId: 'epoch-b',
  });
  config = appendEffectiveConfigurationEpoch(config, epochB);
  assert.equal(config.epochs.length, 2);
  assert.equal(config.current_epoch_id, 'epoch-b');
});

test('partial snapshot records unavailable fields explicitly', () => {
  const snapshot = buildEffectiveConfigurationSnapshot({}, { inferenceMode: 'live' });
  assert.ok(['complete', 'partial'].includes(snapshot.capture_status));
  assert.ok(Array.isArray(snapshot.unavailable_fields));
  const fingerprint = computeEffectiveConfigurationFingerprint(snapshot);
  assert.match(fingerprint, /^[a-f0-9]{64}$/);
  assert.equal(canonicalJsonString({ a: 1 }), '{"a":1}');
});

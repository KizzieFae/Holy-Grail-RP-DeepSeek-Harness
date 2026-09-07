import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  PRIMARY_RUNTIME_CATALOG,
  PRIMARY_RUNTIME_CALL_IDS,
} from '../src/application/llm-call-catalog.mjs';
import { resolveCatalogApplicationTokenQuota } from '../src/application/llm-call-catalog-policy.mjs';
import { generateLlmCallCatalog } from '../scripts/generate-llm-call-catalog.mjs';
import { INFERENCE_KINDS } from '../src/lib/manifest-projection-policy.mjs';

const srcRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'src');
const repoRoot = path.resolve(srcRoot, '..', '..', '..');

test('llm call catalog: primary runtime row count is 25', () => {
  assert.equal(PRIMARY_RUNTIME_CATALOG.length, 25);
  assert.equal(new Set(PRIMARY_RUNTIME_CALL_IDS).size, 25);
});

test('llm call catalog: production kinds are subset of INFERENCE_KINDS', () => {
  for (const entry of PRIMARY_RUNTIME_CATALOG) {
    assert.ok(
      INFERENCE_KINDS.includes(entry.canonical_inference_kind),
      `${entry.call_id} kind missing from INFERENCE_KINDS`,
    );
    const modulePath = path.join(srcRoot, entry.owner_module);
    assert.ok(fs.existsSync(modulePath), `${entry.call_id} owner module missing: ${entry.owner_module}`);
    const source = fs.readFileSync(modulePath, 'utf8');
    assert.match(source, /runEphemeralInference/, `${entry.call_id} owner must invoke runEphemeralInference`);
  }
});

test('llm call catalog: quota resolution succeeds for all primary rows', () => {
  for (const entry of PRIMARY_RUNTIME_CATALOG) {
    const quota = resolveCatalogApplicationTokenQuota(entry, {}, {});
    assert.ok(
      quota === 'UNCAPPED' || Number.isFinite(quota),
      `${entry.call_id} quota unresolved`,
    );
  }
});

test('llm call catalog: generated document is deterministic for fixed empirical input', () => {
  const first = generateLlmCallCatalog({
    generatedAt: '2026-09-07T00:00:00.000Z',
    repositoryAnchor: 'test-anchor',
    empiricalByCall: {},
  });
  const second = generateLlmCallCatalog({
    generatedAt: '2026-09-07T00:00:00.000Z',
    repositoryAnchor: 'test-anchor',
    empiricalByCall: {},
  });
  assert.deepEqual(first, second);
  assert.equal(first.primary_runtime.length, 25);
  assert.equal(first.harness_annex.length, 2);
});

test('llm call catalog: committed docs file matches generator when present', () => {
  const generated = generateLlmCallCatalog();
  const docPath = path.join(repoRoot, 'docs', 'llm-call-catalog.json');
  if (!fs.existsSync(docPath)) {
    assert.fail('docs/llm-call-catalog.json missing — run generate-llm-call-catalog.mjs');
  }
  const committed = JSON.parse(fs.readFileSync(docPath, 'utf8'));
  assert.equal(committed.primary_runtime.length, generated.primary_runtime.length);
  for (let i = 0; i < generated.primary_runtime.length; i += 1) {
    const gen = generated.primary_runtime[i];
    const com = committed.primary_runtime[i];
    assert.equal(com.call_id, gen.call_id);
    assert.equal(com.application_token_quota, gen.application_token_quota);
    assert.equal(com.reasoning_policy, gen.reasoning_policy);
  }
});

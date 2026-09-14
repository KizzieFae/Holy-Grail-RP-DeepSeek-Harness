/**
 * Cross-runtime manifest policy parity (#134, #206).
 * Mirrors v2/domain/tests/test_manifest_policy_parity.py in the RP runtime npm test suite
 * so one-sided Python/Node policy edits fail normal `npm test` validation.
 */

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import {
  ALLOWED_SOURCE_KINDS,
  resolveInferenceKind,
} from '../src/lib/manifest-projection-policy.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '../../..');
const EXPORT_SCRIPT = path.join(REPO_ROOT, 'v2/rp_runtime/scripts/export-manifest-policy.mjs');
const PYTHON_EXPORT = `
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path('v2').resolve()))
from domain_api.manifest_projection_policy import ALLOWED_SOURCE_KINDS, INFERENCE_KINDS
payload = {
    "inference_kinds": sorted(INFERENCE_KINDS),
    "allowed_source_kinds": {
        kind: sorted(allowed) for kind, allowed in ALLOWED_SOURCE_KINDS.items()
    },
    "aliases": {
        "director_decision": "director_turn",
        "character_move": "character_turn",
    },
}
print(json.dumps(payload))
`;

function exportJavaScriptPolicy() {
  const policy = {};
  for (const [kind, allowed] of Object.entries(ALLOWED_SOURCE_KINDS)) {
    policy[kind] = [...allowed].sort();
  }
  return {
    inference_kinds: Object.keys(ALLOWED_SOURCE_KINDS).sort(),
    allowed_source_kinds: policy,
    aliases: {
      director_decision: resolveInferenceKind('director_decision'),
      character_move: resolveInferenceKind('character_move'),
    },
  };
}

function exportPythonPolicy() {
  const python = process.env.HG_PYTHON_EXECUTABLE || 'python';
  const result = spawnSync(python, ['-c', PYTHON_EXPORT], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return JSON.parse(result.stdout.trim());
}

test('manifest policy parity: inference_kind vocabulary matches Python export', () => {
  const jsPolicy = exportJavaScriptPolicy();
  const pyPolicy = exportPythonPolicy();
  assert.deepEqual(jsPolicy.inference_kinds, pyPolicy.inference_kinds);
});

test('manifest policy parity: allowed source_kind sets match Python export', () => {
  const jsPolicy = exportJavaScriptPolicy();
  const pyPolicy = exportPythonPolicy();
  assert.deepEqual(jsPolicy, pyPolicy);
});

test('manifest policy parity: export-manifest-policy.mjs matches in-process policy', () => {
  const result = spawnSync(process.execPath, [EXPORT_SCRIPT], {
    cwd: path.join(REPO_ROOT, 'v2/rp_runtime'),
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const exported = JSON.parse(result.stdout.trim());
  assert.deepEqual(exported, exportJavaScriptPolicy());
});

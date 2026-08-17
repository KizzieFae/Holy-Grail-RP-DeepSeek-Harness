import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { runCharacterInferenceSlice } from '../src/character-inference-slice.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..', '..');
const venvPython = path.join(repoRoot, 'autogen_rp', 'python', '.venv', 'Scripts', 'python.exe');

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods thoughtfully' }],
  motivation: {
    goal: 'acknowledge',
    tactic: 'subtle gesture',
    emotional_driver: 'calm',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const INVALID_MOVE = {
  move_schema_version: 2,
  beats: [],
  motivation: { goal: 'x', tactic: 'x', emotional_driver: 'x', risk_level: 'x' },
};

async function startDomainApi(port) {
  const proc = spawn(
    venvPython,
    ['-m', 'domain_api', '--host', '127.0.0.1', '--port', String(port)],
    { cwd: path.join(repoRoot, 'v2'), env: { ...process.env, PYTHONPATH: path.join(repoRoot, 'v2') } },
  );
  const baseUrl = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch(`${baseUrl}/v1/scenes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cast: ['Alice', 'Bob'] }),
      });
      if (res.ok) return { proc, baseUrl };
    } catch {
      // server not ready
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  proc.kill();
  throw new Error('Domain API server failed to start');
}

test('boundary prototype: reject then commit with correlated hg events', async (t) => {
  const port = 18765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const result = await runCharacterInferenceSlice({
    domainApi: { baseUrl },
    mockResponses: [JSON.stringify(INVALID_MOVE), JSON.stringify(VALID_MOVE)],
  });

  assert.equal(result.committed, true);
  assert.ok(result.domain_commit_id);
  assert.equal(result.continuity_turn_index, 1);

  const proposed = result.events.filter((e) => e.type === 'hg/move-proposed');
  const rejected = result.events.filter((e) => e.type === 'hg/move-rejected');
  const committed = result.events.filter((e) => e.type === 'hg/move-committed');
  assert.equal(proposed.length, 2);
  assert.equal(rejected.length, 1);
  assert.equal(committed.length, 1);
  assert.equal(committed[0].data.inference_id, result.inference_id);
  assert.equal(committed[0].data.domain_commit_id, result.domain_commit_id);

  const stateRes = await fetch(`${baseUrl}/v1/scenes/${encodeURIComponent(result.hg_scene_id)}/state`);
  const state = await stateRes.json();
  assert.equal(state.turn_counter, 1);
  assert.equal(state.committed_move_count, 1);
});

test('boundary prototype: DSH-only proposal does not commit', async (t) => {
  const port = 19765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const createRes = await fetch(`${baseUrl}/v1/scenes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice', 'Bob'] }),
  });
  const created = await createRes.json();
  const hgSceneId = created.hg_scene_id;

  const result = await runCharacterInferenceSlice({
    domainApi: { baseUrl },
    hgSceneId,
    mockResponses: [JSON.stringify(INVALID_MOVE)],
  });

  assert.equal(result.committed, false);
  const stateRes = await fetch(`${baseUrl}/v1/scenes/${encodeURIComponent(hgSceneId)}/state`);
  const state = await stateRes.json();
  assert.equal(state.turn_counter, 0);
  assert.equal(state.committed_move_count, 0);
  assert.ok(result.events.some((e) => e.type === 'hg/move-rejected'));
});

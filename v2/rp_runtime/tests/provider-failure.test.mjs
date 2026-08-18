import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..', '..', '..');
const venvPython = path.join(repoRoot, 'autogen_rp', 'python', '.venv', 'Scripts', 'python.exe');

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
      // not ready
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  proc.kill();
  throw new Error('Domain API server failed to start');
}

test('provider failure: missing credential does not mutate domain state', async (t) => {
  const port = 21765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: {
      mountDeepSeek: true,
      deepseek: { apiKeyEnv: 'HG_TEST_MISSING_DEEPSEEK_KEY' },
    },
  });

  const created = await fetch(`${baseUrl}/v1/scenes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  }).then((res) => res.json());
  const before = await fetch(`${baseUrl}/v1/scenes/${created.hg_scene_id}/state`)
    .then((res) => res.json());
  const turnBefore = Number(before.turn_counter ?? 0);

  const result = await phaseExecutors.runCharacterInference({
    domainApi: { baseUrl },
    hgSceneId: created.hg_scene_id,
    characterId: 'Alice',
    modelProfile: deepseekInferenceProfile({ reasoningEffort: 'off' }),
  });

  assert.equal(result.committed, false);
  assert.ok(result.provider_failure, 'expected structured provider failure');
  assert.equal(result.inference_trace?.provider, 'deepseek-official');
  assert.equal(result.domain_commit_id, null);

  const after = await fetch(`${baseUrl}/v1/scenes/${created.hg_scene_id}/state`)
    .then((res) => res.json());
  assert.equal(Number(after.turn_counter ?? 0), turnBefore);

  const failureEvent = result.scene_events.find((event) => event.type === 'hg/inference-failed');
  assert.ok(failureEvent, 'expected hg/inference-failed scene event');
  assert.equal(failureEvent.data.failure?.code, 'MISSING_CREDENTIAL');
});

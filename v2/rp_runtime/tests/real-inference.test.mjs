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
const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

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

test('real DeepSeek inference: DSH provider boundary with trace evidence', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 120_000,
}, async (t) => {
  const port = 22765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { runtime } = await createHolyGrailRpContext({
    domainApi: { baseUrl },
    inference: { mountDeepSeek: true },
  });

  const result = await runtime.runCharacterInference({
    domainApi: { baseUrl },
    characterId: 'Alice',
    modelProfile: deepseekInferenceProfile({
      reasoningEffort: 'low',
      maxTokens: 512,
    }),
    prompt: [
      'You are Alice in a quiet room. Respond with ONLY one JSON object, no markdown.',
      'Required keys: move_schema_version (2), beats (array with one action beat),',
      'motivation (goal, tactic, emotional_driver, risk_level),',
      'semantic_evaluation (decision: no_covered_change).',
      'Example action: "glances around the room".',
    ].join(' '),
  });

  const trace = result.inference_trace;
  assert.ok(trace, 'expected inference trace');
  assert.equal(trace.provider, 'deepseek-official');
  assert.equal(trace.model, 'deepseek-v4-flash');
  assert.equal(trace.reasoning_effort, 'low');
  assert.ok(trace.manifest_id, 'expected manifest correlation');
  assert.ok(Array.isArray(trace.contribution_ids));
  assert.ok(
    trace.assistant_text.length > 0 || trace.stream.text_delta_count > 0,
    'expected streamed assistant output',
  );
  assert.equal(result.provider_failure, null);

  if (result.committed) {
    assert.ok(result.domain_commit_id);
    assert.equal(typeof result.continuity_turn_index, 'number');
    const commitEvent = result.scene_events.find((event) => event.type === 'hg/move-committed');
    assert.ok(commitEvent);
  } else {
    const proposed = result.scene_events.find((event) => event.type === 'hg/move-proposed');
    assert.ok(proposed, 'expected move proposal even when validation did not commit');
  }
});

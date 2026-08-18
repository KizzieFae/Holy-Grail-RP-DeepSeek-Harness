import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';

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

const VALID_DIRECTOR = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should speak next.',
  environment_event: '',
  tension_shift: '',
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
      // not ready
    }
    await new Promise((r) => setTimeout(r, 100));
  }
  proc.kill();
  throw new Error('Domain API server failed to start');
}

test('director-character round: full orchestration with correlation', async (t) => {
  const port = 20765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, runtime } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await runtime.runDirectorCharacterRound({
    domainApi: { baseUrl },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterResponses: [JSON.stringify(VALID_MOVE)],
  });

  assert.equal(result.committed, true);
  assert.equal(result.selected_character_id, 'Alice');
  assert.equal(result.continuity_turn_index, 1);
  assert.ok(result.domain_commit_id);
  assert.ok(result.hg_round_id);
  assert.ok(result.director_inference_session_id);
  assert.ok(result.character_inference_session_id);
  assert.notEqual(
    result.director_inference_session_id,
    result.character_inference_session_id,
  );

  const types = result.scene_events.map((e) => e.type);
  assert.ok(types.includes('hg/round-started'));
  assert.ok(types.includes('hg/director-proposed'));
  assert.ok(types.includes('hg/director-accepted'));
  assert.ok(types.includes('hg/move-proposed'));
  assert.ok(types.includes('hg/move-committed'));
  assert.ok(types.includes('hg/narrator-started'));
  assert.ok(types.includes('hg/narrator-completed'));
  assert.equal(result.presentation_rendered, true);
  assert.ok(result.presentation_text);

  const stateRes = await fetch(`${baseUrl}/v1/scenes/${encodeURIComponent(result.hg_scene_id)}/state`);
  const state = await stateRes.json();
  assert.equal(state.turn_counter, 1);
  assert.equal(state.committed_move_count, 1);
});

test('director-character round: director rejection does not commit', async (t) => {
  const port = 21765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, runtime } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await runtime.runDirectorCharacterRound({
    domainApi: { baseUrl },
    mockDirectorResponses: [JSON.stringify({ next_actor: 'Zelda', end_round: false, reason: 'x' })],
    mockCharacterResponses: [JSON.stringify(VALID_MOVE)],
  });

  assert.equal(result.committed, false);
  assert.equal(result.completion_reason, 'director_not_accepted');
  assert.ok(result.scene_events.some((e) => e.type === 'hg/director-rejected'));
  assert.equal(result.scene_events.some((e) => e.type === 'hg/move-committed'), false);
});

test('director-character round: records boundary call metrics', async (t) => {
  const port = 22765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, runtime } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await runtime.runDirectorCharacterRound({
    domainApi: { baseUrl },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterResponses: [JSON.stringify(VALID_MOVE)],
  });

  assert.ok(result.boundary_metrics.calls.length >= 6);
  const labels = result.boundary_metrics.calls.map((c) => c.label);
  assert.ok(labels.includes('prepareDirectorContext'));
  assert.ok(labels.includes('validateDirectorDecision'));
  assert.ok(labels.includes('prepareCharacterContext'));
  assert.ok(labels.includes('validateMove'));
  assert.ok(labels.includes('commitMove'));
  assert.ok(labels.includes('prepareNarratorContext'));
});

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

const NARRATOR_PROSE = 'Alice nodded thoughtfully, taking in the workshop around her.';

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

function eventIndex(events, type) {
  return events.findIndex((e) => e.type === type);
}

test('three-role round: director → character → commit → narrator', async (t) => {
  const port = 25765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    createScene: { cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });

  assert.equal(result.committed, true);
  assert.equal(result.presentation_rendered, true);
  assert.equal(result.presentation_text, NARRATOR_PROSE);
  assert.ok(result.narrator_inference_session_id);
  assert.notEqual(result.narrator_inference_session_id, result.character_inference_session_id);
  assert.notEqual(result.narrator_inference_session_id, result.director_inference_session_id);

  const types = result.scene_events.map((e) => e.type);
  assert.ok(types.includes('hg/narrator-started'));
  assert.ok(types.includes('hg/narrator-completed'));

  const commitIdx = eventIndex(result.scene_events, 'hg/move-committed');
  const narratorStartIdx = eventIndex(result.scene_events, 'hg/narrator-started');
  assert.ok(commitIdx >= 0);
  assert.ok(narratorStartIdx > commitIdx);

  const labels = result.boundary_metrics.calls.map((c) => c.label);
  assert.ok(labels.includes('prepareNarratorContext'));
});

test('three-role round: commit failure skips narrator', async (t) => {
  const port = 26765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    createScene: { cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[
      JSON.stringify({
        move_schema_version: 2,
        beats: [],
        motivation: { goal: 'x', tactic: 'x', emotional_driver: 'x', risk_level: 'x' },
      }),
    ]],
    mockNarratorTurnResponses: [[NARRATOR_PROSE]],
  });

  assert.equal(result.committed, false);
  assert.equal(result.presentation_rendered, false);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/narrator-started'), false);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/move-committed'), false);
});

test('narrator failure after commit preserves canon', async (t) => {
  const port = 27765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    createScene: { cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    mockNarratorTurnResponses: [['']],
  });

  assert.equal(result.committed, true);
  assert.equal(result.presentation_rendered, false);
  assert.equal(result.presentation_failed, true);
  assert.ok(result.domain_commit_id);

  const failed = result.scene_events.find((e) => e.type === 'hg/narrator-failed');
  assert.ok(failed);
  assert.equal(failed.data.canon_preserved, true);

  const stateRes = await fetch(`${baseUrl}/v1/scenes/${encodeURIComponent(result.hg_scene_id)}/state`);
  const state = await stateRes.json();
  assert.equal(state.turn_counter, 1);
  assert.equal(state.committed_move_count, 1);
});

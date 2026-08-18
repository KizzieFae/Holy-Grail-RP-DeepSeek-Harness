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

const MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'acts deliberately' }],
  motivation: { goal: 'a', tactic: 'b', emotional_driver: 'c', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_FOR = (name) => ({
  next_actor: name,
  end_round: false,
  reason: `${name} should speak.`,
  environment_event: '',
  tension_shift: '',
});

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

test('participation: forced designation selects Alice without Director inference', async (t) => {
  const port = 38765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, runtime } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await runtime.runRound({
    domainApi: { baseUrl },
    createScene: { cast: ['Alice'] },
    forcedDesignation: 'Alice',
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Bob'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  assert.equal(result.character_turn_count, 1);
  assert.equal(result.actors_used_this_round[0], 'Alice');
  assert.equal(result.scene_events.some((e) => e.type === 'hg/director-proposed'), false);
  const participation = result.scene_events.find((e) => e.type === 'hg/participation-decision');
  assert.ok(participation);
  assert.equal(participation.data.participation.selection_mode, 'direct');
  assert.equal(participation.data.participation.selected_actor, 'Alice');
  assert.deepEqual(participation.data.participation.participation_sources, ['forced_designation']);
});

test('participation: ineligible forced designation falls back to Director', async (t) => {
  const port = 39765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, runtime } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await runtime.runRound({
    domainApi: { baseUrl },
    createScene: { cast: ['Alice', 'Bob'] },
    forcedDesignation: 'Carol',
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  const participation = result.scene_events.find((e) => e.type === 'hg/participation-decision');
  assert.ok(participation);
  assert.equal(participation.data.participation.selection_mode, 'director');
  assert.equal(participation.data.participation.forced_designation_ignored, true);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/director-proposed'), true);
});

test('participation: forced designation consumed only once per round invocation', async (t) => {
  const port = 40765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, runtime } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await runtime.runRound({
    domainApi: { baseUrl },
    createScene: { cast: ['Alice', 'Bob'] },
    forcedDesignation: 'Alice',
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Bob')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)], [JSON.stringify(MOVE)]],
  });

  const participationEvents = result.scene_events.filter((e) => e.type === 'hg/participation-decision');
  assert.equal(participationEvents.length, 2);
  assert.equal(participationEvents[0].data.participation.selection_mode, 'direct');
  assert.equal(participationEvents[1].data.participation.selection_mode, 'director');
  assert.equal(result.character_turn_count, 2);
});

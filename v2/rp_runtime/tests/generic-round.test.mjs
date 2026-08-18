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

const DIRECTOR_END = {
  next_actor: '',
  end_round: true,
  reason: 'Round complete.',
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

test('generic round: director end_round completes without further character turns', async (t) => {
  const port = 32765 + Math.floor(Math.random() * 1000);
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
    createScene: { cast: ['Alice', 'Bob'] },
    mockDirectorResponses: [JSON.stringify(DIRECTOR_END)],
  });

  assert.equal(result.completion_reason, 'director_end_round');
  assert.equal(result.completion_class, 'semantic');
  assert.equal(result.character_turn_count, 0);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/move-proposed'), false);
});

test('generic round: actor exhaustion completes without extra director call', async (t) => {
  const port = 33765 + Math.floor(Math.random() * 1000);
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
    mockDirectorResponses: [JSON.stringify(DIRECTOR_FOR('Alice'))],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  assert.equal(result.completion_reason, 'no_eligible_actors');
  assert.equal(result.character_turn_count, 1);
  const directorAccepted = result.scene_events.filter((e) => e.type === 'hg/director-accepted');
  assert.equal(directorAccepted.length, 1);
});

test('generic round: defensive turn ceiling is distinct from semantic completion', async (t) => {
  const port = 34765 + Math.floor(Math.random() * 1000);
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
    createScene: { cast: ['Alice', 'Bob', 'Carol'] },
    defensiveTurnCeiling: 1,
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_FOR('Alice')),
      JSON.stringify(DIRECTOR_FOR('Bob')),
    ],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
  });

  assert.equal(result.completion_reason, 'defensive_turn_ceiling');
  assert.equal(result.completion_class, 'defensive');
  assert.equal(result.character_turn_count, 1);
});

test('generic round: three-character cast executes until actor exhaustion', async (t) => {
  const port = 35765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const cast = ['Alice', 'Bob', 'Carol'];
  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    createScene: { cast },
    mockDirectorResponses: cast.map((name) => JSON.stringify(DIRECTOR_FOR(name))),
    mockCharacterTurnResponses: cast.map(() => [JSON.stringify(MOVE)]),
  });

  assert.equal(result.completion_reason, 'no_eligible_actors');
  assert.equal(result.character_turn_count, 3);
  assert.deepEqual(result.actors_used_this_round, cast);
});

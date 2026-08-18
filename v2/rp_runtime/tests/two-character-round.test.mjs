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

const ALICE_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'places the blueprint on the table' }],
  motivation: {
    goal: 'share',
    tactic: 'visible placement',
    emotional_driver: 'helpful',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const BOB_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'examines the blueprint Alice left on the table' }],
  motivation: {
    goal: 'inspect',
    tactic: 'careful study',
    emotional_driver: 'curious',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_ALICE = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should speak first.',
  environment_event: '',
  tension_shift: '',
};

const DIRECTOR_BOB = {
  next_actor: 'Bob',
  end_round: false,
  reason: 'Bob should respond after Alice.',
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

function eventIndexes(events, type) {
  return events
    .map((event, index) => (event.type === type ? index : -1))
    .filter((index) => index >= 0);
}

test('two-character round: director sequences Alice then Bob with per-turn narration', async (t) => {
  const port = 29765 + Math.floor(Math.random() * 1000);
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
    mockDirectorResponses: [
      JSON.stringify(DIRECTOR_ALICE),
      JSON.stringify(DIRECTOR_BOB),
    ],
    mockCharacterTurnResponses: [
      [JSON.stringify(ALICE_MOVE)],
      [JSON.stringify(BOB_MOVE)],
    ],
    mockNarratorTurnResponses: [
      ['Alice placed the blueprint on the table.'],
      ['Bob examined the blueprint Alice had left behind.'],
    ],
  });

  assert.equal(result.completion_reason, 'no_eligible_actors');
  assert.equal(result.completion_class, 'semantic');
  assert.equal(result.character_turn_count, 2);
  assert.deepEqual(result.actors_used_this_round, ['Alice', 'Bob']);
  assert.equal(result.character_turns[0].character_id, 'Alice');
  assert.equal(result.character_turns[1].character_id, 'Bob');

  const types = result.scene_events.map((e) => e.type);
  assert.ok(types.includes('hg/round-completed'));
  assert.equal(types.filter((type) => type === 'hg/move-committed').length, 2);
  assert.equal(types.filter((type) => type === 'hg/narrator-completed').length, 2);
  assert.equal(types.filter((type) => type === 'hg/director-accepted').length, 2);

  const commitIndexes = eventIndexes(result.scene_events, 'hg/move-committed');
  const narratorIndexes = eventIndexes(result.scene_events, 'hg/narrator-completed');
  assert.ok(commitIndexes[0] < narratorIndexes[0]);
  assert.ok(narratorIndexes[0] < commitIndexes[1]);
  assert.ok(commitIndexes[1] < narratorIndexes[1]);

  const stateRes = await fetch(`${baseUrl}/v1/scenes/${encodeURIComponent(result.hg_scene_id)}/state`);
  const state = await stateRes.json();
  assert.equal(state.turn_counter, 2);
  assert.equal(state.committed_move_count, 2);
});

test('two-character round: Bob context projection excludes Alice private knowledge', async (t) => {
  const port = 30765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const sceneRes = await fetch(`${baseUrl}/v1/scenes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice', 'Bob'] }),
  });
  const scene = await sceneRes.json();
  const roundRes = await fetch(`${baseUrl}/v1/rounds/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hg_scene_id: scene.hg_scene_id }),
  });
  const round = await roundRes.json();

  const aliceValidation = await fetch(`${baseUrl}/v1/moves/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      inference_id: 'inf-alice',
      hg_scene_id: scene.hg_scene_id,
      hg_round_id: round.hg_round_id,
      character_id: 'Alice',
      role: 'guest',
      turn_index: round.turn_index,
      attempt_index: 0,
      proposed_move: ALICE_MOVE,
      raw_model_output: JSON.stringify(ALICE_MOVE),
    }),
  });
  const aliceValidated = await aliceValidation.json();
  assert.equal(aliceValidated.accepted, true);

  const aliceCommit = await fetch(`${baseUrl}/v1/moves/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      inference_id: 'inf-alice',
      hg_scene_id: scene.hg_scene_id,
      hg_round_id: round.hg_round_id,
      character_id: 'Alice',
      validated_move: aliceValidated.normalized_move,
      director_decision: DIRECTOR_ALICE,
      expected_turn_index: round.turn_index,
    }),
  });
  const aliceCommitted = await aliceCommit.json();
  assert.equal(aliceCommitted.committed, true);

  const bobContextRes = await fetch(`${baseUrl}/v1/context/prepare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_scene_id: scene.hg_scene_id,
      hg_round_id: round.hg_round_id,
      inference_id: 'inf-bob',
      character_id: 'Bob',
      role: 'staff',
      turn_index: aliceCommitted.continuity_turn_index,
      attempt_index: 0,
    }),
  });
  const bobContext = await bobContextRes.json();
  const kinds = new Set(bobContext.contributions.map((c) => c.source_kind));
  assert.equal(kinds.has('continuity_summary'), true);
  assert.equal(kinds.has('character_private'), true);
  const summary = bobContext.contributions.find((c) => c.source_kind === 'continuity_summary');
  assert.ok(summary.content.includes('places the blueprint on the table'));
  const bobPrivate = bobContext.contributions.find((c) => c.source_kind === 'character_private');
  assert.ok(bobPrivate.content.includes('private-Bob'));
  for (const contribution of bobContext.contributions) {
    assert.equal(String(contribution.content).includes('private-Alice'), false);
  }
});

test('two-character round: rejected Alice attempt stays out of Bob projection', async (t) => {
  const port = 31765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port);
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const sceneRes = await fetch(`${baseUrl}/v1/scenes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice', 'Bob'] }),
  });
  const scene = await sceneRes.json();
  const roundRes = await fetch(`${baseUrl}/v1/rounds/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hg_scene_id: scene.hg_scene_id }),
  });
  const round = await roundRes.json();

  const invalidMove = {
    move_schema_version: 2,
    beats: [],
    motivation: { goal: 'x', tactic: 'x', emotional_driver: 'x', risk_level: 'x' },
  };
  const rejected = await fetch(`${baseUrl}/v1/moves/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      inference_id: 'inf-alice-bad',
      hg_scene_id: scene.hg_scene_id,
      hg_round_id: round.hg_round_id,
      character_id: 'Alice',
      role: 'guest',
      turn_index: round.turn_index,
      attempt_index: 0,
      proposed_move: invalidMove,
      raw_model_output: JSON.stringify(invalidMove),
    }),
  });
  assert.equal((await rejected.json()).accepted, false);

  const aliceValidation = await fetch(`${baseUrl}/v1/moves/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      inference_id: 'inf-alice-good',
      hg_scene_id: scene.hg_scene_id,
      hg_round_id: round.hg_round_id,
      character_id: 'Alice',
      role: 'guest',
      turn_index: round.turn_index,
      attempt_index: 1,
      proposed_move: ALICE_MOVE,
      raw_model_output: JSON.stringify(ALICE_MOVE),
    }),
  });
  const aliceValidated = await aliceValidation.json();
  const aliceCommit = await fetch(`${baseUrl}/v1/moves/commit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      inference_id: 'inf-alice-good',
      hg_scene_id: scene.hg_scene_id,
      hg_round_id: round.hg_round_id,
      character_id: 'Alice',
      validated_move: aliceValidated.normalized_move,
      director_decision: DIRECTOR_ALICE,
      expected_turn_index: round.turn_index,
    }),
  });
  const aliceCommitted = await aliceCommit.json();

  const bobContextRes = await fetch(`${baseUrl}/v1/context/prepare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_scene_id: scene.hg_scene_id,
      hg_round_id: round.hg_round_id,
      inference_id: 'inf-bob',
      character_id: 'Bob',
      role: 'staff',
      turn_index: aliceCommitted.continuity_turn_index,
      attempt_index: 0,
    }),
  });
  const bobContext = await bobContextRes.json();
  const summary = bobContext.contributions.find((c) => c.source_kind === 'continuity_summary');
  assert.ok(summary.content.includes('places the blueprint on the table'));
  assert.equal(summary.content.includes('"beats": []'), false);
});

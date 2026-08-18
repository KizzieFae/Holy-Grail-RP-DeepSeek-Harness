import assert from 'node:assert/strict';
import { once } from 'node:events';
import fs from 'node:fs';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { makeTempSessionsDir, startDomainApi } from './helpers/domain-api.mjs';

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

const VALID_DIRECTOR_ALICE = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should speak first.',
  environment_event: '',
  tension_shift: '',
};

const VALID_DIRECTOR_BOB = {
  next_actor: 'Bob',
  end_round: false,
  reason: 'Bob should speak next.',
  environment_event: '',
  tension_shift: '',
};

test('production session: full round persists durable state', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const port = 31765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port, { sessionsDir });
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
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR_ALICE)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  assert.ok(result.hg_session_id);
  assert.equal(result.hg_session_id, result.hg_scene_id);
  assert.equal(result.continuity_turn_index, 1);
  assert.ok(result.domain_commit_id);

  const labels = result.boundary_metrics.calls.map((c) => c.label);
  assert.ok(labels.includes('createSession'));
  assert.equal(labels.includes('createScene'), false);

  const roundStarted = result.scene_events.find((e) => e.type === 'hg/round-started');
  assert.equal(roundStarted.data.hg_session_id, result.hg_session_id);

  const sessionFile = `${sessionsDir}/${result.hg_session_id}.json`;
  assert.ok(fs.existsSync(sessionFile));
});

test('production session: Domain Host restart resumes between rounds', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const port1 = 32765 + Math.floor(Math.random() * 1000);
  const host1 = await startDomainApi(port1, { sessionsDir });
  const { ctx: ctx1, orchestrator: orch1 } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host1.baseUrl },
  });

  const round1 = await orch1.runRound({
    domainApi: { baseUrl: host1.baseUrl },
    session: { mode: 'create', cast: ['Alice', 'Bob'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR_ALICE)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  assert.equal(round1.continuity_turn_index, 1);
  const hgSessionId = round1.hg_session_id;

  await ctx1.fiber.dispose();
  host1.proc.kill();
  await once(host1.proc, 'exit');

  const port2 = 33765 + Math.floor(Math.random() * 1000);
  const host2 = await startDomainApi(port2, { sessionsDir });
  t.after(async () => {
    host2.proc.kill();
    await once(host2.proc, 'exit');
  });

  const { ctx: ctx2, orchestrator: orch2 } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host2.baseUrl },
  });
  t.after(async () => {
    await ctx2.fiber.dispose();
  });

  const round2 = await orch2.runRound({
    domainApi: { baseUrl: host2.baseUrl },
    session: { mode: 'open', hg_session_id: hgSessionId },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR_BOB)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  assert.equal(round2.hg_session_id, hgSessionId);
  assert.equal(round2.continuity_turn_index, 2);
  assert.ok(round2.boundary_metrics.calls.some((c) => c.label === 'openSession'));
});

test('production session: DSH restart uses new execution session for same HG session', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const port = 34765 + Math.floor(Math.random() * 1000);
  const { proc, baseUrl } = await startDomainApi(port, { sessionsDir });
  t.after(async () => {
    proc.kill();
    await once(proc, 'exit');
  });

  const { ctx: ctx1, orchestrator: orch1 } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  const first = await orch1.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR_ALICE)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });
  await ctx1.fiber.dispose();

  const { ctx: ctx2, orchestrator: orch2 } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx2.fiber.dispose();
  });

  const second = await orch2.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: first.hg_session_id },
    mockDirectorResponses: [JSON.stringify({ ...VALID_DIRECTOR_ALICE, end_round: true })],
    mockCharacterTurnResponses: [],
  });

  assert.equal(second.hg_session_id, first.hg_session_id);
  assert.notEqual(second.dsh_scene_session_id, first.dsh_scene_session_id);

  const stateRes = await fetch(`${baseUrl}/v1/scenes/${encodeURIComponent(first.hg_scene_id)}/state`);
  const state = await stateRes.json();
  assert.equal(state.turn_counter, 1);
  assert.equal(state.committed_move_count, 1);
});

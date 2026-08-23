import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { createHolyGrailAppServer } from '../src/application/app-server.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { makeTempSessionsDir } from './helpers/domain-api.mjs';

const MOCK_ROUND = {
  mockDirectorResponses: [
    JSON.stringify({
      next_actor: 'Alice',
      end_round: false,
      reason: 'Alice should respond.',
      environment_event: '',
      tension_shift: '',
    }),
    JSON.stringify({
      next_actor: 'Alice',
      end_round: true,
      reason: 'Round complete.',
      environment_event: '',
      tension_shift: '',
    }),
  ],
  mockCharacterTurnResponses: [[
    JSON.stringify({
      move_schema_version: 2,
      beats: [{ type: 'action', action: 'nods' }],
      motivation: {
        goal: 'ack',
        tactic: 'gesture',
        emotional_driver: 'calm',
        risk_level: 'low',
      },
      semantic_evaluation: { decision: 'no_covered_change' },
    }),
  ]],
  mockNarratorTurnResponses: [['Alice nodded thoughtfully in the workshop.']],
};

test('app server: health, session create, turn submit', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client.start();
  t.after(() => client.stop());

  const server = createHolyGrailAppServer(client);
  const { baseUrl } = await server.listen(0);
  t.after(() => server.close());

  const health = await fetch(`${baseUrl}/api/health`).then((r) => r.json());
  assert.equal(health.application_status, 'ready');

  const created = await fetch(`${baseUrl}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  }).then((r) => r.json());
  assert.ok(created.session.hg_session_id);

  const turn = await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userMessage: 'Hello Alice', ...MOCK_ROUND }),
  }).then((r) => r.json());
  assert.equal(turn.round.committed, true);
  assert.ok(turn.transcript.length >= 2);
});

test('app server: skip turn endpoint advances without user message', async (t) => {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });

  const client = new HolyGrailApplicationClient({
    inferenceMode: 'mock',
    domainHost: { sessionsDir },
  });
  await client.start();
  t.after(() => client.stop());

  const server = createHolyGrailAppServer(client);
  const { baseUrl } = await server.listen(0);
  t.after(() => server.close());

  await fetch(`${baseUrl}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  });

  const skip = await fetch(`${baseUrl}/api/turns/skip`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...MOCK_ROUND }),
  }).then((r) => r.json());
  assert.equal(skip.round.committed, true);
  assert.ok(skip.transcript.some((entry) => entry.player_skip));
});

test('app server: reports unavailable when runtime not started', async (t) => {
  const client = new HolyGrailApplicationClient({ inferenceMode: 'mock' });
  const server = createHolyGrailAppServer(client);
  const { baseUrl } = await server.listen(0);
  t.after(() => server.close());

  const res = await fetch(`${baseUrl}/api/sessions/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cast: ['Alice'] }),
  });
  assert.equal(res.status, 500);
});

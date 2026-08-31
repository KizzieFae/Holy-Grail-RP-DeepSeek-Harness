import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

import { createHolyGrailAppServer } from '../src/application/app-server.mjs';
import { HolyGrailApplicationClient } from '../src/application/hg-application-client.mjs';
import { LIFECYCLE_MILESTONES } from '../src/application/application-turn-lifecycle.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
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

const FAILING_MOCK_ROUND = {
  forceRoundFailure: true,
  testRoundDelayMs: 30,
};

function lifecycleAttempts(store, hgSessionId) {
  const index = store.readIndex(hgSessionId);
  return (index?.attempt_ids ?? []).map((id) => store.readAttempt(hgSessionId, id))
    .filter((attempt) => attempt?.correlation?.role === 'application_lifecycle');
}

async function setupServer(t, evidenceRoot = null) {
  const sessionsDir = makeTempSessionsDir();
  t.after(() => {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
  });
  if (evidenceRoot) {
    t.after(() => {
      fs.rmSync(evidenceRoot, { recursive: true, force: true });
    });
    process.env.HG_EXECUTION_EVIDENCE = 'on';
    process.env.HG_EXECUTION_EVIDENCE_DIR = evidenceRoot;
  }

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

  return { baseUrl, client, evidenceRoot, sessionsDir };
}

test('Case A: fast synchronous success preserves existing behavior', async (t) => {
  const { baseUrl } = await setupServer(t);
  const turn = await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userMessage: 'Hello Alice', ...MOCK_ROUND }),
  }).then((r) => r.json());
  assert.equal(turn.round.committed, true);
  assert.ok(turn.transcript.length >= 2);
  assert.ok(turn.client_operation_id);
});

test('Case B: slow round exposes in-progress then explicit terminal success', async (t) => {
  const evidenceRoot = fs.mkdtempSync(`${makeTempSessionsDir()}-evidence-`);
  const { baseUrl, client } = await setupServer(t, evidenceRoot);
  const operationId = 'op-slow-success';
  const submitPromise = fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userMessage: 'Slow hello',
      client_operation_id: operationId,
      testRoundDelayMs: 80,
      ...MOCK_ROUND,
    }),
  });

  await new Promise((resolve) => setTimeout(resolve, 20));
  const midStatus = await fetch(`${baseUrl}/api/status`).then((r) => r.json());
  assert.equal(midStatus.health.application_status, 'round_in_progress');
  assert.equal(midStatus.health.active_round_operation.operation_id, operationId);

  const turn = await submitPromise.then((r) => r.json());
  assert.equal(turn.client_operation_id, operationId);

  const finalStatus = await fetch(`${baseUrl}/api/status`).then((r) => r.json());
  assert.equal(finalStatus.health.last_round_terminal.outcome, 'succeeded');
  assert.equal(finalStatus.health.last_round_terminal.operation_id, operationId);

  const store = new ExecutionEvidenceStore(evidenceRoot);
  const attempts = lifecycleAttempts(store, client.activeSessionId);
  const milestones = attempts.map((a) => a.decision?.milestone);
  assert.ok(milestones.includes(LIFECYCLE_MILESTONES.ROUND_BEGAN));
  assert.ok(milestones.includes(LIFECYCLE_MILESTONES.ROUND_TERMINAL_SUCCEEDED));
});

test('Case C: delayed authoritative failure exposes explicit terminal failure', async (t) => {
  const { baseUrl } = await setupServer(t);
  const operationId = 'op-slow-fail';
  const res = await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userMessage: 'Fail please',
      client_operation_id: operationId,
      ...FAILING_MOCK_ROUND,
    }),
  });
  assert.equal(res.status, 502);
  const status = await fetch(`${baseUrl}/api/status`).then((r) => r.json());
  assert.equal(status.health.last_round_terminal.outcome, 'failed');
  assert.equal(status.health.last_round_terminal.operation_id, operationId);
  assert.ok(status.health.last_error);
});

test('Case E: concurrent submit rejected with 409 before second durable user turn', async (t) => {
  const evidenceRoot = fs.mkdtempSync(`${makeTempSessionsDir()}-evidence-`);
  const { baseUrl, client } = await setupServer(t, evidenceRoot);
  const firstOp = 'op-first';
  const submitPromise = fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userMessage: 'First message',
      client_operation_id: firstOp,
      testRoundDelayMs: 100,
      ...MOCK_ROUND,
    }),
  });

  await new Promise((resolve) => setTimeout(resolve, 15));
  const conflict = await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userMessage: 'Second message must not persist',
      client_operation_id: 'op-second',
      ...MOCK_ROUND,
    }),
  });
  assert.equal(conflict.status, 409);

  const historyBeforeComplete = await fetch(
    `${baseUrl}/api/sessions/${client.activeSessionId}/transcript`,
  ).then((r) => r.json());
  const userTurnsBefore = historyBeforeComplete.transcript.filter((e) => e.role === 'user');
  assert.equal(userTurnsBefore.filter((e) => e.content === 'Second message must not persist').length, 0);

  await submitPromise;

  const store = new ExecutionEvidenceStore(evidenceRoot);
  const attempts = lifecycleAttempts(store, client.activeSessionId);
  assert.ok(
    attempts.some((a) => a.decision?.milestone === LIFECYCLE_MILESTONES.CONCURRENT_SUBMIT_REJECTED),
  );
});

test('Case F: prior terminal outcome cannot satisfy a newer operation id', async (t) => {
  const { baseUrl } = await setupServer(t);
  const first = await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userMessage: 'First',
      client_operation_id: 'op-one',
      ...MOCK_ROUND,
    }),
  }).then((r) => r.json());
  assert.equal(first.client_operation_id, 'op-one');

  const status = await fetch(`${baseUrl}/api/status`).then((r) => r.json());
  assert.equal(status.health.last_round_terminal.operation_id, 'op-one');

  const secondStatusMid = await fetch(`${baseUrl}/api/status`).then((r) => r.json());
  assert.notEqual(secondStatusMid.health.last_round_terminal?.operation_id, 'op-two');

  await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userMessage: 'Second',
      client_operation_id: 'op-two',
      ...MOCK_ROUND,
    }),
  });

  const afterSecond = await fetch(`${baseUrl}/api/status`).then((r) => r.json());
  assert.equal(afterSecond.health.last_round_terminal.operation_id, 'op-two');
});

test('Cases G/H/I: client recovery milestones correlate with terminal outcomes', async (t) => {
  const evidenceRoot = fs.mkdtempSync(`${makeTempSessionsDir()}-evidence-`);
  const { baseUrl, client } = await setupServer(t, evidenceRoot);
  const operationId = 'op-forensic';

  await fetch(`${baseUrl}/api/application/recovery-milestone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_session_id: client.activeSessionId,
      client_operation_id: operationId,
      milestone: LIFECYCLE_MILESTONES.CLIENT_WAIT_EXPIRED,
      details: { response_wait_sec: 180 },
    }),
  });

  await fetch(`${baseUrl}/api/turns/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userMessage: 'Forensic path',
      client_operation_id: operationId,
      ...MOCK_ROUND,
    }),
  });

  await fetch(`${baseUrl}/api/application/recovery-milestone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hg_session_id: client.activeSessionId,
      client_operation_id: operationId,
      milestone: LIFECYCLE_MILESTONES.RECOVERY_TERMINAL,
      details: { result: 'success_recovered' },
    }),
  });

  const store = new ExecutionEvidenceStore(evidenceRoot);
  const attempts = lifecycleAttempts(store, client.activeSessionId);
  const milestones = attempts.map((a) => ({
    milestone: a.decision?.milestone,
    operation_id: a.decision?.operation_id,
  }));
  assert.ok(milestones.some((m) => m.milestone === LIFECYCLE_MILESTONES.CLIENT_WAIT_EXPIRED
    && m.operation_id === operationId));
  assert.ok(milestones.some((m) => m.milestone === LIFECYCLE_MILESTONES.ROUND_TERMINAL_SUCCEEDED
    && m.operation_id === operationId));
  assert.ok(milestones.some((m) => m.milestone === LIFECYCLE_MILESTONES.RECOVERY_TERMINAL
    && m.operation_id === operationId));

  const pollMilestones = milestones.filter((m) => m.milestone === 'recovery_poll');
  assert.equal(pollMilestones.length, 0);
});

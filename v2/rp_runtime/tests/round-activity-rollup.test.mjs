import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';

function tempStore(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-round-activity-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return new ExecutionEvidenceStore(root);
}

function inferenceAttempt({
  evidenceId,
  hgSessionId = 'sess-ra',
  operationId = 'op-1',
  hgRoundId = 'round-1',
  role = 'storyteller',
  inferenceKind = 'storyteller_orientation',
  totalTokens = 100,
}) {
  return {
    evidence_id: evidenceId,
    correlation: {
      hg_session_id: hgSessionId,
      operation_id: operationId,
      hg_round_id: hgRoundId,
      role,
      inference_kind: inferenceKind,
    },
    request: { schema: 'hg_assembled_request_v1' },
    response: { schema: 'hg_assembled_response_v1' },
    inference_health: {
      usage: { total_tokens: totalTokens },
    },
  };
}

function aggregateAuthoritative(store, hgSessionId, roundId) {
  const index = store.readIndex(hgSessionId);
  const roundKey = String(roundId);
  const ids = new Set(index.round_activity?.[roundKey]?.evidence_ids ?? []);
  let totalTokens = 0;
  const roles = {};
  const kinds = {};
  for (const evidenceId of ids) {
    const attempt = store.readAttempt(hgSessionId, evidenceId);
    if (!attempt) continue;
    const role = attempt.correlation?.role;
    if (role && role !== 'execution_span' && role !== 'application_lifecycle') {
      roles[role] = (roles[role] ?? 0) + 1;
    }
    const kind = attempt.correlation?.inference_kind;
    if (kind) {
      kinds[kind] = (kinds[kind] ?? 0) + 1;
      const tokens = Number(attempt.inference_health?.usage?.total_tokens);
      if (Number.isFinite(tokens)) totalTokens += tokens;
    }
  }
  return { ids, totalTokens, roles, kinds };
}

function rebuildTimingAndActivity(store, hgSessionId) {
  const index = store.readIndex(hgSessionId);
  index.timing = { by_operation: {}, by_round: {} };
  index.round_activity = {};
  for (const evidenceId of index.attempt_ids ?? []) {
    const attempt = store.readAttempt(hgSessionId, evidenceId);
    if (!attempt) continue;
    store._indexTimingAndActivity(hgSessionId, evidenceId, attempt, index);
  }
  fs.writeFileSync(
    store.indexPath(hgSessionId),
    `${JSON.stringify(index, null, 2)}\n`,
    'utf8',
  );
  return index;
}

function assertRoundReconciles(store, hgSessionId, roundId) {
  const roundKey = String(roundId);
  const activity = store.readIndex(hgSessionId).round_activity[roundKey];
  const auth = aggregateAuthoritative(store, hgSessionId, roundId);
  assert.equal(activity.evidence_ids.length, auth.ids.size);
  assert.equal(activity.total_tokens, auth.totalTokens);
  for (const [role, entry] of Object.entries(activity.roles ?? {})) {
    assert.equal(entry.count, auth.roles[role] ?? 0);
    assert.equal(entry.evidence_ids.length, auth.roles[role] ?? 0);
  }
  for (const [kind, entry] of Object.entries(activity.inference_kinds ?? {})) {
    assert.equal(entry.count, auth.kinds[kind] ?? 0);
    assert.equal(entry.evidence_ids.length, auth.kinds[kind] ?? 0);
  }
}

test('round_activity: single indexing reconciles with authoritative attempts', (t) => {
  const store = tempStore(t);
  const hgSessionId = 'sess-single';
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-1',
    hgSessionId,
    role: 'storyteller',
    inferenceKind: 'storyteller_orientation',
    totalTokens: 120,
  }));
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-2',
    hgSessionId,
    role: 'character',
    inferenceKind: 'character_move',
    totalTokens: 80,
  }));
  assertRoundReconciles(store, hgSessionId, 'round-1');
});

test('round_activity: repeated indexing is idempotent', (t) => {
  const store = tempStore(t);
  const hgSessionId = 'sess-repeat';
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-r1',
    hgSessionId,
    totalTokens: 200,
  }));
  const first = JSON.stringify(store.readIndex(hgSessionId).round_activity);
  const index = store.readIndex(hgSessionId);
  const attempt = store.readAttempt(hgSessionId, 'ev-r1');
  store._indexTimingAndActivity(hgSessionId, 'ev-r1', attempt, index);
  store._indexTimingAndActivity(hgSessionId, 'ev-r1', attempt, index);
  fs.writeFileSync(store.indexPath(hgSessionId), `${JSON.stringify(index, null, 2)}\n`, 'utf8');
  const second = JSON.stringify(store.readIndex(hgSessionId).round_activity);
  assert.equal(second, first);
  assertRoundReconciles(store, hgSessionId, 'round-1');
});

test('round_activity: patchOperationRoundAssociation re-index is idempotent', (t) => {
  const store = tempStore(t);
  const hgSessionId = 'sess-patch';
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-p1',
    hgSessionId,
    totalTokens: 150,
  }));
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-p2',
    hgSessionId,
    role: 'character',
    inferenceKind: 'character_move',
    totalTokens: 90,
  }));
  const before = JSON.stringify(store.readIndex(hgSessionId).round_activity);
  store.patchOperationRoundAssociation(hgSessionId, 'op-1', 'round-1');
  const after = JSON.stringify(store.readIndex(hgSessionId).round_activity);
  assert.equal(after, before);
  assertRoundReconciles(store, hgSessionId, 'round-1');
});

test('round_activity: rebuild from attempts reconciles exactly', (t) => {
  const store = tempStore(t);
  const hgSessionId = 'sess-rebuild';
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-b1',
    hgSessionId,
    totalTokens: 300,
  }));
  const index = store.readIndex(hgSessionId);
  index.round_activity['round-1'] = {
    evidence_ids: ['ev-b1'],
    roles: { storyteller: { count: 99, evidence_ids: ['ev-b1'] } },
    inference_kinds: {
      storyteller_orientation: { count: 99, evidence_ids: ['ev-b1'], total_tokens: 99999 },
    },
    participation_evidence_ids: [],
    total_tokens: 99999,
  };
  fs.writeFileSync(store.indexPath(hgSessionId), `${JSON.stringify(index, null, 2)}\n`, 'utf8');

  rebuildTimingAndActivity(store, hgSessionId);
  assertRoundReconciles(store, hgSessionId, 'round-1');
});

test('round_activity: incremental addition increments once', (t) => {
  const store = tempStore(t);
  const hgSessionId = 'sess-incr';
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-i1',
    hgSessionId,
    totalTokens: 50,
  }));
  const afterFirst = store.readIndex(hgSessionId).round_activity['round-1'];
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-i2',
    hgSessionId,
    role: 'director',
    inferenceKind: 'director_decision',
    totalTokens: 75,
  }));
  const afterSecond = store.readIndex(hgSessionId).round_activity['round-1'];
  assert.equal(afterSecond.evidence_ids.length, afterFirst.evidence_ids.length + 1);
  assert.equal(afterSecond.total_tokens, afterFirst.total_tokens + 75);
  assertRoundReconciles(store, hgSessionId, 'round-1');
});

test('round_activity: attempt appears once per operation and round bucket', (t) => {
  const store = tempStore(t);
  const hgSessionId = 'sess-multi';
  store.writeAttempt(inferenceAttempt({
    evidenceId: 'ev-m1',
    hgSessionId,
    operationId: 'op-a',
    hgRoundId: 'round-a',
    totalTokens: 40,
  }));
  const index = store.readIndex(hgSessionId);
  assert.equal(index.timing.by_operation['op-a'].length, 1);
  assert.equal(index.timing.by_round['round-a'].length, 1);
  assert.equal(index.round_activity['round-a'].total_tokens, 40);
  store._indexTimingAndActivity(hgSessionId, 'ev-m1', store.readAttempt(hgSessionId, 'ev-m1'), index);
  fs.writeFileSync(store.indexPath(hgSessionId), `${JSON.stringify(index, null, 2)}\n`, 'utf8');
  const after = store.readIndex(hgSessionId);
  assert.equal(after.timing.by_operation['op-a'].length, 1);
  assert.equal(after.timing.by_round['round-a'].length, 1);
  assert.equal(after.round_activity['round-a'].total_tokens, 40);
});

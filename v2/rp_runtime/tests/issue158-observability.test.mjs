import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import { ExecutionSpanTracker } from '../src/lib/execution-span-tracker.mjs';
import { ExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import {
  createTestSession,
  startDomainApi,
} from './helpers/domain-api.mjs';

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods' }],
  motivation: {
    goal: 'acknowledge',
    tactic: 'gesture',
    emotional_driver: 'calm',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const VALID_DIRECTOR = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice speaks.',
  environment_event: '',
  tension_shift: '',
};

function tempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-158-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const prev = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  t.after(() => {
    for (const [key, value] of Object.entries(prev)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });
  return { dataDir, sessionsDir };
}

function readAttempts(dataDir, hgSessionId) {
  const root = path.join(dataDir, 'execution_evidence', hgSessionId);
  const index = JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8'));
  const attempts = (index.attempt_ids ?? []).map((id) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${id}.json`), 'utf8'),
  ));
  return { index, attempts, root };
}

test('mock round: inference timing uses dsh_session_turn_boundary with timing_observed', async (t) => {
  const { dataDir, sessionsDir } = tempDataEnv(t);
  const port = 35765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl: host.baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const inferAttempts = attempts.filter((entry) => entry.request?.schema === 'hg_assembled_request_v1');
  assert.ok(inferAttempts.length >= 3);
  for (const attempt of inferAttempts) {
    const timing = attempt.inference_health?.timing;
    assert.ok(timing, `missing timing on ${attempt.evidence_id}`);
    assert.equal(timing.timing_observed, true);
    assert.equal(timing.measurement, 'dsh_session_turn_boundary');
    assert.equal(typeof timing.inference_wall_clock_ms, 'number');
    assert.ok(timing.started_at);
    assert.ok(timing.ended_at);
    assert.equal(timing.dsh_inference_session_id, attempt.correlation.dsh_inference_session_id);
  }
});

test('execution span serial A→B→C reconstruction', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-span-158-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const recorder = new ExecutionEvidenceRecorder({ enabled: true, root });
  const tracker = new ExecutionSpanTracker(recorder, {
    hgSessionId: 'sess-span',
    operationId: 'op-span',
    hgRoundId: 'round-span',
  });

  const spanA = tracker.beginSpan('phase_a');
  const spanB = tracker.beginSpan('phase_b', { parentSpanId: spanA });
  const spanC = tracker.beginSpan('phase_c', { parentSpanId: spanB });
  tracker.endSpan(spanA);
  tracker.endSpan(spanB);
  tracker.endSpan(spanC);

  const store = new ExecutionEvidenceStore(root);
  const index = store.readIndex('sess-span');
  const spanIds = (index.attempt_ids ?? []).filter((id) => {
    const attempt = store.readAttempt('sess-span', id);
    return attempt?.correlation?.role === 'execution_span';
  });
  assert.equal(spanIds.length, 3);
  const spans = spanIds.map((id) => store.readAttempt('sess-span', id));
  const byPhase = new Map(spans.map((span) => [span.correlation.phase_id, span]));
  assert.equal(byPhase.get('phase_b').correlation.parent_span_id, byPhase.get('phase_a').correlation.span_id);
  assert.equal(byPhase.get('phase_c').correlation.parent_span_id, byPhase.get('phase_b').correlation.span_id);
  for (const span of spans) {
    assert.equal(span.correlation.role, 'execution_span');
    assert.ok(span.execution?.started_at);
    assert.ok(span.execution?.ended_at);
    assert.equal(typeof span.execution?.wall_ms, 'number');
    assert.equal(span.correlation.operation_id, 'op-span');
    assert.equal(span.correlation.hg_round_id, 'round-span');
  }
});

test('patch preserves authoritative inference timing', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-timing-immut-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const store = new ExecutionEvidenceStore(root);
  const evidenceId = 'ev-timing-immut';
  const timing = {
    timing_observed: true,
    measurement: 'dsh_session_turn_boundary',
    inference_wall_clock_ms: 42,
    started_at: '2026-01-01T00:00:00.000Z',
    ended_at: '2026-01-01T00:00:00.042Z',
    dsh_turn: 1,
  };
  store.writeAttempt({
    evidence_id: evidenceId,
    correlation: {
      evidence_id: evidenceId,
      hg_session_id: 'sess-immut',
      hg_scene_id: 'sess-immut',
      hg_round_id: 'round-immut',
      role: 'director',
      inference_id: 'inf-immut',
      attempt_index: 0,
    },
    request: { schema: 'hg_assembled_request_v1', contributions: [] },
    response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
    inference_health: { timing },
  });
  store.patchAttempt('sess-immut', evidenceId, {
    decision: { outcome: 'accepted' },
    inference_health: {
      timing: {
        timing_observed: true,
        measurement: 'dsh_session_turn_boundary',
        inference_wall_clock_ms: 0,
        started_at: '2026-02-01T00:00:00.000Z',
        ended_at: '2026-02-01T00:00:00.000Z',
      },
    },
  });
  const patched = store.readAttempt('sess-immut', evidenceId);
  assert.equal(patched.inference_health.timing.inference_wall_clock_ms, 42);
  assert.equal(patched.inference_health.timing.started_at, '2026-01-01T00:00:00.000Z');
});

import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { executionEvidenceRoot, isExecutionEvidenceEnabled } from '../src/lib/execution-evidence/config.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import {
  createTestSession,
  fetchSessionState,
  startDomainApi,
} from './helpers/domain-api.mjs';

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

function makeTempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-data-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
    HG_EXECUTION_EVIDENCE_DIR: process.env.HG_EXECUTION_EVIDENCE_DIR,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  delete process.env.HG_EXECUTION_EVIDENCE_DIR;
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
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
  const attempts = (index.attempt_ids ?? []).map((evidenceId) => JSON.parse(
    fs.readFileSync(path.join(root, 'attempts', `${evidenceId}.json`), 'utf8'),
  ));
  return { index, attempts, root };
}

test('execution evidence config: enabled by default; opt-out disables writes', () => {
  assert.equal(isExecutionEvidenceEnabled({ HG_EXECUTION_EVIDENCE: 'on' }), true);
  assert.equal(isExecutionEvidenceEnabled({ HG_EXECUTION_EVIDENCE: 'off' }), false);
  assert.equal(isExecutionEvidenceEnabled({ HG_EXECUTION_EVIDENCE: '0' }), false);
});

test('execution evidence store: atomic attempt + index writes', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-evidence-'));
  const store = new ExecutionEvidenceStore(root);
  const evidenceId = 'ev-1';
  store.writeAttempt({
    evidence_id: evidenceId,
    correlation: {
      evidence_id: evidenceId,
      hg_session_id: 'sess-1',
      hg_scene_id: 'sess-1',
      hg_round_id: 'round-1',
      role: 'director',
      inference_id: 'inf-1',
      attempt_index: 0,
    },
    request: { schema: 'hg_assembled_request_v1', contributions: [{ content: 'alpha' }] },
    response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
  });
  const attempt = store.readAttempt('sess-1', evidenceId);
  assert.equal(attempt.request.contributions[0].content, 'alpha');
  const index = store.readIndex('sess-1');
  assert.deepEqual(index.rounds['round-1'], [evidenceId]);
  fs.rmSync(root, { recursive: true, force: true });
});

test('full round writes execution evidence with request, response, and correlation', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = 24765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const { index, attempts, root } = readAttempts(dataDir, result.hg_session_id);
  assert.ok(fs.existsSync(root));
  assert.ok(index.attempt_ids.length >= 3);
  assert.ok(index.rounds[result.hg_round_id]?.length >= 3);

  const directorAttempt = attempts.find((entry) => entry.correlation.role === 'director');
  const characterAttempt = attempts.find((entry) => entry.correlation.role === 'character');
  const narratorAttempt = attempts.find((entry) => entry.correlation.role === 'narrator');

  assert.ok(directorAttempt);
  assert.equal(directorAttempt.request.schema, 'hg_assembled_request_v1');
  assert.ok(directorAttempt.request.contributions.length > 0);
  assert.equal(directorAttempt.response.schema, 'hg_model_response_v1');
  assert.equal(directorAttempt.decision.outcome, 'accepted');
  assert.equal(directorAttempt.decision.director.selected_character_id, 'Alice');

  assert.ok(characterAttempt);
  assert.equal(characterAttempt.decision.outcome, 'accepted');
  assert.equal(characterAttempt.associations.domain_commit_id, result.domain_commit_id);

  assert.ok(narratorAttempt);
  assert.equal(narratorAttempt.decision.inference_outcome, 'succeeded');
  assert.equal(narratorAttempt.associations.domain_commit_id, result.domain_commit_id);
});

test('director rejection retry chain is durable', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = 25765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [
      JSON.stringify({ next_actor: 'Zelda', end_round: false, reason: 'bad pick' }),
      JSON.stringify(VALID_DIRECTOR),
    ],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const directorAttempts = attempts
    .filter((entry) => entry.correlation.role === 'director')
    .sort((left, right) => left.correlation.attempt_index - right.correlation.attempt_index);
  assert.equal(directorAttempts.length, 2);
  assert.equal(directorAttempts[0].decision.outcome, 'rejected');
  assert.equal(directorAttempts[1].correlation.prior_attempt_id, directorAttempts[0].evidence_id);
  assert.equal(directorAttempts[1].decision.outcome, 'accepted');
});

test('stored assembled request preserves served contribution text without reprojection', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = 26765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const characterAttempt = attempts.find((entry) => entry.correlation.role === 'character');
  const attemptPath = path.join(
    dataDir,
    'execution_evidence',
    result.hg_session_id,
    'attempts',
    `${characterAttempt.evidence_id}.json`,
  );
  const stored = JSON.parse(fs.readFileSync(attemptPath, 'utf8'));
  assert.ok((stored.request.contributions ?? []).length > 0);
  assert.ok(stored.request.contributions.every((entry) => typeof entry.content === 'string'));
  assert.ok(stored.request.user_instruction.text.length > 0);
  assert.equal(stored.request.schema, 'hg_assembled_request_v1');
});

test('restart reconstruction uses durable evidence only', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = 27765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });
  await ctx.fiber.dispose();

  const { attempts, index } = readAttempts(dataDir, result.hg_session_id);
  assert.ok(attempts.length >= 3);
  assert.ok(index.rounds[result.hg_round_id]);
  const director = attempts.find((entry) => entry.correlation.role === 'director');
  assert.ok(director.request.user_instruction.text.length > 0);
  assert.ok(director.response.assistant_text.includes('Alice'));
});

test('opt-out disables evidence without changing RP behavior', async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-data-off-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'off';
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const port = 28765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });
  const state = await fetchSessionState(baseUrl, result.hg_session_id);
  assert.equal(state.turn_counter, 1);
  assert.equal(
    fs.existsSync(path.join(dataDir, 'execution_evidence', result.hg_session_id)),
    false,
  );
});

test('evidence payloads exclude API key material', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const previousKey = process.env.DEEPSEEK_API_KEY;
  process.env.DEEPSEEK_API_KEY = 'sk-test-should-not-appear-in-evidence';
  t.after(() => {
    if (previousKey === undefined) delete process.env.DEEPSEEK_API_KEY;
    else process.env.DEEPSEEK_API_KEY = previousKey;
  });

  const port = 29765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
  });

  const evidenceRoot = path.join(dataDir, 'execution_evidence', result.hg_session_id, 'attempts');
  const serialized = fs.readdirSync(evidenceRoot)
    .map((name) => fs.readFileSync(path.join(evidenceRoot, name), 'utf8'))
    .join('\n');
  assert.equal(serialized.includes('sk-test-should-not-appear-in-evidence'), false);
  assert.equal(executionEvidenceRoot({ HG_DATA_DIR: dataDir }).includes('execution_evidence'), true);
});

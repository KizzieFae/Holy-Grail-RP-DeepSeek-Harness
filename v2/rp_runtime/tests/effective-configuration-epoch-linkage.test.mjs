import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { ExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import {
  appendEffectiveConfigurationEpoch,
  createEffectiveConfigurationEpoch,
} from '../src/lib/runtime-configuration-provenance.mjs';
import {
  createTestSession,
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
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-epoch-'));
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

function llmAttempts(attempts) {
  return attempts.filter((entry) => entry.request?.schema === 'hg_assembled_request_v1');
}

test('correlation records effective_configuration_epoch_id from evidence context', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-epoch-correlation-'));
  const recorder = new ExecutionEvidenceRecorder({ enabled: true, root });
  const evidenceId = recorder.recordInferenceAttempt({
    evidenceContext: {
      hgSessionId: 'sess-epoch',
      hgSceneId: 'sess-epoch',
      hgRoundId: 'round-1',
      role: 'director',
      inferenceId: 'inf-1',
      attemptIndex: 0,
      effectiveConfigurationEpochId: 'epoch-test-1',
    },
    manifest: { manifest_id: 'manifest-1', inference_kind: 'director_decision' },
    contextRegistration: { manifestId: 'manifest-1', contributionIds: [] },
    prompt: 'prompt',
    profile: { kind: 'mock', provider: 'mock', model: 'mock' },
    trace: { assistant_text: '{}', failed: false },
    assistantText: '{}',
    inferenceSessionId: 'dsh-1',
  });
  const attempt = recorder.readAttempt('sess-epoch', evidenceId);
  assert.equal(attempt.correlation.effective_configuration_epoch_id, 'epoch-test-1');
  fs.rmSync(root, { recursive: true, force: true });
});

test('configuration epochs append on fingerprint change for settings and round overrides', () => {
  const initial = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'mock' },
    options: { inferenceMode: 'mock' },
    effectiveFrom: 'session_open',
    epochId: 'epoch-open',
  });
  let config = appendEffectiveConfigurationEpoch(null, initial);
  assert.equal(config.current_epoch_id, 'epoch-open');

  const settingsUpdate = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'live', model: 'deepseek-chat' },
    options: { inferenceMode: 'live' },
    effectiveFrom: 'settings_update',
    epochId: 'epoch-settings',
  });
  config = appendEffectiveConfigurationEpoch(config, settingsUpdate);
  assert.equal(config.epochs.length, 2);
  assert.equal(config.current_epoch_id, 'epoch-settings');

  const roundOverride = createEffectiveConfigurationEpoch({
    settings: { inferenceMode: 'live', model: 'deepseek-reasoner' },
    options: { inferenceMode: 'live', model: 'deepseek-reasoner' },
    effectiveFrom: 'round_options_override',
    epochId: 'epoch-round-override',
  });
  config = appendEffectiveConfigurationEpoch(config, roundOverride);
  assert.equal(config.epochs.length, 3);
  assert.equal(config.current_epoch_id, 'epoch-round-override');
});

test('full round stamps LLM attempts with governing effective configuration epoch', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = 25765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const epochId = 'epoch-integration-1';
  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    effectiveConfigurationEpochId: epochId,
  });

  const { attempts } = readAttempts(dataDir, result.hg_session_id);
  const llm = llmAttempts(attempts);
  assert.ok(llm.length >= 3);
  for (const attempt of llm) {
    assert.equal(
      attempt.correlation.effective_configuration_epoch_id,
      epochId,
      `missing epoch on ${attempt.correlation.role}/${attempt.correlation.inference_kind ?? 'default'}`,
    );
  }
});

test('epoch change between rounds is reflected on later LLM attempts', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const port = 26765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const created = await createTestSession(baseUrl, { cast: ['Alice'] });
  const hgSessionId = created.hg_session_id;

  const round1 = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: hgSessionId },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    effectiveConfigurationEpochId: 'epoch-round-a',
  });

  const round2 = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'open', hg_session_id: hgSessionId },
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockCharacterTurnResponses: [[JSON.stringify(VALID_MOVE)]],
    effectiveConfigurationEpochId: 'epoch-round-b',
  });

  const { attempts } = readAttempts(dataDir, hgSessionId);
  const round1Llm = llmAttempts(attempts.filter(
    (entry) => entry.correlation.hg_round_id === round1.hg_round_id,
  ));
  const round2Llm = llmAttempts(attempts.filter(
    (entry) => entry.correlation.hg_round_id === round2.hg_round_id,
  ));
  assert.ok(round1Llm.length >= 1);
  assert.ok(round2Llm.length >= 1);
  for (const attempt of round1Llm) {
    assert.equal(attempt.correlation.effective_configuration_epoch_id, 'epoch-round-a');
  }
  for (const attempt of round2Llm) {
    assert.equal(attempt.correlation.effective_configuration_epoch_id, 'epoch-round-b');
  }
});

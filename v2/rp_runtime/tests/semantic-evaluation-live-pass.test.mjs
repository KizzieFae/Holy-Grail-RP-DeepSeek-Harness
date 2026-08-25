import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile, mockInferenceProfile } from '../src/lib/inference-profile.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';
import { findCharacterMoveAttempt } from './helpers/character-cognition-mock.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods quietly' }],
  motivation: {
    goal: 'acknowledge',
    tactic: 'subtle gesture',
    emotional_driver: 'calm',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

test('live semantic evaluator inference through Character phase (bounded pass)', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 180_000,
}, async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-live-semantic-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
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

  const port = 25765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port, { sessionsDir });
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { mountDeepSeek: true },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice'], location: 'Dorm' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });

  const sceneEvents = [];
  const sceneAgent = {
    session: {
      append(type, payload) {
        sceneEvents.push({ type, payload });
      },
    },
  };

  const characterTurn = await phaseExecutors.runCharacter({
    api,
    sceneAgent,
    sceneSessionId: 'scene-live-semantic',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    directorDecision: { next_actor: 'Alice', end_round: false },
    characterInferenceId: 'inf-live-semantic-char',
    mockResponses: [JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [],
    modelProfile: mockInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile({
      reasoningEffort: 'low',
      maxTokens: 512,
    }),
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });

  assert.equal(characterTurn.committed, true, 'expected commit after live semantic evaluation');
  assert.equal(characterTurn.generatedCandidateCount, 1);

  const semanticEvent = sceneEvents.find((event) => event.type === 'hg/semantic-evaluation');
  assert.ok(semanticEvent, 'expected semantic evaluation trace event');
  assert.ok(
    ['pass', 'reject_soft'].includes(String(semanticEvent.payload?.overall_result ?? ''))
      || semanticEvent.payload?.findings?.length === 0,
    `unexpected semantic outcome: ${JSON.stringify(semanticEvent.payload)}`,
  );

  const evidenceRoot = path.join(dataDir, 'execution_evidence', session.hg_session_id);
  const index = JSON.parse(fs.readFileSync(path.join(evidenceRoot, 'index.json'), 'utf8'));
  const attempts = (index.attempt_ids ?? []).map((evidenceId) => JSON.parse(
    fs.readFileSync(path.join(evidenceRoot, 'attempts', `${evidenceId}.json`), 'utf8'),
  ));

  const characterAttempt = findCharacterMoveAttempt(attempts);
  assert.ok(characterAttempt);
  assert.equal(characterAttempt.decision?.outcome, 'accepted');
  assert.ok(characterAttempt.decision?.parse?.proposed_move);
  assert.ok(characterAttempt.response?.assistant_text);
  assert.ok(characterAttempt.decision?.semantic_evaluation?.result);

  const evaluatorAttempts = attempts.filter((attempt) => attempt.correlation?.role === 'semantic_evaluator');
  assert.equal(evaluatorAttempts.length, 1, 'expected one live semantic evaluator attempt');
  assert.ok(evaluatorAttempts[0].response?.assistant_text?.length > 0, 'expected evaluator raw output');
  assert.equal(evaluatorAttempts[0].correlation.prior_attempt_id, characterAttempt.evidence_id);
  assert.equal(
    evaluatorAttempts[0].response?.provider ?? evaluatorAttempts[0].request?.inference_profile?.provider,
    'deepseek-official',
  );
});

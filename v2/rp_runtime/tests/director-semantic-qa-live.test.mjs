import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { runDirectorPhase } from '../src/plugins/hg-phase-executors/director-phase.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

const MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'responds thoughtfully' }],
  motivation: {
    goal: 'answer',
    tactic: 'direct reply',
    emotional_driver: 'curious',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_JSON = (name) => JSON.stringify({
  next_actor: name,
  end_round: false,
  reason: `${name} should respond next based on scene flow.`,
  environment_event: '',
  tension_shift: 'steady',
});

test('live director semantic QA: user addressee vs wrong next_actor (production path)', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 240_000,
}, async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-live-director-qa-'));
  const sessionsDir = path.join(dataDir, 'sessions');
  fs.mkdirSync(sessionsDir, { recursive: true });
  const previous = {
    HG_DATA_DIR: process.env.HG_DATA_DIR,
    HG_EXECUTION_EVIDENCE: process.env.HG_EXECUTION_EVIDENCE,
  };
  process.env.HG_DATA_DIR = dataDir;
  process.env.HG_EXECUTION_EVIDENCE = 'on';
  t.after(() => {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    fs.rmSync(dataDir, { recursive: true, force: true });
  });

  const port = 26765 + Math.floor(Math.random() * 1000);
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

  const session = await api.createSession({ cast: ['Alice', 'Bob'], location: 'Common room' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  await api.recordUserTurn({
    hg_session_id: session.hg_session_id,
    content: 'Bob, what do you think about this?',
    hg_round_id: round.hg_round_id,
  });

  const sceneEvents = [];
  const sceneAgent = {
    session: {
      append(type, payload) {
        sceneEvents.push({ type, payload });
      },
    },
  };

  const directorResult = await phaseExecutors.runDirector({
    api,
    sceneAgent,
    sceneSessionId: 'scene-live-director-qa-addressee',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    directorInferenceId: 'inf-live-director-addressee',
    directorAttemptSeed: 0,
    mockDirectorResponses: [DIRECTOR_JSON('Alice')],
    mockDirectorSemanticQaResponses: [],
    directorResponseIndex: 0,
    actorsUsedThisRound: [],
    turnIndex: round.turn_index,
    eligibilitySnapshot: null,
    participationContext: null,
    modelProfile: deepseekInferenceProfile(),
    liveMaxAttempts: 2,
    directorSemanticQaEnabled: true,
    semanticEvaluatorProfile: deepseekInferenceProfile(),
  });

  assert.equal(directorResult.accepted, true, 'director selection should complete after QA policy');
  const qaEvents = sceneEvents.filter((e) => e.type === 'hg/director-semantic-qa');
  assert.ok(qaEvents.length >= 1, 'expected semantic QA trace event');
  const qaEvent = qaEvents[0];
  assert.equal(qaEvent.payload.evaluation_pass_id, 'inf-live-director-addressee-qa-0');
  assert.ok(qaEvent.payload.overall_result, 'live evaluator should return overall_result');

  const ctxResp = await api.prepareDirectorSemanticQaContext({
    hg_scene_id: session.hg_scene_id,
    hg_round_id: round.hg_round_id,
    inference_id: 'inf-live-director-addressee',
    turn_index: round.turn_index,
    evaluation_pass_id: 'probe-addressee',
    candidate_decision: {
      next_actor: 'Alice',
      end_round: false,
      reason: 'Alice should speak.',
      environment_event: '',
      tension_shift: 'steady',
    },
    raw_model_output: DIRECTOR_JSON('Alice'),
    actors_used_this_round: [],
  });
  const kinds = new Set((ctxResp.contributions ?? []).map((c) => c.source_kind));
  assert.ok(kinds.has('user_turn_source'), 'QA manifest must include authoritative user source');
  const userRef = (ctxResp.authority_references ?? []).find((r) => String(r.ref_id ?? '').startsWith('user:'));
  assert.ok(userRef, 'authority refs must include user source ref');
  assert.equal(userRef.authority_class, 'authoritative');
  assert.match(String(userRef.text ?? ''), /Bob/i);
});

test('director semantic QA soft path: controlled policy with correction context', async (t) => {
  const port = 27765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const softReject = JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: 'inf-soft-live-qa-0',
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'dir_reason_coherence',
      severity: 'soft',
      finding: 'Reason too thin for the steering context',
      rationale: 'controlled policy fixture',
    }],
  });
  const pass = JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: 'inf-soft-live-qa-1',
    overall_result: 'pass',
    findings: [],
  });
  const directorResponses = [DIRECTOR_JSON('Alice'), DIRECTOR_JSON('Alice')];
  const semanticResponses = [softReject, pass];

  let correctionSeen = false;
  let directorInferenceCount = 0;
  const sceneEvents = [];
  const sceneAgent = {
    session: {
      append(type, payload) {
        sceneEvents.push({ type, payload });
      },
    },
  };

  const apiWrapper = createDomainApiClient(host.baseUrl);
  const trackingApi = {
    ...apiWrapper,
    async prepareDirectorContext(body) {
      if (body.correction_context) correctionSeen = true;
      return apiWrapper.prepareDirectorContext(body);
    },
  };

  const session = await api.createSession({ cast: ['Alice', 'Bob'], location: 'Hall' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });

  const result = await runDirectorPhase({
    runEphemeralInference: async (args) => {
      if (args.evidenceContext?.role === 'semantic_evaluator') {
        const passId = args.evidenceContext.evaluationPassId ?? '';
        const index = passId.endsWith('-qa-0') ? 0 : 1;
        return {
          failed: false,
          raw: semanticResponses[index],
          evidenceId: `eval-evidence-${index}`,
          inferenceSessionId: `eval-sess-${index}`,
          trace: { provider: 'mock', failed: false },
        };
      }
      const raw = directorResponses[directorInferenceCount];
      directorInferenceCount += 1;
      return {
        failed: false,
        raw,
        evidenceId: `director-evidence-${directorInferenceCount}`,
        inferenceSessionId: `director-sess-${directorInferenceCount}`,
        trace: { provider: 'mock', failed: false },
      };
    },
    recorder: phaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    api: trackingApi,
    sceneAgent,
    sceneSessionId: 'scene-soft-policy',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    directorInferenceId: 'inf-soft-live',
    directorAttemptSeed: 0,
    mockDirectorResponses: directorResponses,
    mockDirectorSemanticQaResponses: semanticResponses,
    directorResponseIndex: 0,
    actorsUsedThisRound: [],
    turnIndex: round.turn_index,
    eligibilitySnapshot: null,
    participationContext: null,
    modelProfile: deepseekInferenceProfile(),
    liveMaxAttempts: 3,
    directorSemanticQaEnabled: true,
    semanticEvaluatorProfile: deepseekInferenceProfile(),
  });

  assert.equal(result.accepted, true);
  assert.equal(directorInferenceCount, 2, 'soft reject should trigger one director regeneration');
  assert.equal(correctionSeen, true, 'soft reject should trigger one regeneration with correction context');
  const qaEvents = sceneEvents.filter((e) => e.type === 'hg/director-semantic-qa');
  assert.ok(qaEvents.length >= 2);
  assert.equal(qaEvents[0].payload.policy_action, 'soft_regen');
  assert.ok(
    qaEvents.some((e) => e.payload.policy_action === 'pass' || e.payload.overall_result === 'pass'),
  );
});

test('participation-direct bypasses director semantic QA (production orchestrator path)', async (t) => {
  const port = 28765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const { baseUrl } = host;
  t.after(() => host.stop());

  const { ctx, orchestrator } = await createHolyGrailRpContext({ domainApi: { baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const result = await orchestrator.runRound({
    domainApi: { baseUrl },
    session: { mode: 'create', cast: ['Alice'] },
    forcedDesignation: 'Alice',
    mockDirectorResponses: [DIRECTOR_JSON('Bob')],
    mockCharacterTurnResponses: [[JSON.stringify(MOVE)]],
    directorSemanticQaEnabled: true,
  });

  assert.equal(result.character_turn_count, 1);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/director-proposed'), false);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/director-semantic-qa'), false);
  assert.equal(result.scene_events.some((e) => e.type === 'hg/director-accepted'), false);
});

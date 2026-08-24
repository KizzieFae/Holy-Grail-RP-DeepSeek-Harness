import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { runNarratorPhase } from '../src/plugins/hg-phase-executors/narrator-phase.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

const ACTION_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'examines the ledger carefully' }],
  motivation: {
    goal: 'verify the accounts',
    tactic: 'close reading',
    emotional_driver: 'focused',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const DIRECTOR_JSON = JSON.stringify({
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should act next.',
  environment_event: '',
  tension_shift: 'steady',
});

async function commitAliceMove(api, sessionId, roundId) {
  const validation = await api.validateDirectorDecision({
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    inference_id: 'inf-director-narrator-live',
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: JSON.parse(DIRECTOR_JSON),
  });
  assert.equal(validation.accepted, true);
  const commit = await api.commitMove({
    inference_id: 'inf-commit-narrator-live',
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    character_id: 'Alice',
    validated_move: ACTION_MOVE,
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  assert.equal(commit.committed, true);
  return commit;
}

function sceneAgentCollector(events) {
  return {
    session: {
      append(type, payload) {
        events.push({ type, payload });
      },
    },
  };
}

test('live narrator semantic QA: faithful paraphrase accepted (production path)', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 240_000,
}, async (t) => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-live-narrator-qa-paraphrase-'));
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

  const port = 29765 + Math.floor(Math.random() * 1000);
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

  const session = await api.createSession({ cast: ['Alice'], location: 'Study' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const sceneEvents = [];
  const sceneAgent = sceneAgentCollector(sceneEvents);

  const result = await phaseExecutors.runNarrator({
    api,
    sceneAgent,
    sceneSessionId: 'scene-live-narrator-paraphrase',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-live-narrator-paraphrase',
    mockNarratorResponses: [],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
    prompt: 'Render the committed character move as scene narration only. Paraphrase is allowed.',
  });

  assert.equal(result.presentation_rendered, true, result.presentation_failure_reason ?? 'narrator failed');
  assert.ok(result.presentation_text);
  assert.ok(sceneEvents.some((event) => event.type === 'hg/narrator-semantic-qa'));
  const qaEvent = sceneEvents.find((event) => event.type === 'hg/narrator-semantic-qa');
  assert.ok(['pass', 'accept_with_residuals'].includes(qaEvent.payload.policy_action)
    || qaEvent.payload.overall_result === 'pass');
});

test('live narrator semantic QA: stylistically distant faithful candidate accepted', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 240_000,
}, async (t) => {
  const port = 30765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { mountDeepSeek: true },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice'], location: 'Archive' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const distantProse = (
    'In the hush of the archive, Alice bent over the ledger with scholarly intensity, '
    + 'tracing columns of ink as though the numbers themselves might confess some hidden truth.'
  );
  const sceneEvents = [];
  const result = await runNarratorPhase({
    api,
    runEphemeralInference: async (args) => {
      if (args.evidenceContext?.role === 'semantic_evaluator') {
        return ctx.hgPhaseExecutors.runEphemeralInference(args);
      }
      return {
        evidenceId: 'ev-narrator',
        inferenceSessionId: 'is-narrator',
        raw: distantProse,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-live-narrator-distant',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-live-narrator-distant',
    mockNarratorResponses: [distantProse],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
    prompt: 'Render the committed character move as scene narration only.',
  });

  assert.equal(result.presentation_rendered, true, result.presentation_failure_reason ?? 'narrator failed');
  assert.equal(result.presentation_text, distantProse);
  assert.ok(sceneEvents.some((event) => event.type === 'hg/narrator-semantic-qa'));
});

test('controlled narrator semantic QA: attribution hard reject uses committed fallback', async (t) => {
  const port = 31765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice', 'Bob'], location: 'Hall' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const attributionCandidate = 'Bob examined the ledger carefully, tracing each column in silence.';
  const hardReject = (passId) => JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'nar_attribution_error',
      severity: 'hard',
      finding: 'Action assigned to Bob but committed actor is Alice',
      rationale: 'controlled attribution fixture',
      authoritative_citation: { ref_id: `commit:${commit.domain_commit_id}` },
    }],
  });

  const sceneEvents = [];
  const result = await runNarratorPhase({
    api,
    runEphemeralInference: async ({ mockResponses, evidenceContext }) => ({
      evidenceId: evidenceContext?.role === 'semantic_evaluator' ? 'ev-eval' : 'ev-narrator',
      inferenceSessionId: 'is-1',
      raw: mockResponses?.[0] ?? attributionCandidate,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-controlled-attribution',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-controlled-attribution',
    mockNarratorResponses: [attributionCandidate, attributionCandidate],
    mockNarratorSemanticQaResponses: [
      hardReject('inf-controlled-attribution-qa-0'),
      hardReject('inf-controlled-attribution-qa-1'),
    ],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
  });

  assert.equal(result.presentation_rendered, false);
  assert.equal(result.presentation_failed, true);
  assert.equal(result.terminal_disposition, 'committed_fallback');
  assert.equal(sceneEvents.some((event) => event.type === 'hg/narrator-completed'), false);
});

test('controlled narrator semantic QA: derived-only hard citation does not hard-reject', async (t) => {
  const port = 32765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx } = await createHolyGrailRpContext({ domainApi: { baseUrl: host.baseUrl } });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice'], location: 'Study' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const prose = 'Alice examined the ledger carefully, tracing each column in silence.';
  const derivedHard = (passId) => JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'nar_committed_contradiction',
      severity: 'hard',
      finding: 'Contradicts derived director orchestration only',
      rationale: 'controlled derived-only fixture',
      authoritative_citation: { ref_id: `orch:round:${round.hg_round_id}` },
    }],
  });

  const sceneEvents = [];
  const result = await runNarratorPhase({
    api,
    runEphemeralInference: async ({ mockResponses, evidenceContext }) => ({
      evidenceId: evidenceContext?.role === 'semantic_evaluator' ? 'ev-eval' : 'ev-narrator',
      inferenceSessionId: 'is-1',
      raw: mockResponses?.[0] ?? prose,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-derived-only',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-derived-only',
    mockNarratorResponses: [prose, prose],
    mockNarratorSemanticQaResponses: [
      derivedHard('inf-derived-only-qa-0'),
      derivedHard('inf-derived-only-qa-1'),
    ],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(result.terminal_disposition, 'accepted_with_residual_soft_concerns');
  const qaEvents = sceneEvents.filter((event) => event.type === 'hg/narrator-semantic-qa');
  assert.ok(qaEvents.length >= 2);
  assert.equal(qaEvents[0].payload.policy_action, 'soft_regen');
  assert.equal(qaEvents[1].payload.policy_action, 'accept_with_residuals');
  assert.ok(qaEvents.every((event) => event.payload.policy_action !== 'hard_regen'));
  assert.ok(qaEvents.every((event) => event.payload.policy_action !== 'exhausted_fallback'));
});

test('live narrator semantic QA: unsupported interior claim can hard-reject', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 240_000,
}, async (t) => {
  const port = 33765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  const api = createDomainApiClient(host.baseUrl);
  t.after(() => host.stop());

  const { ctx } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { mountDeepSeek: true },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice'], location: 'Study' });
  const round = await api.startRound({ hg_scene_id: session.hg_scene_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const inventedInterior = (
    'Alice examined the ledger, already knowing her brother had forged the final entry last winter.'
  );
  const sceneEvents = [];

  const result = await runNarratorPhase({
    api,
    runEphemeralInference: async (args) => {
      if (args.evidenceContext?.role === 'semantic_evaluator') {
        return ctx.hgPhaseExecutors.runEphemeralInference(args);
      }
      return {
        evidenceId: 'ev-narrator',
        inferenceSessionId: 'is-narrator',
        raw: inventedInterior,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
    recorder: ctx.hgPhaseExecutors.executionEvidenceRecorder,
    trace: ctx.hgTraceEmitter,
    sceneAgent: sceneAgentCollector(sceneEvents),
    sceneSessionId: 'scene-live-psych-invention',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_scene_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-live-psych-invention',
    mockNarratorResponses: [inventedInterior, inventedInterior],
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: deepseekInferenceProfile(),
    semanticEvaluatorProfile: deepseekInferenceProfile(),
    narratorSemanticQaEnabled: true,
  });

  const qaEvents = sceneEvents.filter((event) => event.type === 'hg/narrator-semantic-qa');
  assert.ok(qaEvents.length >= 1, 'expected live semantic evaluator invocation');
  if (result.presentation_rendered) {
    assert.ok(
      qaEvents.some((event) => event.payload.overall_result === 'pass'
        || event.payload.policy_action === 'accept_with_residuals'),
      'if accepted, evaluator should not have authoritative hard reject',
    );
  } else {
    assert.equal(result.terminal_disposition, 'committed_fallback');
  }
});

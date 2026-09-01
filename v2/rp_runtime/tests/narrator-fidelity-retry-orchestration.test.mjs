import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createDomainApiClient } from '../src/lib/domain-api-client.mjs';
import { patchNarratorTerminalPresentationEvidence } from '../src/lib/execution-evidence/narrator-terminal-evidence.mjs';
import { mockInferenceProfile } from '../src/lib/inference-profile.mjs';
import { runNarratorPhase } from '../src/plugins/hg-phase-executors/narrator-phase.mjs';
import { startDomainApi } from './helpers/domain-api.mjs';

const SPEECH_MOVE = {
  move_schema_version: 2,
  beats: [
    {
      type: 'speech',
      dialogue: 'Keep your voice down, Bob.',
      audibility: 'directed',
      audience: ['Bob'],
    },
  ],
  motivation: {
    goal: 'warn quietly',
    tactic: 'hushed tone',
    emotional_driver: 'alert',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

const REQUIRED_DIALOGUE = 'Keep your voice down, Bob.';
const REJECTED_PROSE_0 = 'Alice leaned closer, speaking far too loudly for the room.';
const REJECTED_PROSE_1 = 'She shot Bob a warning look but never repeated the line.';
const ACCEPTED_PROSE = `Alice murmured, "${REQUIRED_DIALOGUE}," glancing toward the door.`;

const DIRECTOR_JSON = JSON.stringify({
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should act next.',
  environment_event: '',
  tension_shift: 'steady',
});

function makeTempDataEnv(t) {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-narrator-fidelity-'));
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
  return { index, attempts };
}

function narratorMainAttempts(attempts) {
  return attempts
    .filter((entry) => entry.correlation.role === 'narrator'
      && entry.correlation.inference_kind !== 'narrator_environment_cognition')
    .sort((left, right) => left.correlation.attempt_index - right.correlation.attempt_index);
}

function semanticCorrectionContribution(attempt) {
  return (attempt.request?.contributions ?? []).find(
    (entry) => entry.source_kind === 'semantic_correction',
  );
}

async function commitAliceMove(api, sessionId, roundId) {
  const validation = await api.validateDirectorDecision({
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    inference_id: 'inf-director-fidelity-retry',
    turn_index: 0,
    attempt_index: 0,
    proposed_decision: JSON.parse(DIRECTOR_JSON),
  });
  assert.equal(validation.accepted, true);
  const commit = await api.commitMove({
    inference_id: 'inf-commit-fidelity-retry',
    hg_scene_id: sessionId,
    hg_round_id: roundId,
    character_id: 'Alice',
    validated_move: SPEECH_MOVE,
    director_decision: validation.normalized_decision,
    expected_turn_index: 0,
  });
  assert.equal(commit.committed, true);
  return commit;
}

function createTrace() {
  const events = [];
  return {
    events,
    emit(_session, type, _scope, payload) {
      events.push({ type, payload });
    },
  };
}

function createNarratorResponseInference(runEphemeralInference, responses) {
  let narratorCallIndex = 0;
  return async (params) => {
    const inferenceKind = params.evidenceContext?.inferenceKind;
    if (inferenceKind === 'narrator_environment_cognition') {
      return runEphemeralInference(params);
    }
    const wrapped = {
      ...params,
      mockResponses: [responses[narratorCallIndex] ?? responses[responses.length - 1]],
    };
    narratorCallIndex += 1;
    return runEphemeralInference(wrapped);
  };
}

test('runNarratorPhase fidelity retry then success records full evidence chain', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const host = await startDomainApi(undefined, { t, sessionsDir });
  const api = createDomainApiClient(host.baseUrl);
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice', 'Bob'] });
  const round = await api.startRound({ hg_scene_id: session.hg_session_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const prepareCalls = [];
  const originalPrepare = api.prepareNarratorContext.bind(api);
  api.prepareNarratorContext = async (body) => {
    prepareCalls.push(body);
    return originalPrepare(body);
  };

  const result = await runNarratorPhase({
    api,
    runEphemeralInference: createNarratorResponseInference(
      phaseExecutors.runEphemeralInference.bind(phaseExecutors),
      [REJECTED_PROSE_0, ACCEPTED_PROSE],
    ),
    trace: createTrace(),
    recorder: phaseExecutors.executionEvidenceRecorder,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'fidelity-retry-success',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_session_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-narrator-fidelity-success',
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: mockInferenceProfile(),
    narratorSemanticQaEnabled: false,
    prompt: null,
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(prepareCalls.length, 2);
  assert.equal(prepareCalls[1].correction_context?.validation_class, 'speech_verbatim');
  assert.deepEqual(
    prepareCalls[1].correction_context?.required_speech_dialogues,
    [REQUIRED_DIALOGUE],
  );

  const { attempts } = readAttempts(dataDir, session.hg_session_id);
  const mainAttempts = narratorMainAttempts(attempts);
  assert.equal(mainAttempts.length, 2);
  assert.equal(mainAttempts[0].decision.validation_class, 'speech_verbatim');
  assert.equal(mainAttempts[0].decision.retry_decision, 'retry');
  assert.ok(mainAttempts[0].decision.fidelity_correction);
  assert.equal(mainAttempts[0].response.assistant_text, REJECTED_PROSE_0);
  assert.equal(mainAttempts[0].decision.candidate_presentation_text, REJECTED_PROSE_0);
  assert.equal(mainAttempts[1].correlation.prior_attempt_id, mainAttempts[0].evidence_id);
  assert.ok(semanticCorrectionContribution(mainAttempts[1]));
  assert.match(
    semanticCorrectionContribution(mainAttempts[1]).content,
    /Keep your voice down, Bob\./,
  );
  assert.equal(mainAttempts[1].decision.validation_accepted, true);
  assert.equal(mainAttempts[1].decision.presentation_text, ACCEPTED_PROSE);
  assert.equal(result.narrator_evidence_id, mainAttempts[1].evidence_id);
});

test('runNarratorPhase fidelity retry then degraded fallback records terminal presentation', async (t) => {
  const { dataDir, sessionsDir } = makeTempDataEnv(t);
  const host = await startDomainApi(undefined, { t, sessionsDir });
  const api = createDomainApiClient(host.baseUrl);
  const { ctx, phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
  });
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  const session = await api.createSession({ cast: ['Alice', 'Bob'] });
  const round = await api.startRound({ hg_scene_id: session.hg_session_id });
  const commit = await commitAliceMove(api, session.hg_session_id, round.hg_round_id);
  const trace = createTrace();

  const result = await runNarratorPhase({
    api,
    runEphemeralInference: createNarratorResponseInference(
      phaseExecutors.runEphemeralInference.bind(phaseExecutors),
      [REJECTED_PROSE_0, REJECTED_PROSE_1],
    ),
    trace,
    recorder: phaseExecutors.executionEvidenceRecorder,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'fidelity-retry-degraded',
    hgSessionId: session.hg_session_id,
    hgSceneId: session.hg_session_id,
    hgRoundId: round.hg_round_id,
    characterId: 'Alice',
    domainCommitId: commit.domain_commit_id,
    continuityTurnIndex: commit.continuity_turn_index,
    narratorInferenceId: 'inf-narrator-fidelity-degraded',
    mockNarratorSemanticQaResponses: [],
    characterTurnIndex: 0,
    modelProfile: mockInferenceProfile(),
    narratorSemanticQaEnabled: false,
    prompt: null,
  });

  assert.equal(result.presentation_rendered, false);
  assert.equal(result.presentation_failed, true);
  assert.equal(result.terminal_disposition, 'committed_fallback');

  const presentationEntry = await api.recordPresentation({
    hg_session_id: session.hg_session_id,
    domain_commit_id: commit.domain_commit_id,
    hg_round_id: round.hg_round_id,
    character_id: 'Alice',
    presentation_text: null,
    presentation_failed: true,
    inference_outcome: result.inference_outcome,
    perceptual_visibility: null,
  });
  assert.equal(presentationEntry.metadata?.presentation_degraded, true);
  assert.equal(presentationEntry.metadata?.presentation_source, 'degraded_deterministic_fallback');
  assert.match(presentationEntry.content, /Keep your voice down, Bob\./);

  patchNarratorTerminalPresentationEvidence(phaseExecutors.executionEvidenceRecorder, {
    hgSessionId: session.hg_session_id,
    narratorEvidenceId: result.narrator_evidence_id,
    presentationEntry,
  });

  const { attempts } = readAttempts(dataDir, session.hg_session_id);
  const mainAttempts = narratorMainAttempts(attempts);
  assert.equal(mainAttempts.length, 2);
  assert.equal(mainAttempts[0].decision.rejected_presentation_text, REJECTED_PROSE_0);
  assert.equal(mainAttempts[1].decision.rejected_presentation_text, REJECTED_PROSE_1);
  assert.ok(mainAttempts[0].decision.fidelity_correction);
  assert.ok(semanticCorrectionContribution(mainAttempts[1]));
  const terminalAttempt = mainAttempts[1];
  assert.equal(terminalAttempt.associations.presentation_entry_id, presentationEntry.entry_id);
  assert.equal(terminalAttempt.decision.terminal_presentation.text, presentationEntry.content);
  assert.equal(terminalAttempt.decision.terminal_presentation.presentation_degraded, true);

  const failedEvent = trace.events.find((event) => event.type === 'hg/narrator-failed');
  assert.equal(failedEvent?.payload?.canon_preserved, true);
});

test('patchNarratorTerminalPresentationEvidence is a no-op when evidence disabled', () => {
  const calls = [];
  const recorder = {
    isEnabled: () => false,
    patchDecision: (...args) => calls.push(args),
  };
  patchNarratorTerminalPresentationEvidence(recorder, {
    hgSessionId: 'scene-1',
    narratorEvidenceId: 'ev-1',
    presentationEntry: { entry_id: 'hist-1', content: 'x', metadata: {} },
  });
  assert.equal(calls.length, 0);
});

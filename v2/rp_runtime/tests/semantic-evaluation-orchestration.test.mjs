import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { runCharacterPhase } from '../src/plugins/hg-phase-executors/character-phase.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';

const PLAYER_AGENCY_GUARDRAIL_ID = 'guardrail:player_agency';

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

const VALID_MOVE_2 = {
  ...VALID_MOVE,
  beats: [{ type: 'action', action: 'smiles warmly' }],
};

function semanticPass() {
  return JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'pass',
    findings: [],
  });
}

function semanticHard(refId = PLAYER_AGENCY_GUARDRAIL_ID) {
  return JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_hard',
    findings: [
      {
        dimension: 'R02b',
        severity: 'hard',
        finding: 'Invented player speech',
        rationale: 'Character spoke for player',
        authoritative_citation: { ref_id: refId },
      },
    ],
    correction_request: { summary: 'Remove invented player speech', dimensions: ['R02b'] },
  });
}

function semanticSoft() {
  return JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_soft',
    findings: [
      {
        dimension: 'R11',
        severity: 'soft',
        finding: 'Repetitive phrasing',
        rationale: 'Near-duplicate beat from prior turn',
      },
    ],
    correction_request: { summary: 'Vary phrasing', dimensions: ['R11'] },
  });
}

function createMockApi({
  turnIndex = 0,
  commitSequence = [{ committed: true, continuity_turn_index: 1, domain_commit_id: 'dc-1' }],
  validationSequence = [{ accepted: true, normalized_move: VALID_MOVE, retryable: false }],
} = {}) {
  let commitIndex = 0;
  let validationIndex = 0;
  const prepareCalls = [];
  return {
    prepareCalls,
    async getSceneState() {
      return { turn_counter: turnIndex };
    },
    async prepareCharacterContext(body) {
      prepareCalls.push(body);
      return {
        manifest_id: `manifest-char-${prepareCalls.length}`,
        inference_id: body.inference_id,
        hg_scene_id: body.hg_scene_id,
        hg_round_id: body.hg_round_id,
        character_id: body.character_id,
        turn_index: body.turn_index,
        attempt_index: body.attempt_index,
        contributions: body.correction_context
          ? [{ source_kind: 'semantic_correction', content: JSON.stringify(body.correction_context) }]
          : [],
      };
    },
    async validateMove(body) {
      const result = validationSequence[validationIndex] ?? validationSequence.at(-1);
      validationIndex += 1;
      return {
        accepted: Boolean(result.accepted),
        validation_class: result.validation_class ?? 'valid',
        reason: result.reason ?? '',
        retryable: Boolean(result.retryable),
        normalized_move: result.normalized_move ?? body.proposed_move,
      };
    },
    async prepareSemanticEvaluationContext(body) {
      return {
        manifest_id: 'manifest-semantic-eval-1',
        inference_id: body.inference_id,
        hg_scene_id: body.hg_scene_id,
        hg_round_id: body.hg_round_id,
        character_id: body.character_id,
        turn_index: body.turn_index,
        evaluation_pass_id: body.evaluation_pass_id,
        authority_references: [{ ref_id: PLAYER_AGENCY_GUARDRAIL_ID }],
        candidate_package: {
          candidate_move: body.candidate_move,
          raw_model_output: body.raw_model_output,
        },
        contributions: [],
      };
    },
    async commitMove() {
      const result = commitSequence[commitIndex] ?? commitSequence.at(-1);
      commitIndex += 1;
      return result;
    },
  };
}

function createMockInference(responses) {
  let index = 0;
  return async ({ mockResponses, role }) => {
    const raw = mockResponses?.[0] ?? responses[index] ?? JSON.stringify(VALID_MOVE);
    if (!mockResponses?.length) index += 1;
    return {
      failed: false,
      raw,
      evidenceId: `ev-${role}-${index}`,
      inferenceSessionId: `sess-${role}-${index}`,
      trace: { role },
    };
  };
}

function createFailingInference(failCount = 1) {
  let calls = 0;
  return async ({ role }) => {
    calls += 1;
    if (calls <= failCount) {
      return { failed: true, failure: 'provider_timeout', evidenceId: `ev-fail-${calls}`, trace: {} };
    }
    return {
      failed: false,
      raw: JSON.stringify(VALID_MOVE),
      evidenceId: `ev-ok-${calls}`,
      inferenceSessionId: `sess-${role}`,
      trace: {},
    };
  };
}

function createRecorderBackedInference(recorder, {
  characterRaw = JSON.stringify(VALID_MOVE),
  semanticOutcomes = [],
} = {}) {
  const roleCalls = { character: 0, semantic_evaluator: 0 };
  const inferenceCalls = [];

  async function runEphemeralInference({
    inferenceId,
    mockResponses,
    role: roleParam,
    evidenceContext,
    manifest,
  }) {
    const role = evidenceContext?.role ?? roleParam;
    roleCalls[role] = (roleCalls[role] ?? 0) + 1;
    inferenceCalls.push({ inferenceId, role, evidenceContext });

    let failed = false;
    let failure = null;
    let raw = '';

    if (role === 'character') {
      raw = mockResponses?.[0] ?? characterRaw;
    } else if (role === 'semantic_evaluator') {
      const idx = roleCalls.semantic_evaluator - 1;
      const outcome = semanticOutcomes[idx] ?? { raw: semanticPass() };
      if (outcome.fail) {
        failed = true;
        failure = outcome.failure ?? 'inference_failed';
        raw = outcome.raw ?? '';
      } else {
        raw = outcome.raw ?? semanticPass();
      }
    }

    const evidenceId = recorder.recordInferenceAttempt({
      evidenceContext,
      manifest: manifest ?? { manifest_id: 'm', contributions: [] },
      contextRegistration: { manifestId: manifest?.manifest_id ?? 'm', contributionIds: [] },
      prompt: 'test',
      profile: { kind: 'mock', provider: 'mock', model: 'mock' },
      trace: { assistant_text: raw, failed },
      assistantText: raw,
      inferenceSessionId: `sess-${inferenceId}`,
    });

    return {
      failed,
      failure,
      raw,
      evidenceId,
      inferenceSessionId: `sess-${inferenceId}`,
      trace: { role, failed },
    };
  }

  return { runEphemeralInference, roleCalls, inferenceCalls };
}

const noopTrace = { emit: () => {} };
const noopSceneAgent = { session: {} };

test('character phase: pass then commit', async () => {
  const api = createMockApi();
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([JSON.stringify(VALID_MOVE)]),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: { next_actor: 'Bob' },
    characterInferenceId: 'inf-char-0',
    mockResponses: [JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [semanticPass()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 1);
  assert.equal(api.prepareCalls.length, 1);
  assert.equal(api.prepareCalls[0].correction_context, undefined);
});

test('character phase: hard then correction then pass', async () => {
  const api = createMockApi({
    validationSequence: [
      { accepted: true, normalized_move: VALID_MOVE },
      { accepted: true, normalized_move: VALID_MOVE_2 },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([
      JSON.stringify(VALID_MOVE),
      JSON.stringify(VALID_MOVE_2),
    ]),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-hard',
    mockResponses: [JSON.stringify(VALID_MOVE), JSON.stringify(VALID_MOVE_2)],
    mockSemanticEvaluatorResponses: [semanticHard(), semanticPass()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 2);
  assert.ok(api.prepareCalls[1].correction_context);
  assert.match(
    JSON.stringify(api.prepareCalls[1].correction_context),
    /Remove invented player speech/,
  );
});

test('character phase: hard persists through candidate ceiling', async () => {
  const api = createMockApi({
    validationSequence: [
      { accepted: true, normalized_move: VALID_MOVE },
      { accepted: true, normalized_move: VALID_MOVE },
      { accepted: true, normalized_move: VALID_MOVE },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([
      JSON.stringify(VALID_MOVE),
      JSON.stringify(VALID_MOVE),
      JSON.stringify(VALID_MOVE),
    ]),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-exhaust',
    mockResponses: [
      JSON.stringify(VALID_MOVE),
      JSON.stringify(VALID_MOVE),
      JSON.stringify(VALID_MOVE),
    ],
    mockSemanticEvaluatorResponses: [semanticHard(), semanticHard(), semanticHard()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, false);
  assert.equal(result.terminalDisposition, 'hard_exhausted');
  assert.equal(result.generatedCandidateCount, 3);
});

test('character phase: soft revision then residual soft accept', async () => {
  const api = createMockApi({
    validationSequence: [
      { accepted: true, normalized_move: VALID_MOVE },
      { accepted: true, normalized_move: VALID_MOVE_2 },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([
      JSON.stringify(VALID_MOVE),
      JSON.stringify(VALID_MOVE_2),
    ]),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-soft',
    mockResponses: [JSON.stringify(VALID_MOVE), JSON.stringify(VALID_MOVE_2)],
    mockSemanticEvaluatorResponses: [semanticSoft(), semanticSoft()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 2);
  assert.ok(result.residualSoftConcerns.length >= 1);
});

test('character phase: objective retryable false terminates without regeneration', async () => {
  const api = createMockApi({
    validationSequence: [
      {
        accepted: false,
        validation_class: 'schema',
        reason: 'invalid beats',
        retryable: false,
      },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([JSON.stringify(VALID_MOVE)]),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-obj-term',
    mockResponses: [JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [semanticPass()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, false);
  assert.equal(result.terminalDisposition, 'objective_validation_terminal');
  assert.equal(result.generatedCandidateCount, 1);
});

test('character phase: anchor mismatch regenerates without committing stale candidate', async () => {
  const api = createMockApi({
    commitSequence: [
      { committed: false, reason: 'turn counter anchor mismatch' },
      { committed: true, continuity_turn_index: 2, domain_commit_id: 'dc-2' },
    ],
    validationSequence: [
      { accepted: true, normalized_move: VALID_MOVE },
      { accepted: true, normalized_move: VALID_MOVE_2 },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([
      JSON.stringify(VALID_MOVE),
      JSON.stringify(VALID_MOVE_2),
    ]),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-anchor',
    mockResponses: [JSON.stringify(VALID_MOVE), JSON.stringify(VALID_MOVE_2)],
    mockSemanticEvaluatorResponses: [semanticPass(), semanticPass()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 2);
});

test('character phase: character inference infrastructure retry then pass', async () => {
  const api = createMockApi();
  const result = await runCharacterPhase({
    runEphemeralInference: createFailingInference(1),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-infra',
    mockResponses: [JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [semanticPass()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 1);
});

test('character phase: evaluator infrastructure retry succeeds without new Character candidate', async () => {
  const api = createMockApi();
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-evidence-eval-retry-'));
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root: evidenceRoot });
  const { runEphemeralInference, roleCalls, inferenceCalls } = createRecorderBackedInference(recorder, {
    semanticOutcomes: [
      { fail: true, failure: 'provider_timeout' },
      { raw: semanticPass() },
    ],
  });

  const result = await runCharacterPhase({
    runEphemeralInference,
    recorder,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-eval-retry-pass',
    mockResponses: [JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [semanticPass()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });

  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 1);
  assert.equal(roleCalls.character, 1);
  assert.equal(roleCalls.semantic_evaluator, 2);
  assert.equal(api.prepareCalls.length, 1);

  const semanticCalls = inferenceCalls.filter((call) => call.role === 'semantic_evaluator');
  assert.equal(semanticCalls.length, 2);
  assert.notEqual(semanticCalls[0].inferenceId, semanticCalls[1].inferenceId);
  assert.match(semanticCalls[1].inferenceId, /infra-retry-1/);
  assert.equal(semanticCalls[0].evidenceContext?.evaluationPassId, semanticCalls[1].evidenceContext?.evaluationPassId);

  const index = recorder.readIndex('sess-1');
  const evaluatorAttempts = (index.attempt_ids ?? [])
    .map((id) => recorder.readAttempt('sess-1', id))
    .filter((attempt) => attempt?.correlation?.role === 'semantic_evaluator');
  assert.equal(evaluatorAttempts.length, 2);
  const characterAttempt = (index.attempt_ids ?? [])
    .map((id) => recorder.readAttempt('sess-1', id))
    .find((attempt) => attempt?.correlation?.role === 'character');
  assert.ok(characterAttempt);
  for (const attempt of evaluatorAttempts) {
    assert.equal(attempt.correlation.prior_attempt_id, characterAttempt.evidence_id);
    assert.equal(attempt.correlation.inference_id, 'inf-char-eval-retry-pass');
  }

  fs.rmSync(evidenceRoot, { recursive: true, force: true });
});

test('character phase: evaluator infrastructure retry exhaustion fails closed without extra candidate', async () => {
  const api = createMockApi();
  const evidenceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-evidence-eval-fail-'));
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root: evidenceRoot });
  const { runEphemeralInference, roleCalls, inferenceCalls } = createRecorderBackedInference(recorder, {
    semanticOutcomes: [
      { fail: true, failure: 'provider_timeout' },
      { fail: true, failure: 'malformed_evaluator_output', raw: 'not-json' },
      { raw: semanticPass() },
    ],
  });

  const result = await runCharacterPhase({
    runEphemeralInference,
    recorder,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-eval-retry-fail',
    mockResponses: [JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [semanticPass()],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });

  assert.equal(result.committed, false);
  assert.equal(result.terminalDisposition, 'semantic_evaluator_failed');
  assert.equal(result.generatedCandidateCount, 1);
  assert.equal(roleCalls.character, 1);
  assert.equal(roleCalls.semantic_evaluator, 2);
  assert.equal(api.prepareCalls.length, 1);
  assert.equal(inferenceCalls.filter((call) => call.role === 'semantic_evaluator').length, 2);

  const index = recorder.readIndex('sess-1');
  assert.ok(index.semantic.evaluator_failures.length >= 1);

  fs.rmSync(evidenceRoot, { recursive: true, force: true });
});

test('character phase: respects liveMaxAttempts ceiling of three', async () => {
  const api = createMockApi({
    validationSequence: Array.from({ length: 5 }, () => ({
      accepted: false,
      validation_class: 'schema',
      reason: 'retry',
      retryable: true,
    })),
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference(Array.from({ length: 5 }, () => JSON.stringify(VALID_MOVE))),
    recorder: null,
    trace: noopTrace,
    api,
    sceneAgent: noopSceneAgent,
    sceneSessionId: 'scene-1',
    hgSessionId: 'sess-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    directorDecision: {},
    characterInferenceId: 'inf-char-ceiling',
    mockResponses: Array.from({ length: 5 }, () => JSON.stringify(VALID_MOVE)),
    mockSemanticEvaluatorResponses: Array.from({ length: 5 }, () => semanticPass()),
    characterTurnIndex: 0,
    liveMaxAttempts: 99,
  });
  assert.equal(result.committed, false);
  assert.equal(result.generatedCandidateCount, 3);
});

test('execution evidence index: semantic hard finding is discoverable', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-evidence-semantic-'));
  const store = new ExecutionEvidenceStore(root);
  const evidenceId = 'ev-char-1';
  store.writeAttempt({
    evidence_id: evidenceId,
    correlation: {
      evidence_id: evidenceId,
      hg_session_id: 'sess-1',
      hg_scene_id: 'scene-1',
      hg_round_id: 'round-1',
      role: 'character',
      inference_id: 'inf-1',
      attempt_index: 0,
    },
    request: {},
    response: {},
  });
  store.patchAttempt('sess-1', evidenceId, {
    decision: {
      outcome: 'semantic_rejected_hard',
      semantic_evaluation: {
        result: {
          findings: [{ dimension: 'R02b', severity: 'hard', finding: 'test' }],
        },
      },
    },
  });
  const index = store.readIndex('sess-1');
  assert.ok(index.semantic.hard_findings.includes(evidenceId));
  assert.ok(index.semantic.by_dimension.R02b.includes(evidenceId));
  fs.rmSync(root, { recursive: true, force: true });
});

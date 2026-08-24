import assert from 'node:assert/strict';
import test from 'node:test';

import { runNarratorPhase } from '../src/plugins/hg-phase-executors/narrator-phase.mjs';

const VALID_PRESENTATION = 'Alice nodded thoughtfully, taking in the workshop around her.';

function makeSemanticPass(passId = 'narrator-qa-pass') {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'pass',
    findings: [],
  });
}

function makeSemanticSoftReject(passId = 'narrator-qa-pass') {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'nar_framing_distortion',
      severity: 'soft',
      finding: 'Tone could be tighter',
      rationale: 'test',
    }],
  });
}

function makeSemanticHardReject(passId = 'narrator-qa-pass') {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: passId,
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'nar_attribution_error',
      severity: 'hard',
      finding: 'Wrong speaker attribution',
      rationale: 'test',
      authoritative_citation: { ref_id: 'commit:abc' },
    }],
  });
}

function createMockApi({
  validationAccepted = true,
  prepareCalls = [],
} = {}) {
  return {
    prepareCalls,
    async prepareNarratorContext(body) {
      prepareCalls.push(body);
      return {
        manifest_id: `manifest-narrator-${body.inference_id}-${body.attempt_index ?? 0}`,
        inference_id: body.inference_id,
        contributions: body.correction_context
          ? [{ source_kind: 'semantic_correction', content: JSON.stringify(body.correction_context) }]
          : [],
      };
    },
    async prepareNarratorSemanticQaContext() {
      return {
        manifest_id: 'manifest-narrator-qa-1',
        inference_id: 'inf-narrator-1',
        hg_scene_id: 'scene-1',
        hg_round_id: 'round-1',
        turn_index: 0,
        authority_references: [{
          ref_id: 'commit:abc',
          kind: 'committed_move',
          authority_class: 'authoritative',
          label: 'Committed move',
          text: 'Alice nods.',
        }],
        contributions: [{
          contribution_id: 'manifest-narrator-qa-1-role',
          source_kind: 'committed_move',
          authority_class: 'authoritative',
          priority: 10,
          content: 'Narrator QA context',
          knowledge_ids: [],
          provenance: {},
        }],
      };
    },
    async validateNarratorPresentation() {
      return {
        accepted: validationAccepted,
        validation_class: validationAccepted ? 'accepted' : 'speech_verbatim',
        reason: validationAccepted ? '' : 'speech mismatch',
        retryable: !validationAccepted,
      };
    },
  };
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

test('runNarratorPhase accepts after semantic QA pass', async () => {
  const api = createMockApi();
  const trace = createTrace();
  let inferenceCalls = 0;
  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION],
    mockNarratorSemanticQaResponses: [makeSemanticPass('inf-narrator-1-qa-0')],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ mockResponses, evidenceContext }) => {
      inferenceCalls += 1;
      const isEvaluator = evidenceContext?.role === 'semantic_evaluator';
      const raw = isEvaluator
        ? mockResponses?.[0]
        : mockResponses?.[0] ?? VALID_PRESENTATION;
      return {
        evidenceId: isEvaluator ? `ev-eval-${inferenceCalls}` : `ev-narrator-${inferenceCalls}`,
        inferenceSessionId: `is-${inferenceCalls}`,
        raw,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(result.presentation_text, VALID_PRESENTATION);
  assert.ok(trace.events.some((event) => event.type === 'hg/narrator-semantic-qa'));
  assert.equal(inferenceCalls, 2);
});

test('runNarratorPhase does not invoke semantic QA when F1 validation fails', async () => {
  const api = createMockApi({ validationAccepted: false });
  const trace = createTrace();
  let semanticPrepareCalls = 0;
  api.prepareNarratorSemanticQaContext = async () => {
    semanticPrepareCalls += 1;
    throw new Error('semantic QA should not run');
  };

  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION, VALID_PRESENTATION],
    mockNarratorSemanticQaResponses: [makeSemanticPass()],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ mockResponses }) => ({
      evidenceId: 'ev-narrator-1',
      inferenceSessionId: 'is-1',
      raw: mockResponses?.[0] ?? VALID_PRESENTATION,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
  });

  assert.equal(semanticPrepareCalls, 0);
  assert.equal(result.presentation_failed, true);
  assert.equal(trace.events.some((event) => event.type === 'hg/narrator-semantic-qa'), false);
});

test('runNarratorPhase soft reject regen then accepts with residuals', async () => {
  const prepareCalls = [];
  const api = createMockApi({ prepareCalls });
  const trace = createTrace();
  const semanticResponses = [
    makeSemanticSoftReject('inf-narrator-1-qa-0'),
    makeSemanticPass('inf-narrator-1-qa-1'),
  ];
  let narratorInferenceCalls = 0;

  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION, 'Alice nodded again with richer detail.'],
    mockNarratorSemanticQaResponses: semanticResponses,
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ mockResponses, evidenceContext }) => {
      const isEvaluator = evidenceContext?.role === 'semantic_evaluator';
      if (isEvaluator) {
        return {
          evidenceId: 'ev-eval',
          inferenceSessionId: 'is-eval',
          raw: mockResponses?.[0],
          failed: false,
          trace: { finish: { kind: 'stop' } },
        };
      }
      narratorInferenceCalls += 1;
      return {
        evidenceId: `ev-narrator-${narratorInferenceCalls}`,
        inferenceSessionId: `is-${narratorInferenceCalls}`,
        raw: mockResponses?.[0] ?? VALID_PRESENTATION,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(prepareCalls.length, 2);
  assert.ok(prepareCalls[1].correction_context);
  assert.match(JSON.stringify(prepareCalls[1].correction_context), /nar_framing_distortion/);
});

test('runNarratorPhase soft reject on final attempt accepts with residuals', async () => {
  const api = createMockApi();
  const trace = createTrace();
  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION, VALID_PRESENTATION],
    mockNarratorSemanticQaResponses: [
      makeSemanticSoftReject('inf-narrator-1-qa-0'),
      makeSemanticSoftReject('inf-narrator-1-qa-1'),
    ],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ mockResponses, evidenceContext }) => ({
      evidenceId: evidenceContext?.role === 'semantic_evaluator' ? 'ev-eval' : 'ev-narrator',
      inferenceSessionId: 'is-1',
      raw: mockResponses?.[0] ?? VALID_PRESENTATION,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(result.terminal_disposition, 'accepted_with_residual_soft_concerns');
});

test('runNarratorPhase hard reject exhausted uses committed fallback', async () => {
  const api = createMockApi();
  const trace = createTrace();
  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION, VALID_PRESENTATION],
    mockNarratorSemanticQaResponses: [
      makeSemanticHardReject('inf-narrator-1-qa-0'),
      makeSemanticHardReject('inf-narrator-1-qa-1'),
    ],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ mockResponses, evidenceContext }) => ({
      evidenceId: evidenceContext?.role === 'semantic_evaluator' ? 'ev-eval' : 'ev-narrator',
      inferenceSessionId: 'is-1',
      raw: mockResponses?.[0] ?? VALID_PRESENTATION,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
  });

  assert.equal(result.presentation_rendered, false);
  assert.equal(result.presentation_failed, true);
  assert.equal(result.terminal_disposition, 'committed_fallback');
});

test('runNarratorPhase skips semantic QA when disabled', async () => {
  const api = createMockApi();
  api.prepareNarratorSemanticQaContext = async () => {
    throw new Error('semantic QA disabled');
  };
  const trace = createTrace();
  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: false,
    runEphemeralInference: async () => ({
      evidenceId: 'ev-narrator-1',
      inferenceSessionId: 'is-1',
      raw: VALID_PRESENTATION,
      failed: false,
      trace: { finish: { kind: 'stop' } },
    }),
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(trace.events.some((event) => event.type === 'hg/narrator-semantic-qa'), false);
});

test('runNarratorPhase infra failure uses committed fallback without extra narrator generation', async () => {
  const api = createMockApi();
  api.prepareNarratorSemanticQaContext = async () => {
    throw new Error('context prepare failed');
  };
  const trace = createTrace();
  let narratorGenerations = 0;
  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ evidenceContext }) => {
      if (evidenceContext?.role !== 'semantic_evaluator') {
        narratorGenerations += 1;
      }
      return {
        evidenceId: 'ev-narrator-1',
        inferenceSessionId: 'is-1',
        raw: VALID_PRESENTATION,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
  });

  assert.equal(narratorGenerations, 1);
  assert.equal(result.presentation_failed, true);
  assert.equal(result.terminal_disposition, 'committed_fallback');
});

test('runNarratorPhase evaluator infra retry succeeds without extra narrator generation', async () => {
  const api = createMockApi();
  const trace = createTrace();
  let evaluatorCalls = 0;
  let narratorGenerations = 0;
  const passId = 'inf-narrator-1-qa-0';
  const result = await runNarratorPhase({
    api,
    trace,
    sceneAgent: { session: { append: () => {} } },
    sceneSessionId: 'sess-1',
    hgSessionId: 'scene-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    characterId: 'Alice',
    domainCommitId: 'commit-abc',
    continuityTurnIndex: 1,
    narratorInferenceId: 'inf-narrator-1',
    mockNarratorResponses: [VALID_PRESENTATION],
    mockNarratorSemanticQaResponses: [makeSemanticPass(passId)],
    characterTurnIndex: 0,
    modelProfile: { kind: 'mock' },
    narratorSemanticQaEnabled: true,
    runEphemeralInference: async ({ inferenceId, mockResponses, evidenceContext }) => {
      if (evidenceContext?.role === 'semantic_evaluator') {
        evaluatorCalls += 1;
        if (evaluatorCalls === 1) {
          return {
            evidenceId: 'ev-eval-1',
            inferenceSessionId: 'is-eval-1',
            raw: '',
            failed: false,
            trace: { finish: { kind: 'stop' } },
          };
        }
        return {
          evidenceId: 'ev-eval-2',
          inferenceSessionId: 'is-eval-2',
          raw: mockResponses?.[0] ?? makeSemanticPass(passId),
          failed: false,
          trace: { finish: { kind: 'stop' } },
        };
      }
      narratorGenerations += 1;
      assert.match(inferenceId, /^inf-narrator-1/);
      return {
        evidenceId: 'ev-narrator-1',
        inferenceSessionId: 'is-1',
        raw: VALID_PRESENTATION,
        failed: false,
        trace: { finish: { kind: 'stop' } },
      };
    },
  });

  assert.equal(result.presentation_rendered, true);
  assert.equal(narratorGenerations, 1);
  assert.equal(evaluatorCalls, 2);
});

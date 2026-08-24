import assert from 'node:assert/strict';
import test from 'node:test';

import { runDirectorPhase } from '../src/plugins/hg-phase-executors/director-phase.mjs';

const VALID_DIRECTOR = {
  next_actor: 'Alice',
  end_round: false,
  reason: 'Alice should respond next.',
  environment_event: '',
  tension_shift: '',
};

function makeSemanticPass(passId = 'director-qa-pass') {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: passId,
    overall_result: 'pass',
    findings: [],
  });
}

function makeSemanticSoftReject(passId = 'director-qa-pass') {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: passId,
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'dir_reason_coherence',
      severity: 'soft',
      finding: 'Reason is too thin',
      rationale: 'test',
    }],
  });
}

function makeSemanticHardReject(passId = 'director-qa-pass') {
  return JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: passId,
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'dir_scene_contradiction',
      severity: 'hard',
      finding: 'Contradicts committed scene fact',
      rationale: 'test',
      authoritative_citation: { ref_id: 'ground:scene:location' },
    }],
  });
}

function createMockApi({
  validationAccepted = true,
  selectedCharacterId = 'Alice',
} = {}) {
  return {
    async prepareDirectorContext() {
      return {
        manifest_id: 'manifest-director-1',
        inference_id: 'inf-director-1',
        contributions: [],
      };
    },
    async prepareDirectorSemanticQaContext() {
      return {
        manifest_id: 'manifest-director-qa-1',
        inference_id: 'inf-director-1',
        hg_scene_id: 'scene-1',
        hg_round_id: 'round-1',
        turn_index: 0,
        authority_references: [{
          ref_id: 'ground:scene:location',
          kind: 'grounding',
          authority_class: 'authoritative',
          label: 'Scene location',
          text: 'The tavern.',
        }],
        contributions: [{
          contribution_id: 'manifest-director-qa-1-role',
          source_kind: 'director_decision',
          authority_class: 'derived',
          priority: 10,
          content: 'Director context',
          knowledge_ids: [],
          provenance: {},
        }],
      };
    },
    async validateDirectorDecision({ proposed_decision: proposed }) {
      return {
        accepted: validationAccepted,
        normalized_decision: proposed ?? VALID_DIRECTOR,
        selected_character_id: selectedCharacterId,
        validation_class: validationAccepted ? 'accepted' : 'invalid_actor',
        reason: validationAccepted ? '' : 'invalid actor',
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

test('runDirectorPhase accepts after semantic QA pass', async () => {
  const api = createMockApi();
  const trace = createTrace();
  let inferenceCalls = 0;
  const result = await runDirectorPhase({
    api,
    trace,
    sceneAgent: { session: {} },
    sceneSessionId: 'sess-1',
    hgSessionId: 'hg-session-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    directorInferenceId: 'inf-director-1',
    directorAttemptSeed: 0,
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    mockDirectorSemanticQaResponses: [makeSemanticPass('inf-director-1-qa-0')],
    directorResponseIndex: 0,
    actorsUsedThisRound: [],
    turnIndex: 0,
    eligibilitySnapshot: { eligibility_snapshot_id: 'snap-1' },
    participationContext: {},
    runEphemeralInference: async (args) => {
      inferenceCalls += 1;
      const isEvaluator = args.evidenceContext?.role === 'semantic_evaluator';
      return {
        failed: false,
        raw: isEvaluator
          ? makeSemanticPass(args.evidenceContext.evaluationPassId)
          : JSON.stringify(VALID_DIRECTOR),
        evidenceId: isEvaluator ? `eval-evidence-${inferenceCalls}` : `director-evidence-${inferenceCalls}`,
        inferenceSessionId: `sess-${inferenceCalls}`,
        trace: { provider: 'mock' },
      };
    },
    liveMaxAttempts: 3,
    directorSemanticQaEnabled: true,
  });

  assert.equal(result.accepted, true);
  assert.equal(result.selectedCharacterId, 'Alice');
  assert.equal(result.terminalDisposition, 'accepted');
  assert.ok(trace.events.some((event) => event.type === 'hg/director-semantic-qa'));
});

test('runDirectorPhase performs one soft regeneration then accepts with residuals', async () => {
  const api = createMockApi();
  const trace = createTrace();
  const directorResponses = [
    JSON.stringify({ ...VALID_DIRECTOR, reason: 'first reason' }),
    JSON.stringify({ ...VALID_DIRECTOR, reason: 'second reason' }),
  ];
  const semanticResponses = [
    makeSemanticSoftReject('inf-director-1-qa-0'),
    makeSemanticPass('inf-director-1-qa-1'),
  ];
  let directorInferenceCount = 0;

  const result = await runDirectorPhase({
    api,
    trace,
    sceneAgent: { session: {} },
    sceneSessionId: 'sess-1',
    hgSessionId: 'hg-session-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    directorInferenceId: 'inf-director-1',
    directorAttemptSeed: 0,
    mockDirectorResponses: directorResponses,
    mockDirectorSemanticQaResponses: semanticResponses,
    directorResponseIndex: 0,
    actorsUsedThisRound: [],
    turnIndex: 0,
    eligibilitySnapshot: { eligibility_snapshot_id: 'snap-1' },
    participationContext: {},
    runEphemeralInference: async (args) => {
      if (args.evidenceContext?.role === 'semantic_evaluator') {
        const passId = args.evidenceContext.evaluationPassId;
        const index = passId.endsWith('-qa-0') ? 0 : 1;
        return {
          failed: false,
          raw: semanticResponses[index],
          evidenceId: `eval-evidence-${index}`,
          inferenceSessionId: `eval-sess-${index}`,
          trace: { provider: 'mock' },
        };
      }
      const raw = directorResponses[directorInferenceCount];
      directorInferenceCount += 1;
      return {
        failed: false,
        raw,
        evidenceId: `director-evidence-${directorInferenceCount}`,
        inferenceSessionId: `director-sess-${directorInferenceCount}`,
        trace: { provider: 'mock' },
      };
    },
    liveMaxAttempts: 3,
    directorSemanticQaEnabled: true,
  });

  assert.equal(result.accepted, true);
  assert.equal(directorInferenceCount, 2);
  assert.equal(result.terminalDisposition, 'accepted');
});

test('runDirectorPhase retains prior soft-rejected candidate after hard exhaustion', async () => {
  const api = createMockApi();
  const trace = createTrace();
  const directorResponses = [
    JSON.stringify({ ...VALID_DIRECTOR, reason: 'soft rejected' }),
    JSON.stringify({ ...VALID_DIRECTOR, reason: 'hard rejected' }),
    JSON.stringify({ ...VALID_DIRECTOR, reason: 'hard rejected again' }),
  ];
  let directorInferenceCount = 0;

  const result = await runDirectorPhase({
    api,
    trace,
    sceneAgent: { session: {} },
    sceneSessionId: 'sess-1',
    hgSessionId: 'hg-session-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    directorInferenceId: 'inf-director-1',
    directorAttemptSeed: 0,
    mockDirectorResponses: directorResponses,
    mockDirectorSemanticQaResponses: [
      makeSemanticSoftReject('inf-director-1-qa-0'),
      makeSemanticHardReject('inf-director-1-qa-1'),
      makeSemanticHardReject('inf-director-1-qa-2'),
    ],
    directorResponseIndex: 0,
    actorsUsedThisRound: [],
    turnIndex: 0,
    eligibilitySnapshot: { eligibility_snapshot_id: 'snap-1' },
    participationContext: {},
    runEphemeralInference: async (args) => {
      if (args.evidenceContext?.role === 'semantic_evaluator') {
        const passId = args.evidenceContext.evaluationPassId;
        const index = Number(passId.split('-qa-')[1]);
        const payloads = [
          makeSemanticSoftReject('inf-director-1-qa-0'),
          makeSemanticHardReject('inf-director-1-qa-1'),
          makeSemanticHardReject('inf-director-1-qa-2'),
        ];
        return {
          failed: false,
          raw: payloads[index],
          evidenceId: `eval-evidence-${index}`,
          inferenceSessionId: `eval-sess-${index}`,
          trace: { provider: 'mock' },
        };
      }
      const raw = directorResponses[directorInferenceCount];
      directorInferenceCount += 1;
      return {
        failed: false,
        raw,
        evidenceId: `director-evidence-${directorInferenceCount}`,
        inferenceSessionId: `director-sess-${directorInferenceCount}`,
        trace: { provider: 'mock' },
      };
    },
    liveMaxAttempts: 3,
    directorSemanticQaEnabled: true,
  });

  assert.equal(result.accepted, true);
  assert.equal(result.terminalDisposition, 'semantic_soft_exhaustion_retained');
  assert.equal(result.directorDecision.reason, 'soft rejected');
});

test('runDirectorPhase skips semantic QA when disabled', async () => {
  const api = createMockApi();
  let semanticPrepareCalled = false;
  api.prepareDirectorSemanticQaContext = async () => {
    semanticPrepareCalled = true;
    throw new Error('should not be called');
  };

  const result = await runDirectorPhase({
    api,
    trace: createTrace(),
    sceneAgent: { session: {} },
    sceneSessionId: 'sess-1',
    hgSessionId: 'hg-session-1',
    hgSceneId: 'scene-1',
    hgRoundId: 'round-1',
    directorInferenceId: 'inf-director-1',
    directorAttemptSeed: 0,
    mockDirectorResponses: [JSON.stringify(VALID_DIRECTOR)],
    directorResponseIndex: 0,
    actorsUsedThisRound: [],
    turnIndex: 0,
    eligibilitySnapshot: { eligibility_snapshot_id: 'snap-1' },
    participationContext: {},
    runEphemeralInference: async () => ({
      failed: false,
      raw: JSON.stringify(VALID_DIRECTOR),
      evidenceId: 'director-evidence-1',
      inferenceSessionId: 'director-sess-1',
      trace: { provider: 'mock' },
    }),
    liveMaxAttempts: 3,
    directorSemanticQaEnabled: false,
  });

  assert.equal(result.accepted, true);
  assert.equal(semanticPrepareCalled, false);
});

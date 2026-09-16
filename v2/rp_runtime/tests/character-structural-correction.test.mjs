import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import test from 'node:test';

import { runCharacterPhase } from '../src/plugins/hg-phase-executors/character-phase.mjs';
import {
  buildCorrectionContextFromStructuralValidation,
  buildStructuralRepairGuidance,
  classifyStructuralFailureClasses,
  enrichObjectiveValidationCorrectionContext,
  isEligibleStructuralValidationFailure,
} from '../src/lib/character-structural-correction.mjs';
import { attachCharacterCognitionApiStubs } from './helpers/character-cognition-mock.mjs';

const MOTIVATION = {
  goal: 'respond',
  tactic: 'exchange',
  emotional_driver: 'formal',
  risk_level: 'medium',
};

const VALID_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'nods thoughtfully' }],
  motivation: MOTIVATION,
  semantic_evaluation: { decision: 'no_covered_change' },
};

const MISSING_VERSION_MOVE = {
  beats: [{ type: 'action', action: 'nods' }],
  motivation: MOTIVATION,
};

const MISSING_BEAT_TYPE_MOVE = {
  move_schema_version: 2,
  beats: [{ action: 'nods thoughtfully' }],
  motivation: MOTIVATION,
};

const CANONICAL_REPAIRED_MOVE = {
  move_schema_version: 2,
  beats: [
    { type: 'action', action: 'nods thoughtfully' },
    { type: 'speech', dialogue: 'Good evening.' },
  ],
  motivation: MOTIVATION,
  semantic_evaluation: { decision: 'no_covered_change' },
};

const REPO_V2_ROOT = path.resolve(import.meta.dirname, '../..');
const DOMAIN_TESTS_ROOT = path.join(REPO_V2_ROOT, 'domain', 'tests');

function runIngressValidation(move) {
  const script = `
import json
import sys
from pathlib import Path
v2 = Path.cwd().parent.parent
sys.path.insert(0, str(v2))
sys.path.insert(0, str(v2 / "domain" / "modules"))
from character_move_ingress import ingest_character_move_json_object
move = json.loads(sys.stdin.read())
parsed, err = ingest_character_move_json_object(move)
print(json.dumps({"accepted": parsed is not None, "reason": err or ""}))
`;
  const result = spawnSync('python', ['-c', script], {
    cwd: DOMAIN_TESTS_ROOT,
    env: {
      ...process.env,
      PYTHONPATH: REPO_V2_ROOT,
    },
    input: JSON.stringify(move),
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return JSON.parse(result.stdout);
}

function createMockApi({
  validationSequence = [{ accepted: true, normalized_move: VALID_MOVE, retryable: false }],
  commitSequence = [{ committed: true, continuity_turn_index: 1, domain_commit_id: 'dc-1' }],
} = {}) {
  let validationIndex = 0;
  let commitIndex = 0;
  const prepareCalls = [];
  return {
    prepareCalls,
    api: attachCharacterCognitionApiStubs({
      prepareCalls,
      async getSceneState() {
        return { turn_counter: 0 };
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
            ? [{
              source_kind: 'semantic_correction',
              content: JSON.stringify(body.correction_context),
            }]
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
          authority_references: [],
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
    }),
  };
}

function createMockInference(responses) {
  let index = 0;
  return async ({ mockResponses }) => {
    const raw = mockResponses?.[index] ?? responses[index] ?? JSON.stringify(VALID_MOVE);
    index += 1;
    return {
      failed: false,
      raw,
      evidenceId: `ev-char-${index}`,
      inferenceSessionId: `sess-char-${index}`,
      trace: {},
    };
  };
}

const noopTrace = { emit() {} };
const noopSceneAgent = { session: {} };

test('classifyStructuralFailureClasses detects schema version and beat type failures', () => {
  assert.deepEqual(
    classifyStructuralFailureClasses('move_schema_version is required (v2 only)'),
    ['missing_or_invalid_move_schema_version'],
  );
  assert.deepEqual(
    classifyStructuralFailureClasses('invalid beat type: None'),
    ['missing_or_invalid_beat_type'],
  );
});

test('isEligibleStructuralValidationFailure accepts retryable parse_error structural failures only', () => {
  assert.equal(isEligibleStructuralValidationFailure({
    accepted: false,
    validation_class: 'parse_error',
    reason: 'invalid beat type: None',
    retryable: true,
  }), true);
  assert.equal(isEligibleStructuralValidationFailure({
    accepted: false,
    validation_class: 'parse_error',
    reason: 'Unexpected token',
    retryable: true,
  }), false);
  assert.equal(isEligibleStructuralValidationFailure({
    accepted: false,
    validation_class: 'domain_rule',
    reason: 'invalid beat type: None',
    retryable: true,
  }), false);
});

test('buildCorrectionContextFromStructuralValidation includes canonical schema-version guidance', () => {
  const context = buildCorrectionContextFromStructuralValidation({
    validation_class: 'parse_error',
    reason: 'move_schema_version is required (v2 only; v1 character move ingress removed per GitHub #143)',
  }, {
    attemptIndex: 1,
    characterInferenceId: 'inf-char-201',
  });
  assert.deepEqual(context.required_move_schema_version, { move_schema_version: 2 });
  assert.match(context.structural_repair_guidance, /move_schema_version/);
  assert.match(context.structural_repair_guidance, /"move_schema_version":2/);
  assert.equal(context.evaluation_pass_id, 'inf-char-201-structural-1');
});

test('buildCorrectionContextFromStructuralValidation includes canonical beat-type guidance', () => {
  const context = buildCorrectionContextFromStructuralValidation({
    validation_class: 'parse_error',
    reason: 'invalid beat type: None',
  });
  assert.deepEqual(context.required_beat_structure_examples, {
    action: { type: 'action', action: '...' },
    speech: { type: 'speech', dialogue: '...' },
  });
  assert.match(context.structural_repair_guidance, /"type":"action"/);
  assert.match(context.structural_repair_guidance, /"type":"speech"/);
});

test('structural repair guidance does not inject narrative or story content', () => {
  const guidance = buildStructuralRepairGuidance([
    'missing_or_invalid_move_schema_version',
    'missing_or_invalid_beat_type',
  ]);
  const forbidden = [
    'Ayame',
    'Arkham',
    'Kizzie',
    'should decide',
    'score well',
    'invitation',
    'doorway',
    'foyer',
  ];
  for (const term of forbidden) {
    assert.equal(guidance.toLowerCase().includes(term.toLowerCase()), false, term);
  }
});

test('ingress validator rejects missing move_schema_version', () => {
  const result = runIngressValidation(MISSING_VERSION_MOVE);
  assert.equal(result.accepted, false);
  assert.match(result.reason, /move_schema_version is required/);
});

test('ingress validator rejects missing beat type', () => {
  const result = runIngressValidation(MISSING_BEAT_TYPE_MOVE);
  assert.equal(result.accepted, false);
  assert.match(result.reason, /invalid beat type/);
});

test('canonical repaired move passes ingress validation', () => {
  const result = runIngressValidation(CANONICAL_REPAIRED_MOVE);
  assert.equal(result.accepted, true);
});

test('character phase: valid first attempt has no correction context', async () => {
  const { api, prepareCalls } = createMockApi();
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
    characterInferenceId: 'inf-char-valid',
    mockResponses: [JSON.stringify(VALID_MOVE)],
    mockSemanticEvaluatorResponses: [{
      schema: 'hg_semantic_evaluation_result_v1',
      overall_result: 'pass',
      findings: [],
      correction_request: null,
      residual_soft_concerns: [],
    }],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(prepareCalls[0].correction_context, undefined);
});

test('character phase: missing move_schema_version retry includes structural correction guidance', async () => {
  const { api, prepareCalls } = createMockApi({
    validationSequence: [
      {
        accepted: false,
        validation_class: 'parse_error',
        reason: 'move_schema_version is required (v2 only; v1 character move ingress removed per GitHub #143)',
        retryable: true,
      },
      { accepted: true, normalized_move: VALID_MOVE, retryable: false },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([
      JSON.stringify(MISSING_VERSION_MOVE),
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
    characterInferenceId: 'inf-char-schema',
    mockResponses: [
      JSON.stringify(MISSING_VERSION_MOVE),
      JSON.stringify(VALID_MOVE),
    ],
    mockSemanticEvaluatorResponses: [{
      schema: 'hg_semantic_evaluation_result_v1',
      overall_result: 'pass',
      findings: [],
      correction_request: null,
      residual_soft_concerns: [],
    }],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 2);
  const correction = prepareCalls[1].correction_context;
  assert.ok(correction);
  assert.deepEqual(correction.required_move_schema_version, { move_schema_version: 2 });
  assert.match(JSON.stringify(correction), /structural_repair_guidance/);
});

test('character phase: missing beat type retry includes beat structure guidance and still rejects first attempt', async () => {
  const { api, prepareCalls } = createMockApi({
    validationSequence: [
      {
        accepted: false,
        validation_class: 'parse_error',
        reason: 'invalid beat type: None',
        retryable: true,
      },
      { accepted: true, normalized_move: VALID_MOVE, retryable: false },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
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
    characterInferenceId: 'inf-char-beat-type',
    mockResponses: [
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
      JSON.stringify(VALID_MOVE),
    ],
    mockSemanticEvaluatorResponses: [{
      schema: 'hg_semantic_evaluation_result_v1',
      overall_result: 'pass',
      findings: [],
      correction_request: null,
      residual_soft_concerns: [],
    }],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, true);
  assert.equal(result.generatedCandidateCount, 2);
  const correction = prepareCalls[1].correction_context;
  assert.ok(correction);
  assert.deepEqual(correction.required_beat_structure_examples.action, {
    type: 'action',
    action: '...',
  });
  assert.deepEqual(correction.required_beat_structure_examples.speech, {
    type: 'speech',
    dialogue: '...',
  });
});

test('character phase: structural correction does not change retry budget', async () => {
  const { api } = createMockApi({
    validationSequence: [
      {
        accepted: false,
        validation_class: 'parse_error',
        reason: 'invalid beat type: None',
        retryable: true,
      },
      {
        accepted: false,
        validation_class: 'parse_error',
        reason: 'invalid beat type: None',
        retryable: true,
      },
      {
        accepted: false,
        validation_class: 'parse_error',
        reason: 'invalid beat type: None',
        retryable: true,
      },
    ],
  });
  const result = await runCharacterPhase({
    runEphemeralInference: createMockInference([
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
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
    characterInferenceId: 'inf-char-budget',
    mockResponses: [
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
      JSON.stringify(MISSING_BEAT_TYPE_MOVE),
    ],
    characterTurnIndex: 0,
    liveMaxAttempts: 3,
  });
  assert.equal(result.committed, false);
  assert.equal(result.generatedCandidateCount, 3);
});

test('enrichObjectiveValidationCorrectionContext leaves non-structural parse errors minimal', () => {
  const context = enrichObjectiveValidationCorrectionContext({
    validation_class: 'parse_error',
    reason: 'Unexpected token } in JSON at position 4',
    retryable: true,
  });
  assert.equal(context.structural_repair_guidance, undefined);
  assert.equal(context.source, 'objective_validation');
});

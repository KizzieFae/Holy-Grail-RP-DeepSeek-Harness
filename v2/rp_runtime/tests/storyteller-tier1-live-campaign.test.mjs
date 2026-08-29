import assert from 'node:assert/strict';
import test from 'node:test';

import { CampaignLimits } from '../src/scenario-harness/campaign-limits.mjs';
import {
  parseCertificationEvalResult,
  runCertificationEvaluator,
  CERTIFICATION_EVAL_SCHEMA,
} from '../src/scenario-harness/certification-evaluator.mjs';
import { loadTruthFixture, listTruthFixtures } from '../src/scenario-harness/fixture-truth.mjs';
import {
  analyzeHardBlockers,
  analyzeLayerBAccounting,
  detectForbiddenLeaks,
  HARD_BLOCKER_CODES,
} from '../src/scenario-harness/hard-blockers.mjs';
import { createInstrumentedInference } from '../src/scenario-harness/instrumented-inference.mjs';
import {
  attachSemanticCharacterization,
  createSemanticCharacterization,
} from '../src/scenario-harness/semantic-characterization.mjs';
import {
  createScenarioResult,
  finalizeScenarioResult,
  OBJECTIVE_STATUS,
} from '../src/scenario-harness/scenario-result.mjs';
import { mockInferenceProfile, deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';
import { mockRuntimeConfig } from '../src/scenario-harness/live-config.mjs';

test('truth fixtures load for tranche-1 cases', () => {
  const ids = [
    't1-01-init',
    't1-02-no-replan',
    't1-03-replan',
    't1-05-known-basis',
    't1-06-unsafe-hidden',
    't1-06-safe-translation',
    't1-07-regen',
  ];
  for (const id of ids) {
    const truth = loadTruthFixture(id);
    assert.equal(truth.fixture_id, id);
  }
  assert.ok(listTruthFixtures().length >= ids.length);
});

test('campaign limits enforce run and inference ceilings', () => {
  const limits = new CampaignLimits({ maxRuns: 2, maxInferences: 3 });
  limits.recordRun();
  limits.recordInference();
  limits.recordInference();
  limits.recordInference();
  assert.throws(() => limits.assertCanInfer(), /campaign_inference_limit_exceeded/);
  limits.recordRun();
  assert.throws(() => limits.assertCanRun(), /campaign_run_limit_exceeded/);
});

test('instrumented inference distinguishes live vs controlled calls', async () => {
  const limits = new CampaignLimits({ maxRuns: 10, maxInferences: 10 });
  const runtimeConfig = mockRuntimeConfig();
  let callIndex = 0;
  const phaseExecutors = {
    runEphemeralInference: async (params) => {
      callIndex += 1;
      return {
        evidenceId: `ev-${callIndex}`,
        failed: false,
        raw: params.mockResponses?.[0] ?? '{}',
        trace: { usage: { input_tokens: 1, output_tokens: 2 } },
      };
    },
  };
  const instrumented = createInstrumentedInference({
    phaseExecutors,
    campaignLimits: limits,
    runtimeConfig,
  });
  await instrumented.runEphemeralInference({
    inferenceId: 'mock-1',
    prompt: 'x',
    manifest: { contributions: [] },
    mockResponses: ['{}'],
    modelProfile: mockInferenceProfile(),
    evidenceContext: { inferenceKind: 'plot_cognition_update' },
  });
  await instrumented.runEphemeralInference({
    inferenceId: 'live-1',
    prompt: 'x',
    manifest: { contributions: [] },
    mockResponses: [],
    modelProfile: deepseekInferenceProfile(),
    evidenceContext: { inferenceKind: 'plot_cognition_init', hgSessionId: 'sess-1' },
  });
  const summary = instrumented.summarize();
  assert.equal(summary.controlled_calls, 1);
  assert.equal(summary.live_calls, 1);
  assert.equal(limits.inferenceCount, 1);
});

test('layer B accounting enforces max 2 evals and 1 regeneration', () => {
  const calls = [
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'character_advisory_generation' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
  ];
  const analysis = analyzeLayerBAccounting(calls);
  assert.equal(analysis.evalCount, 3);
  assert.ok(analysis.violations.some((v) => v.code === HARD_BLOCKER_CODES.EVAL_EXCEEDED));
});

test('hard blocker detects epistemic leak against fixture truth', () => {
  const truth = loadTruthFixture('t1-06-unsafe-hidden');
  const leaks = detectForbiddenLeaks('Alice should enter code 9999 now.', truth, 'Alice');
  assert.ok(leaks.length > 0);
  const analysis = analyzeHardBlockers({
    scenarioResult: finalizeScenarioResult(createScenarioResult('T1-06', {
      objectiveGates: { ok: { name: 'ok', pass: true } },
    })),
    truth,
    consumerTexts: ['Use vault code 9999'],
    targetCharacter: 'Alice',
    liveCalls: [],
  });
  assert.ok(analysis.has_blocker);
  assert.ok(analysis.blockers.some((b) => b.code === HARD_BLOCKER_CODES.EPISTEMIC_LEAK));
});

test('semantic characterization cannot overwrite objective_status', () => {
  const base = finalizeScenarioResult(createScenarioResult('T1-05', {
    objectiveGates: { gate_a: { name: 'gate_a', pass: false } },
  }));
  assert.equal(base.objective_status, OBJECTIVE_STATUS.NOT_PROVEN);
  const attached = attachSemanticCharacterization(base, createSemanticCharacterization({
    fixtureId: 't1-05-known-basis',
    dimensions: { character_advisory: { naturalness: 'natural' } },
  }));
  assert.equal(attached.objective_status, OBJECTIVE_STATUS.NOT_PROVEN);
  assert.equal(attached.objective_pass, false);
  assert.ok(attached.semantic_characterization);
});

test('certification evaluator is read-only and parseable with mock output', async () => {
  const truth = loadTruthFixture('t1-05-known-basis');
  const mockEval = JSON.stringify({
    schema: CERTIFICATION_EVAL_SCHEMA,
    scenario_id: 'T1-05',
    evaluation_target: 'character:Alice',
    dimensions: { character_advisory: { naturalness: { level: 'natural', notes: 'ok' } } },
    categorical_findings: ['useful'],
    governance_flags: [],
    summary: 'Candidate advisory is grounded and useful.',
  });
  const domainMutations = [];
  const api = {
    preparePlotCognitionProjection: () => {
      domainMutations.push('prepare');
      return { accepted: false };
    },
  };
  const evalResult = await runCertificationEvaluator({
    runEphemeralInference: async () => ({
      failed: false,
      raw: mockEval,
      evidenceId: 'ev-cert-1',
    }),
    truth,
    outputText: 'Stay quiet while searching near the lockbox.',
    evaluationTarget: 'character:Alice',
    scenarioId: 'T1-05',
    mockResponse: mockEval,
    evidenceContextBase: { hgSessionId: 'sess-1' },
  });
  assert.equal(domainMutations.length, 0);
  assert.equal(evalResult.ok, true);
  assert.equal(evalResult.characterization.categorical_findings.includes('useful'), true);
  const parsed = parseCertificationEvalResult(mockEval);
  assert.equal(parsed.ok, true);
});

test('T1-06 truth distinguishes unsafe vs safe translation fixtures', () => {
  const unsafe = loadTruthFixture('t1-06-unsafe-hidden');
  const safe = loadTruthFixture('t1-06-safe-translation');
  assert.equal(unsafe.variant, 'unsafe');
  assert.equal(safe.variant, 'safe');
  assert.ok(safe.permitted_support?.length > 0);
});

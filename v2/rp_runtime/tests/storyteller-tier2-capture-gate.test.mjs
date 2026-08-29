import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { buildCampaignReport } from '../src/scenario-harness/campaign-report.mjs';
import { CampaignLimits } from '../src/scenario-harness/campaign-limits.mjs';
import {
  CERTIFICATION_EVAL_SCHEMA,
  runCertificationEvaluator,
} from '../src/scenario-harness/certification-evaluator.mjs';
import { loadTruthFixture } from '../src/scenario-harness/fixture-truth.mjs';
import {
  analyzeHardBlockers,
  analyzeLayerBAccounting,
  HARD_BLOCKER_CODES,
} from '../src/scenario-harness/hard-blockers.mjs';
import { createInstrumentedInference } from '../src/scenario-harness/instrumented-inference.mjs';
import { mockRuntimeConfig } from '../src/scenario-harness/live-config.mjs';
import {
  assertInvalidationInPrepareContext,
  buildCharacterCertificationSubject,
  buildPlotInitCertificationSubject,
  buildPlotUpdateCertificationSubject,
  overlayHasPressureText,
  proveUnsafeCandidate,
} from '../src/scenario-harness/production-capture.mjs';
import {
  attachSemanticCharacterization,
  createSemanticCharacterization,
} from '../src/scenario-harness/semantic-characterization.mjs';
import {
  createScenarioResult,
  finalizeScenarioResult,
  OBJECTIVE_STATUS,
} from '../src/scenario-harness/scenario-result.mjs';
import {
  buildC2OverlayWithPressure,
  buildC3InvalidationProofFromPrepare,
  TRANCHE2_CASES,
  verifyDurableEvidence,
} from '../src/scenario-harness/tier1-tranche2.mjs';
import { startHarnessRuntime } from '../src/scenario-harness/harness-runtime.mjs';
import { createHarnessRpContext } from '../src/scenario-harness/harness-runtime.mjs';
import { summarizeInferenceCounts } from '../src/scenario-harness/inference-mocks.mjs';
import { seedCharacterOverlayGoal } from '../tests/helpers/plot-cognition-projection-fixtures.mjs';
import { loadOverlayStore } from '../src/scenario-harness/forensic-query.mjs';

test('C1 certification subject includes raw proposal not overlay summary', () => {
  const truth = loadTruthFixture('t1-01-init');
  const subject = buildPlotInitCertificationSubject({
    capture: { raw_model_response: '{"schema":"hg_plot_cognition_init_proposal_v1"}', manifest_material: '{}' },
    lifecycle: { initFinalize: { accepted: false, code: 'integrity_invalid' }, operation: 'initialization' },
    truth,
  });
  assert.equal(subject.kind, 'plot_cognition_init');
  assert.ok(subject.raw_init_proposal.includes('hg_plot_cognition_init_proposal_v1'));
  assert.equal(subject.finalize.code, 'integrity_invalid');
});

test('C2 overlay seed contains fixture pressure text', () => {
  const truth = loadTruthFixture('t1-02-no-replan');
  const sessionsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-c2-pressure-'));
  const scopeId = 'scope-pressure-test';
  const { hasPressure, pressureText } = buildC2OverlayWithPressure(sessionsDir, scopeId, truth);
  assert.ok(hasPressure);
  const overlay = loadOverlayStore(sessionsDir, scopeId);
  assert.ok(overlayHasPressureText(overlay, pressureText));
});

test('C3 invalidation proof detects new committed authority', () => {
  const baseline = {
    source_snapshot: { canonical_body: { committed_moves: [] } },
    authority_source_fingerprint: 'fp-before',
  };
  const after = {
    source_snapshot: {
      canonical_body: {
        committed_moves: [{ domain_commit_id: 'hg-commit-1' }],
        continuity: { public_events: [] },
      },
    },
    authority_source_fingerprint: 'fp-after',
  };
  const proof = buildC3InvalidationProofFromPrepare(baseline, after);
  assert.equal(proof.ok, true);
  assert.equal(proof.committed_move_count, 1);
});

test('C4 character subject carries candidate text and verdict', () => {
  const truth = loadTruthFixture('t1-05-known-basis');
  const subject = buildCharacterCertificationSubject({
    capture: {
      candidate_text: 'Find the key quietly without drawing attention.',
      layer_b: { first: { verdict: 'withhold', rationale: 'too directive' } },
      character_storyteller_contributions: [],
    },
    truth,
    targetCharacter: 'Alice',
  });
  assert.ok(subject.candidate_text);
  assert.equal(subject.layer_b_first_verdict, 'withhold');
  assert.equal(subject.production_outcome, 'withheld');
});

test('C5 unsafe candidate proof detects forbidden private fact', () => {
  const truth = loadTruthFixture('t1-06-unsafe-hidden');
  const proof = proveUnsafeCandidate('Use Bob secret vault code 9999 to open the vault.', truth, 'Alice');
  assert.equal(proof.unsafe, true);
});

test('C6 safe candidate subject distinguishes withhold vs delivery', () => {
  const truth = loadTruthFixture('t1-06-safe-translation');
  const subject = buildCharacterCertificationSubject({
    capture: {
      candidate_text: 'Notice Bob seems anxious and check in discreetly.',
      layer_b: { first: { verdict: 'pass', rationale: 'safe' } },
      character_storyteller_contributions: [{ content: 'You could ask Bob if everything is alright.' }],
    },
    truth,
    targetCharacter: 'Alice',
  });
  assert.equal(subject.production_outcome, 'admitted');
  assert.ok(subject.final_character_contribution);
});

test('C7 unsafe candidate reaches proof gate before live', () => {
  const truth = loadTruthFixture('t1-07-regen');
  const proof = proveUnsafeCandidate(
    'Reveal the hidden vault location on the north wall panel to Alice.',
    truth,
    'Alice',
  );
  assert.equal(proof.unsafe, true);
});

test('layer B raw verdict capture shape', () => {
  const subject = buildCharacterCertificationSubject({
    capture: {
      candidate_text: 'unsafe',
      layer_b: {
        first: {
          verdict: 'rewrite_required',
          rationale: 'basis leak',
          regeneration_guidance: { safe_constraints: ['no code'] },
        },
        regeneration: { raw: '{"text":"safe rewrite"}' },
        second: { verdict: 'pass', rationale: 'ok' },
      },
      character_storyteller_contributions: [],
    },
    truth: loadTruthFixture('t1-07-regen'),
    targetCharacter: 'Alice',
  });
  assert.equal(subject.layer_b_first_verdict, 'rewrite_required');
  assert.ok(subject.regeneration_text);
  assert.equal(subject.layer_b_second_verdict, 'pass');
});

test('withholding is explicit when no contribution admitted', () => {
  const subject = buildCharacterCertificationSubject({
    capture: {
      candidate_text: 'candidate',
      layer_b: { first: { verdict: 'withhold', rationale: 'unsafe' } },
      character_storyteller_contributions: [],
      withheld_reason: 'semantic_withhold',
    },
    truth: loadTruthFixture('t1-06-unsafe-hidden'),
    targetCharacter: 'Alice',
  });
  assert.equal(subject.production_outcome, 'withheld');
  assert.equal(subject.withheld_reason, 'semantic_withhold');
});

test('certification evaluator prompt uses evaluationSubject when provided', async () => {
  const truth = loadTruthFixture('t1-05-known-basis');
  let capturedPrompt = '';
  const evalResult = await runCertificationEvaluator({
    runEphemeralInference: async ({ prompt }) => {
      capturedPrompt = prompt;
      return {
        failed: false,
        raw: JSON.stringify({
          schema: CERTIFICATION_EVAL_SCHEMA,
          scenario_id: 'T1-05',
          evaluation_target: 'character:Alice',
          dimensions: {},
          categorical_findings: [],
          governance_flags: [],
          summary: 'ok',
        }),
        evidenceId: 'ev-1',
      };
    },
    truth,
    evaluationSubject: { candidate_text: 'Find the key quietly.', production_outcome: 'withheld' },
    evaluationTarget: 'character:Alice',
    scenarioId: 'T1-05',
  });
  assert.equal(evalResult.ok, true);
  assert.ok(capturedPrompt.includes('Find the key quietly.'));
  assert.ok(capturedPrompt.includes('Certification subject to evaluate'));
});

test('durable execution evidence remains queryable after harness teardown', async () => {
  const campaignDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-durable-evidence-'));
  const runtime = await startHarnessRuntime({
    dataDir: campaignDir,
    sessionsDir: path.join(campaignDir, 'sessions'),
    forensicsDir: path.join(campaignDir, 'plot_cognition_forensics'),
  });
  const session = await runtime.api.createSession({ cast: ['Alice', 'Bob'] });
  const { ctx: rpCtx, phaseExecutors } = await createHarnessRpContext({
    baseUrl: runtime.baseUrl,
    dataDir: runtime.dataDir,
  });
  const limits = new CampaignLimits({ maxRuns: 1, maxInferences: 1 });
  const instrumented = createInstrumentedInference({
    phaseExecutors,
    campaignLimits: limits,
    runtimeConfig: mockRuntimeConfig(),
  });
  await instrumented.runEphemeralInference({
    inferenceId: 'inf-durable-test',
    prompt: 'test',
    manifest: { contributions: [] },
    mockResponses: ['{}'],
    modelProfile: mockRuntimeConfig().defaultProfile,
    evidenceContext: {
      hgSessionId: session.hg_session_id,
      inferenceKind: 'storyteller_certification_eval',
    },
  });
  await rpCtx.fiber.dispose();
  await runtime.dispose();
  const check = verifyDurableEvidence(campaignDir, session.hg_session_id);
  assert.equal(check.queryable, true);
  assert.ok(check.count >= 1);
});

test('token rollup uses inputTokens/outputTokens field names', () => {
  const report = buildCampaignReport({
    results: [{
      case_id: 'C1',
      result: {
        campaign: {
          live_inference_summary: {
            calls: [{
              live: true,
              inference_kind: 'plot_cognition_init',
              usage: { inputTokens: 10, outputTokens: 20 },
            }],
          },
        },
        phase_durations_ms: { total: 1 },
      },
    }],
    limits: new CampaignLimits({ maxRuns: 7, maxInferences: 18 }),
    hardBlockers: [],
    tranche: 2,
  });
  assert.equal(report.totals.tokens.input, 10);
  assert.equal(report.totals.tokens.output, 20);
  assert.equal(report.totals.tokens.total, 30);
  assert.equal(report.totals.tokens.unavailable, false);
});

test('semantic characterization cannot alter objective_status', () => {
  const base = finalizeScenarioResult(createScenarioResult('T1-05', {
    objectiveGates: { gate_a: { name: 'gate_a', pass: false } },
  }));
  const attached = attachSemanticCharacterization(base, createSemanticCharacterization({
    fixtureId: 't1-05-known-basis',
    dimensions: { character_advisory: { naturalness: 'natural' } },
  }));
  assert.equal(attached.objective_status, OBJECTIVE_STATUS.NOT_PROVEN);
});

test('tranche2 campaign limits: 7 runs and 18 inferences', () => {
  const limits = new CampaignLimits({ maxRuns: 7, maxInferences: 18 });
  for (let i = 0; i < 7; i += 1) limits.recordRun();
  for (let i = 0; i < 18; i += 1) limits.recordInference();
  assert.throws(() => limits.assertCanRun(), /campaign_run_limit_exceeded/);
  assert.throws(() => limits.assertCanInfer(), /campaign_inference_limit_exceeded/);
});

test('layer B accounting excludes certification evaluator and enforces production chain', () => {
  const calls = [
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'character_advisory_generation' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'storyteller_certification_eval' },
  ];
  const analysis = analyzeLayerBAccounting(calls.filter((c) => c.inference_kind !== 'storyteller_certification_eval'));
  assert.equal(analysis.evalCount, 2);
  assert.equal(analysis.regenCount, 1);
  assert.equal(analysis.layerBCount, 3);
  assert.equal(analysis.violations.length, 0);
  const withCorrections = analyzeLayerBAccounting([
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
    { live: true, inference_kind: 'character_advisory_generation' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval_contract_correction' },
  ]);
  assert.equal(withCorrections.layerBCount, 5);
  assert.equal(withCorrections.violations.length, 0);
  const exceeded = analyzeLayerBAccounting([
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
    { live: true, inference_kind: 'plot_cognition_epistemic_eval' },
  ]);
  assert.ok(exceeded.violations.some((v) => v.code === HARD_BLOCKER_CODES.EVAL_EXCEEDED));
});

test('tranche2 case registry has seven entries', () => {
  assert.equal(TRANCHE2_CASES.length, 7);
});

test('C3 assertInvalidation rejects unchanged authority', () => {
  const body = { committed_moves: [], continuity: { public_events: [] } };
  const prepare = {
    source_snapshot: { canonical_body: body },
    authority_source_fingerprint: 'same',
  };
  const proof = assertInvalidationInPrepareContext(prepare, {
    authority_source_fingerprint: 'same',
    committed_move_count: 0,
  });
  assert.equal(proof.ok, false);
});

test('plot update subject includes overlay pressure state for C2', () => {
  const truth = loadTruthFixture('t1-02-no-replan');
  const subject = buildPlotUpdateCertificationSubject({
    capture: { raw_model_response: '{"schema":"hg_plot_cognition_update_inference_v1"}' },
    updateResult: { stage: 'finalized', finalizeResponse: { accepted: true, code: 'update_committed' } },
    truth,
    overlayBefore: { store_revision: 1, goals: { g1: {} }, pressures: { p1: { pressure_text: 'Locate the key without alerting others.' } } },
    overlayAfter: { store_revision: 2, goals: { g1: {} }, pressures: { p1: { pressure_text: 'Locate the key without alerting others.' } } },
  });
  assert.ok(subject.overlay_before.pressures.includes('Locate the key without alerting others.'));
});

test('admitted character text captured when present', () => {
  const texts = ['Quietly search near the lockbox.'];
  const analysis = analyzeHardBlockers({
    scenarioResult: finalizeScenarioResult(createScenarioResult('T1-05', {
      objectiveGates: { ok: { name: 'ok', pass: true } },
    })),
    truth: loadTruthFixture('t1-05-known-basis'),
    consumerTexts: texts,
    targetCharacter: 'Alice',
    liveCalls: [],
  });
  assert.equal(analysis.has_blocker, false);
});

test('C2 overlay seed helper writes pressures into store file', () => {
  const sessionsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-seed-pressure-'));
  const scopeId = 'scope-seed';
  seedCharacterOverlayGoal(sessionsDir, scopeId, {
    pressures: [{ pressure_text: 'Locate the key without alerting others.' }],
  });
  const overlay = loadOverlayStore(sessionsDir, scopeId);
  assert.equal(Object.keys(overlay.pressures ?? {}).length, 1);
});

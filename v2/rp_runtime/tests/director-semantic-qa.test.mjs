import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DIRECTOR_SELECTION_CEILING,
  canApplySoftRegeneration,
  clearRetention,
  createDirectorSelectionBudget,
  recordDirectorAttempt,
  recordSoftRegeneration,
  setRetentionEligible,
} from '../src/plugins/hg-phase-executors/director-candidate-budget.mjs';
import {
  DIRECTOR_QA_CONFIG_ID,
  VALID_DIMENSIONS,
  applyDirectorSemanticPolicy,
  buildCorrectionContextFromDirectorQa,
  buildDirectorEvaluatorPrompt,
} from '../src/plugins/hg-phase-executors/director-semantic-qa.mjs';

test('director selection limit respects ceiling', () => {
  const budget = createDirectorSelectionBudget(5);
  assert.equal(budget.limit, DIRECTOR_SELECTION_CEILING);
  assert.equal(createDirectorSelectionBudget(2).limit, 2);
});

test('soft regeneration allows only one regeneration', () => {
  const budget = createDirectorSelectionBudget(3);
  assert.equal(canApplySoftRegeneration(budget), true);
  recordSoftRegeneration(budget);
  assert.equal(canApplySoftRegeneration(budget), false);
});

test('retention clears on hard reject of retained candidate', () => {
  const budget = createDirectorSelectionBudget(3);
  setRetentionEligible(budget, { evidenceId: 'ev-1', decision: { next_actor: 'Alice' } });
  clearRetention(budget, { evidenceId: 'ev-1' });
  assert.equal(budget.retentionEligibleCandidate, null);
});

test('buildDirectorEvaluatorPrompt includes all director dimensions', () => {
  const prompt = buildDirectorEvaluatorPrompt({
    evaluationPassId: 'eval-1',
  });
  for (const dimension of VALID_DIMENSIONS) {
    assert.match(prompt, new RegExp(dimension));
  }
  assert.match(prompt, /next_actor/);
});

test('buildCorrectionContextFromDirectorQa excludes replacement actor binding', () => {
  const context = buildCorrectionContextFromDirectorQa({
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'dir_reason_coherence',
      severity: 'soft',
      finding: 'reason too thin',
      rationale: 'test',
    }],
    evaluator_summary: 'revise reason',
  }, { evaluationPassId: 'eval-2' });
  assert.equal(context.source, 'semantic_qa');
  assert.equal(context.evaluation_pass_id, 'eval-2');
  assert.equal(context.findings.length, 1);
  assert.equal('next_actor' in context, false);
  assert.match(context.instruction, /replacement Director JSON only/);
});

test('applyDirectorSemanticPolicy passes clean QA result', () => {
  const budget = createDirectorSelectionBudget(3);
  const policy = applyDirectorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      schema: 'hg_semantic_qa_result_v1',
      overall_result: 'pass',
      findings: [],
    },
  }, budget);
  assert.equal(policy.action, 'pass');
});

test('applyDirectorSemanticPolicy soft regen when budget allows', () => {
  const budget = createDirectorSelectionBudget(3);
  const policy = applyDirectorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_soft',
      findings: [{
        dimension: 'dir_reason_coherence',
        severity: 'soft',
        finding: 'weak reason',
        rationale: 'test',
      }],
    },
  }, budget);
  assert.equal(policy.action, 'soft_regen');
});

test('applyDirectorSemanticPolicy accepts with residuals after soft regen used', () => {
  const budget = createDirectorSelectionBudget(3);
  recordSoftRegeneration(budget);
  const policy = applyDirectorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_soft',
      findings: [{
        dimension: 'dir_pacing_tension',
        severity: 'soft',
        finding: 'tension mismatch',
        rationale: 'test',
      }],
    },
  }, budget);
  assert.equal(policy.action, 'accept_with_residuals');
  assert.equal(policy.residualSoftConcerns.length, 1);
});

test('applyDirectorSemanticPolicy hard regen then retain on exhaustion', () => {
  const budget = createDirectorSelectionBudget(3);
  setRetentionEligible(budget, {
    evidenceId: 'ev-retain',
    decision: { next_actor: 'Alice', end_round: false },
  });
  recordDirectorAttempt(budget);
  recordDirectorAttempt(budget);
  const policy = applyDirectorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_hard',
      findings: [{
        dimension: 'dir_scene_contradiction',
        severity: 'hard',
        finding: 'contradiction',
        rationale: 'test',
        authoritative_citation: { ref_id: 'ground:scene:location' },
      }],
    },
  }, budget);
  assert.equal(policy.action, 'retain');
  assert.equal(policy.candidate.evidenceId, 'ev-retain');
});

test('applyDirectorSemanticPolicy reports infrastructure failure', () => {
  const budget = createDirectorSelectionBudget(3);
  const policy = applyDirectorSemanticPolicy({
    infrastructureFailure: true,
    evaluatorError: 'parse_failed',
    result: null,
  }, budget);
  assert.equal(policy.action, 'infra_fail');
});

test('director QA config id and dimensions are stable', () => {
  assert.equal(DIRECTOR_QA_CONFIG_ID, 'director_semantic_qa_v1');
  assert.equal(VALID_DIMENSIONS.size, 5);
});

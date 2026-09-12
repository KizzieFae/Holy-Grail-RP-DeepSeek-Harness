import assert from 'node:assert/strict';
import test from 'node:test';

import { CITATION_STATUS } from '../src/lib/semantic-qa-envelope.mjs';
import {
  NARRATOR_QA_CONFIG_ID,
  VALID_DIMENSIONS,
  applyNarratorSemanticPolicy,
  buildCorrectionContextFromNarratorQa,
  buildNarratorEvaluatorPrompt,
  classifySemanticQaResult,
} from '../src/plugins/hg-phase-executors/narrator-semantic-qa.mjs';

test('buildNarratorEvaluatorPrompt delegates rubric to manifest contributions', () => {
  const prompt = buildNarratorEvaluatorPrompt({
    evaluationPassId: 'eval-1',
  });
  assert.match(prompt, /manifest contributions/i);
  assert.match(prompt, /evaluation_pass_id to "eval-1"/);
  assert.match(prompt, /narrator/i);
  assert.doesNotMatch(prompt, /nar_environmental_contradiction/);
});

test('buildCorrectionContextFromNarratorQa excludes replacement prose binding', () => {
  const context = buildCorrectionContextFromNarratorQa({
    overall_result: 'reject_soft',
    findings: [{
      dimension: 'nar_framing_distortion',
      severity: 'soft',
      finding: 'tone mismatch',
      rationale: 'test',
    }],
  }, { evaluationPassId: 'eval-2' });
  assert.equal(context.source, 'semantic_qa');
  assert.equal(context.evaluation_pass_id, 'eval-2');
  assert.equal(context.findings.length, 1);
  assert.equal('presentation_text' in context, false);
  assert.match(context.instruction, /replacement narration only/);
});

test('applyNarratorSemanticPolicy passes clean QA result', () => {
  const policy = applyNarratorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      schema: 'hg_semantic_qa_result_v1',
      overall_result: 'pass',
      findings: [],
    },
  }, { attemptIndex: 0, maxAttempts: 2 });
  assert.equal(policy.action, 'pass');
});

test('applyNarratorSemanticPolicy soft regen on attempt 0', () => {
  const policy = applyNarratorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_soft',
      findings: [{
        dimension: 'nar_framing_distortion',
        severity: 'soft',
        finding: 'weak framing',
        rationale: 'test',
      }],
    },
  }, { attemptIndex: 0, maxAttempts: 2 });
  assert.equal(policy.action, 'soft_regen');
});

test('applyNarratorSemanticPolicy accepts with residuals on attempt 1 soft reject', () => {
  const policy = applyNarratorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_soft',
      findings: [{
        dimension: 'nar_framing_distortion',
        severity: 'soft',
        finding: 'residual concern',
        rationale: 'test',
      }],
    },
  }, { attemptIndex: 1, maxAttempts: 2 });
  assert.equal(policy.action, 'accept_with_residuals');
  assert.equal(policy.residualSoftConcerns.length, 1);
});

test('applyNarratorSemanticPolicy hard regen on attempt 0', () => {
  const policy = applyNarratorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_hard',
      findings: [{
        dimension: 'nar_committed_contradiction',
        severity: 'hard',
        finding: 'contradiction',
        rationale: 'test',
        authoritative_citation: { ref_id: 'commit:abc' },
      }],
    },
  }, { attemptIndex: 0, maxAttempts: 2 });
  assert.equal(policy.action, 'hard_regen');
});

test('applyNarratorSemanticPolicy exhausted fallback on attempt 1 hard reject', () => {
  const policy = applyNarratorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_hard',
      findings: [{
        dimension: 'nar_attribution_error',
        severity: 'hard',
        finding: 'wrong speaker',
        rationale: 'test',
        authoritative_citation: { ref_id: 'commit:abc' },
      }],
    },
  }, { attemptIndex: 1, maxAttempts: 2 });
  assert.equal(policy.action, 'exhausted_fallback');
});

test('applyNarratorSemanticPolicy reports infrastructure failure', () => {
  const policy = applyNarratorSemanticPolicy({
    infrastructureFailure: true,
    evaluatorError: 'parse_failed',
    result: null,
  }, { attemptIndex: 0, maxAttempts: 2 });
  assert.equal(policy.action, 'infra_fail');
});

test('narrator QA config id and dimensions are stable', () => {
  assert.equal(NARRATOR_QA_CONFIG_ID, 'narrator_semantic_qa_v1');
  assert.equal(VALID_DIMENSIONS.size, 9);
});

test('classifySemanticQaResult downgrades derived-only hard citations to soft', () => {
  const result = {
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'nar_committed_contradiction',
      severity: 'hard',
      finding: 'Contradicts director orchestration only',
      rationale: 'test',
      authoritative_citation: { ref_id: 'orch:round:round-1' },
    }],
  };
  const citationValidations = [{
    finding_index: 0,
    ref_id: 'orch:round:round-1',
    status: CITATION_STATUS.DERIVED_AUTHORITY_CLASS,
    resolved_authority_class: 'derived',
  }];
  const classified = classifySemanticQaResult(result, citationValidations);
  assert.equal(classified.hasHard, false);
  assert.equal(classified.hasSoft, true);
});

test('applyNarratorSemanticPolicy passes when hard reject cites only derived evidence', () => {
  const policy = applyNarratorSemanticPolicy({
    infrastructureFailure: false,
    result: {
      overall_result: 'reject_hard',
      findings: [{
        dimension: 'nar_committed_contradiction',
        severity: 'hard',
        finding: 'Derived-only hard attempt',
        rationale: 'test',
        authoritative_citation: { ref_id: 'orch:round:round-1' },
      }],
    },
    citationValidations: [{
      finding_index: 0,
      ref_id: 'orch:round:round-1',
      status: CITATION_STATUS.DERIVED_AUTHORITY_CLASS,
      resolved_authority_class: 'derived',
    }],
  }, { attemptIndex: 1, maxAttempts: 2 });
  assert.equal(policy.action, 'accept_with_residuals');
});

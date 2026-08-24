import assert from 'node:assert/strict';
import test from 'node:test';

import {
  CITATION_STATUS,
  parseSemanticQaResult,
  validateAuthorityReferences,
} from '../src/lib/semantic-qa-envelope.mjs';

test('validateAuthorityReferences preserves authority classes', () => {
  const { normalized, errors } = validateAuthorityReferences([
    {
      ref_id: 'derived:1',
      kind: 'digest',
      authority_class: 'derived',
      label: 'Digest',
      text: 'Derived evidence',
    },
    {
      ref_id: 'advisory:1',
      kind: 'hint',
      authority_class: 'advisory',
      label: 'Hint',
      text: 'Advisory evidence',
    },
  ]);
  assert.equal(errors.length, 0);
  assert.equal(normalized[0].authority_class, 'derived');
  assert.equal(normalized[1].authority_class, 'advisory');
});

test('parseSemanticQaResult rejects invalid severity', () => {
  const raw = JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: 'eval-1',
    overall_result: 'pass',
    findings: [{ dimension: 'N1', severity: 'medium', finding: 'x', rationale: 'y' }],
  });
  const parsed = parseSemanticQaResult(raw);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.findings.length, 0);
  assert.ok(parsed.parseWarnings.some((w) => w.includes('severity')));
});

test('parseSemanticQaResult accepts optional evaluator summary', () => {
  const raw = JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'character',
    evaluation_pass_id: 'eval-1',
    overall_result: 'pass',
    findings: [],
    evaluator_summary: 'No issues found.',
    residual_soft_concerns: ['minor wording'],
  });
  const parsed = parseSemanticQaResult(raw);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.evaluator_summary, 'No issues found.');
  assert.deepEqual(parsed.result.residual_soft_concerns, ['minor wording']);
});

test('missing hard citation is reported in sidecar', () => {
  const parsed = parseSemanticQaResult(JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: 'eval-1',
    overall_result: 'reject_hard',
    findings: [{ dimension: 'D2', severity: 'hard', finding: 'x', rationale: 'y' }],
  }));
  assert.equal(parsed.citationValidations[0].status, CITATION_STATUS.MISSING_CITATION);
});

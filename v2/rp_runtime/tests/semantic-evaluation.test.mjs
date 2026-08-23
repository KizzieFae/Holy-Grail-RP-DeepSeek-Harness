import assert from 'node:assert/strict';
import test from 'node:test';

import {
  CHARACTER_CANDIDATE_CEILING,
  characterCandidateLimit,
  createCandidateBudgetState,
  canApplyHardCorrection,
  recordGeneratedCandidate,
  recordHardCorrection,
} from '../src/plugins/hg-phase-executors/character-candidate-budget.mjs';
import {
  DEFAULT_PASS_RESULT,
  parseSemanticEvaluationResult,
} from '../src/plugins/hg-phase-executors/character-semantic-evaluation.mjs';

const PLAYER_AGENCY_GUARDRAIL_ID = 'guardrail:player_agency';

test('character candidate limit respects ceiling', () => {
  assert.equal(characterCandidateLimit(5), CHARACTER_CANDIDATE_CEILING);
  assert.equal(characterCandidateLimit(2), 2);
});

test('hard correction budget allows two corrections within three candidates', () => {
  const budget = createCandidateBudgetState(3);
  recordGeneratedCandidate(budget);
  assert.equal(canApplyHardCorrection(budget), true);
  recordHardCorrection(budget);
  recordGeneratedCandidate(budget);
  assert.equal(canApplyHardCorrection(budget), true);
  recordHardCorrection(budget);
  recordGeneratedCandidate(budget);
  assert.equal(canApplyHardCorrection(budget), false);
});

test('unknown hard authority reference is downgraded to soft', () => {
  const authorityRefs = [{ ref_id: PLAYER_AGENCY_GUARDRAIL_ID }];
  const raw = JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_hard',
    findings: [
      {
        dimension: 'R12',
        severity: 'hard',
        finding: 'contradicts binding fact',
        rationale: 'test',
        authoritative_citation: { ref_id: 'binding_fact:missing' },
      },
    ],
  });
  const parsed = parseSemanticEvaluationResult(raw, authorityRefs);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.overall_result, 'reject_hard');
  assert.equal(parsed.result.findings[0].severity, 'soft');
});

test('valid player agency hard finding passes with guardrail ref', () => {
  const authorityRefs = [{ ref_id: PLAYER_AGENCY_GUARDRAIL_ID }];
  const raw = JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_hard',
    findings: [
      {
        dimension: 'R02b',
        severity: 'hard',
        finding: 'Character spoke for the player',
        rationale: 'Invented player dialogue',
        authoritative_citation: { ref_id: PLAYER_AGENCY_GUARDRAIL_ID },
      },
    ],
    correction_request: {
      summary: 'Remove invented player speech',
      dimensions: ['R02b'],
    },
  });
  const parsed = parseSemanticEvaluationResult(raw, authorityRefs);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.findings.length, 1);
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('default pass result shape', () => {
  assert.equal(DEFAULT_PASS_RESULT.overall_result, 'pass');
  assert.deepEqual(DEFAULT_PASS_RESULT.findings, []);
});

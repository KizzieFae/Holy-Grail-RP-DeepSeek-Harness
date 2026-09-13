import assert from 'node:assert/strict';
import test from 'node:test';

import { parseSemanticEvaluationResult } from '../src/plugins/hg-phase-executors/character-semantic-evaluation.mjs';
import {
  PLAYER_AUTHORSHIP_DIMENSION,
  applyNarratorSemanticPolicy,
  buildNarratorEvaluatorPrompt,
  classifySemanticQaResult,
} from '../src/plugins/hg-phase-executors/narrator-semantic-qa.mjs';
import { parseSemanticQaResult } from '../src/lib/semantic-qa-envelope.mjs';

const GUARDRAIL = 'guardrail:player_authorship';

test('narrator evaluator prompt enumerates authorized overall_result values', () => {
  const prompt = buildNarratorEvaluatorPrompt({
    evaluationPassId: 'eval-1',
  });
  assert.match(prompt, /overall_result pass\|reject_soft\|reject_hard/);
  assert.match(prompt, /nar_player_authorship/);
  assert.doesNotMatch(prompt, /nar_environmental_contradiction/);
});

test('parseSemanticQaResult rejects bare fail overall_result', () => {
  const parsed = parseSemanticQaResult(JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'narrator',
    evaluation_pass_id: 'eval-1',
    overall_result: 'fail',
    findings: [],
  }), []);
  assert.equal(parsed.ok, false);
  assert.match(parsed.error, /overall_result must be pass, reject_soft, or reject_hard/);
});

test('R02b hard finding cites player authorship guardrail', () => {
  const parsed = parseSemanticEvaluationResult(JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'R02b',
      severity: 'hard',
      finding: 'Invented frayed cuffs on Player character',
      rationale: 'no player_fact inventory supports wardrobe detail',
      authoritative_citation: { ref_id: GUARDRAIL },
    }],
  }), [{ ref_id: GUARDRAIL }]);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('R02b unsupported fact without fabricated player_fact ref stays hard via guardrail', () => {
  const parsed = parseSemanticEvaluationResult(JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'R02b',
      severity: 'hard',
      finding: 'Unsupported Player skin sensation',
      rationale: 'inventory lacks supporting player_fact; guardrail applies',
      authoritative_citation: { ref_id: GUARDRAIL },
    }],
  }), [{ ref_id: GUARDRAIL }, { ref_id: 'player_fact:user_post:u1' }]);
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('R14 hard accepts top-level ref_id citation alias from live evaluator', () => {
  const parsed = parseSemanticEvaluationResult(JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'R14',
      severity: 'hard',
      description: 'Established-but-not-entitled private thought',
      ref_id: 'perception_fact:entitlement:entry-1:u1',
    }],
  }), [
    { ref_id: 'perception_fact:entitlement:entry-1:u1' },
  ]);
  assert.equal(parsed.result.findings[0].severity, 'hard');
  assert.equal(
    parsed.result.findings[0].authoritative_citation.ref_id,
    'perception_fact:entitlement:entry-1:u1',
  );
});

test('R14 hard uses perception_fact not authorship guardrail alone for entitlement', () => {
  const parsed = parseSemanticEvaluationResult(JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'R14',
      severity: 'hard',
      finding: 'Character references off-scene Player knowledge',
      authoritative_citation: { ref_id: 'perception_fact:scene:present_characters' },
    }],
  }), [
    { ref_id: GUARDRAIL },
    { ref_id: 'perception_fact:scene:present_characters' },
  ]);
  assert.equal(parsed.result.findings[0].dimension, 'R14');
  assert.equal(parsed.result.findings[0].severity, 'hard');
});

test('nar_player_authorship hard exhausts to fail-closed not fallback', () => {
  const evalOutcome = {
    infrastructureFailure: false,
    citationValidations: [{
      finding_index: 0,
      status: 'valid',
      resolved_authority_class: 'authoritative',
    }],
    result: {
      overall_result: 'reject_hard',
      findings: [{
        dimension: PLAYER_AUTHORSHIP_DIMENSION,
        severity: 'hard',
        finding: 'Material Player amplification of single shiver into tremor',
        authoritative_citation: { ref_id: GUARDRAIL },
      }],
    },
  };
  const policy = applyNarratorSemanticPolicy(evalOutcome, { attemptIndex: 1, maxAttempts: 2 });
  assert.equal(policy.action, 'player_authorship_fail_closed');
});

test('nar_psychological_invention hard still uses exhausted_fallback', () => {
  const evalOutcome = {
    infrastructureFailure: false,
    citationValidations: [{
      finding_index: 0,
      status: 'valid',
      resolved_authority_class: 'authoritative',
    }],
    result: {
      overall_result: 'reject_hard',
      findings: [{
        dimension: 'nar_psychological_invention',
        severity: 'hard',
        finding: 'Unsupported NPC interior state',
        authoritative_citation: { ref_id: 'commit:abc' },
      }],
    },
  };
  const policy = applyNarratorSemanticPolicy(evalOutcome, { attemptIndex: 1, maxAttempts: 2 });
  assert.equal(policy.action, 'exhausted_fallback');
});

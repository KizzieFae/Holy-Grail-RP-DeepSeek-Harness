import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { semanticQaDecisionPatch } from '../src/lib/execution-evidence/semantic-qa-patch.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import {
  CITATION_STATUS,
  parseSemanticQaResult,
  validateFindingCitations,
} from '../src/lib/semantic-qa-envelope.mjs';
import { runSemanticQaEvaluation } from '../src/lib/semantic-qa-substrate.mjs';

const SAMPLE_REFS = [{
  ref_id: 'guardrail:player_agency',
  kind: 'guardrail',
  authority_class: 'authoritative',
  label: 'Player agency',
  text: 'Do not invent player behavior.',
}];

test('parseSemanticQaResult preserves hard severity on unknown citation', () => {
  const raw = JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: 'eval-1',
    overall_result: 'reject_hard',
    findings: [{
      dimension: 'D1',
      severity: 'hard',
      finding: 'bad',
      rationale: 'why',
      authoritative_citation: { ref_id: 'missing:ref' },
    }],
  });
  const parsed = parseSemanticQaResult(raw, SAMPLE_REFS);
  assert.equal(parsed.ok, true);
  assert.equal(parsed.result.findings[0].severity, 'hard');
  assert.equal(parsed.citationValidations[0].status, CITATION_STATUS.UNKNOWN_REF);
});

test('advisory citation validation reports class without promotion', () => {
  const refs = [{
    ref_id: 'derived:digest',
    kind: 'scene_digest',
    authority_class: 'advisory',
    label: 'Digest',
    text: 'Advisory only.',
  }];
  const validations = validateFindingCitations(
    [{
      dimension: 'N1',
      severity: 'hard',
      authoritative_citation: { ref_id: 'derived:digest' },
    }],
    refs,
  );
  assert.equal(validations[0].status, CITATION_STATUS.ADVISORY_AUTHORITY_CLASS);
  assert.equal(validations[0].resolved_authority_class, 'advisory');
});

test('semanticQaDecisionPatch captures target role and citation sidecar', () => {
  const patch = semanticQaDecisionPatch({
    evaluationPassId: 'eval-1',
    evaluationTargetRole: 'narrator',
    evaluatorEvidenceId: 'evidence-1',
    result: { overall_result: 'reject_soft', findings: [] },
    citationValidations: [{ finding_index: 0, status: 'valid' }],
  });
  assert.equal(patch.semantic_qa.evaluation_target_role, 'narrator');
  assert.equal(patch.semantic_qa.citation_validations[0].status, 'valid');
});

test('runSemanticQaEvaluation records mocked success with citation sidecar', async () => {
  const contextResponse = {
    manifest_id: 'manifest-semantic-qa-eval-1',
    inference_id: 'inf-dir-1',
    hg_scene_id: 'scene-1',
    hg_round_id: 'round-1',
    turn_index: 0,
    authority_references: SAMPLE_REFS,
    contributions: [{
      contribution_id: 'manifest-semantic-qa-eval-1-role',
      source_kind: 'director_decision',
      authority_class: 'derived',
      priority: 10,
      content: 'Role context',
      knowledge_ids: [],
      provenance: {},
    }],
  };

  const mockResponse = JSON.stringify({
    schema: 'hg_semantic_qa_result_v1',
    evaluation_target_role: 'director',
    evaluation_pass_id: 'eval-1',
    overall_result: 'pass',
    findings: [],
  });

  const inferenceCalls = [];
  const result = await runSemanticQaEvaluation({
    evaluationPassId: 'eval-1',
    evaluationTargetRole: 'director',
    parentCandidateEvidenceId: 'candidate-evidence-1',
    evidenceContextBase: {
      hgSessionId: 'session-1',
      hgSceneId: 'scene-1',
      hgRoundId: 'round-1',
      inferenceId: 'inf-dir-1',
    },
    prepareContext: async () => contextResponse,
    buildEvaluatorPrompt: () => 'Return semantic QA JSON only.',
    runEphemeralInference: async (args) => {
      inferenceCalls.push(args);
      return {
        failed: false,
        raw: mockResponse,
        evidenceId: 'evaluator-evidence-1',
        inferenceSessionId: 'sess-semantic-qa',
        trace: { provider: 'mock' },
      };
    },
    mockResponse,
  });

  assert.equal(result.ok, true);
  assert.equal(result.infrastructureFailure, false);
  assert.equal(result.result.overall_result, 'pass');
  assert.equal(inferenceCalls.length, 1);
  assert.equal(inferenceCalls[0].evidenceContext.role, 'semantic_evaluator');
  assert.equal(inferenceCalls[0].evidenceContext.evaluationTargetRole, 'director');
  assert.equal(inferenceCalls[0].evidenceContext.priorAttemptId, 'candidate-evidence-1');
});

test('runSemanticQaEvaluation reports context prepare infrastructure failure', async () => {
  const result = await runSemanticQaEvaluation({
    evaluationPassId: 'eval-2',
    evaluationTargetRole: 'narrator',
    evidenceContextBase: { hgSessionId: 'session-1' },
    prepareContext: async () => {
      throw new Error('prepare failed');
    },
    buildEvaluatorPrompt: () => 'prompt',
    runEphemeralInference: async () => ({
      failed: true,
      failure: 'should-not-run',
    }),
  });

  assert.equal(result.ok, false);
  assert.equal(result.infrastructureFailure, true);
  assert.equal(result.stage, 'context_prepare');
});

test('runSemanticQaEvaluation reports malformed evaluator output', async () => {
  const result = await runSemanticQaEvaluation({
    evaluationPassId: 'eval-3',
    evaluationTargetRole: 'director',
    evidenceContextBase: { hgSessionId: 'session-1', inferenceId: 'inf-1' },
    prepareContext: async () => ({
      manifest_id: 'm1',
      inference_id: 'inf-1',
      hg_scene_id: 'scene-1',
      hg_round_id: 'round-1',
      turn_index: 0,
      authority_references: [],
      contributions: [],
    }),
    buildEvaluatorPrompt: () => 'prompt',
    runEphemeralInference: async () => ({
      failed: false,
      raw: '{"schema":"wrong"}',
      evidenceId: 'evidence-malformed',
    }),
  });

  assert.equal(result.ok, false);
  assert.equal(result.infrastructureFailure, true);
  assert.equal(result.stage, 'parse');
});

test('semantic qa index is additive and does not require character semantic block', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-semantic-qa-'));
  const store = new ExecutionEvidenceStore(root);
  const hgSessionId = `session-${Date.now()}`;
  store.writeAttempt({
    evidence_id: 'candidate-1',
    correlation: {
      hg_session_id: hgSessionId,
      hg_round_id: 'round-1',
      role: 'director',
      inference_id: 'inf-1',
    },
  });
  store.patchAttempt(hgSessionId, 'candidate-1', {
    decision: {
      role: 'director',
      semantic_qa: {
        evaluation_target_role: 'director',
        infrastructure_failure: false,
        result: {
          findings: [{ dimension: 'D1', severity: 'soft' }],
        },
      },
    },
  });
  const index = store.readIndex(hgSessionId);
  assert.equal(index.semantic.qa_by_target_role.director.includes('candidate-1'), true);
  fs.rmSync(root, { recursive: true, force: true });
});

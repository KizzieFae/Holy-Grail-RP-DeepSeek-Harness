import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import { createTriggerRecord } from '../src/lib/conditional-job/envelope.mjs';
import {
  establishCanonicalJobEvidence,
  finalizeSemanticJob,
  finalizeSemanticJobIfOpen,
  openQaEvaluationJob,
  openSemanticJob,
  recordQaEvaluationInferenceAttempt,
  routingJobDispositionForTerminal,
  semanticJobIdFromEvaluationPass,
} from '../src/lib/conditional-job/semantic-job-evidence.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';
import { runLibrarianMediation } from '../src/lib/librarian-mediation-substrate.mjs';

test('QA infra retries share one semantic_job_id and canonical envelope', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-cjob-qa-retry-'));
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root });
  const hgSessionId = 'sess-qa-retry';
  const store = new ExecutionEvidenceStore(root);
  const evaluationPassId = 'inf-char-eval-0';
  const targetJobId = 'target-job-1';
  const targetCanonical = 'ev-target';
  store.writeAttempt({
    evidence_id: targetCanonical,
    correlation: { hg_session_id: hgSessionId, semantic_job_id: targetJobId },
    conditional_job: {
      schema: 'hg_conditional_semantic_job_v1',
      semantic_job_id: targetJobId,
      job_kind: 'character_move_generation',
      job_disposition: 'succeeded',
    },
  });
  let qaHandle = null;
  for (const infra of [0, 1]) {
    const evidenceId = infra === 0 ? 'ev-qa-fail' : 'ev-qa-ok';
    store.writeAttempt({
      evidence_id: evidenceId,
      correlation: { hg_session_id: hgSessionId, inference_kind: 'character_semantic_evaluation' },
      request: { schema: 'hg_assembled_request_v1', contributions: [] },
      response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
    });
    if (!qaHandle) {
      ({ handle: qaHandle } = openQaEvaluationJob(recorder, hgSessionId, {
        targetSemanticJobId: targetJobId,
        targetCanonicalEvidenceId: targetCanonical,
        evaluationPassId,
        correlation: { hg_session_id: hgSessionId },
        inferenceKind: 'character_semantic_evaluation',
      }));
    }
    qaHandle = recordQaEvaluationInferenceAttempt(recorder, hgSessionId, qaHandle, {
      evidenceId,
      canonicalInferenceKind: 'character_semantic_evaluation',
      infrastructureAttempt: infra,
    });
  }
  const expectedId = semanticJobIdFromEvaluationPass(evaluationPassId);
  assert.equal(qaHandle.semanticJobId, expectedId);
  const canonical = store.readAttempt(hgSessionId, qaHandle.canonicalEvidenceId);
  assert.equal(canonical.conditional_job.inference_attempt_refs.length, 2);
  const retry = store.readAttempt(hgSessionId, 'ev-qa-ok');
  assert.equal(retry.correlation.semantic_job_id, expectedId);
  assert.equal(retry.conditional_job, undefined);
  fs.rmSync(root, { recursive: true, force: true });
});

test('routing terminal disposition maps failure without success flag', () => {
  const terminal = routingJobDispositionForTerminal({
    directorAccepted: false,
    terminalDisposition: 'selection_budget_exhausted',
  });
  assert.equal(terminal.disposition, 'failed');
  assert.equal(terminal.reasonCode, 'selection_budget_exhausted');
});

test('finalizeSemanticJobIfOpen is idempotent', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-cjob-idem-'));
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root });
  const hgSessionId = 'sess-idem';
  const store = new ExecutionEvidenceStore(root);
  let handle = openSemanticJob({
    jobKind: 'routing_selection',
    triggerRecord: createTriggerRecord({
      source: 'round_topology',
      owner: 'dsh_orchestration',
      eligibilityDecision: { outcome: 'director_phase_entered' },
      inferenceRequired: true,
      evidenceRefs: [],
    }),
    correlation: { hg_session_id: hgSessionId },
  });
  store.writeAttempt({
    evidence_id: 'ev-dir',
    correlation: { hg_session_id: hgSessionId, inference_kind: 'director_turn' },
    request: { schema: 'hg_assembled_request_v1', contributions: [] },
    response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
  });
  handle = establishCanonicalJobEvidence(recorder, hgSessionId, 'ev-dir', handle, {
    canonicalInferenceKind: 'director_turn',
  });
  handle = finalizeSemanticJobIfOpen(recorder, hgSessionId, handle, {
    disposition: 'failed',
    reasonCode: 'hard_exhausted',
  });
  const first = store.readAttempt(hgSessionId, 'ev-dir').conditional_job.job_disposition;
  handle = finalizeSemanticJobIfOpen(recorder, hgSessionId, handle, {
    disposition: 'succeeded',
  });
  const second = store.readAttempt(hgSessionId, 'ev-dir').conditional_job.job_disposition;
  assert.equal(first, 'failed');
  assert.equal(second, 'failed');
  fs.rmSync(root, { recursive: true, force: true });
});

test('mediation inference failure finalizes knowledge_mediation job', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-cjob-med-fail-'));
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root });
  const hgSessionId = 'sess-med-fail';
  const store = new ExecutionEvidenceStore(root);
  const result = await runLibrarianMediation({
    domainApi: {
      prepareLibrarianMediationContext: async () => ({
        request_id: 'req-fail',
        manifest_id: 'man-1',
        mediation_catalog: [{ source_id: 'lmi:cand:a' }],
        contributions: [],
        retrieval_request_ids: [],
        retrieval_disposition: [],
      }),
      finalizeLibrarianMediation: async () => ({
        bundle_id: 'bundle-fail',
        audit: { host_validation: { accepted: false, rejection_codes: [] } },
        entries: [],
      }),
    },
    hgSceneId: 'scene-1',
    inferenceId: 'inf-med',
    knowledgeAccessRequest: { request_id: 'req-fail' },
    hgSessionId,
    recorder,
    runEphemeralInference: async () => {
      const evidenceId = 'ev-med-fail';
      store.writeAttempt({
        evidence_id: evidenceId,
        correlation: {
          hg_session_id: hgSessionId,
          inference_kind: 'librarian_mediation',
        },
        request: { schema: 'hg_assembled_request_v1', contributions: [] },
        response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
      });
      return {
        failed: true,
        failure: 'provider_inference_failed',
        evidenceId,
        stage: 'inference',
      };
    },
  });
  assert.equal(result.ok, false);
  const attempt = store.readAttempt(hgSessionId, 'ev-med-fail');
  assert.equal(attempt.conditional_job.job_kind, 'knowledge_mediation');
  assert.equal(attempt.conditional_job.job_disposition, 'failed_inference');
  fs.rmSync(root, { recursive: true, force: true });
});

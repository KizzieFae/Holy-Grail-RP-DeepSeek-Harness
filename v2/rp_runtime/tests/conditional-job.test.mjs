import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
  validateConditionalJobEnvelope,
  createTriggerRecord,
  buildOpenConditionalJobEnvelope,
  closeJobDisposition,
} from '../src/lib/conditional-job/envelope.mjs';
import {
  SEMANTIC_JOB_KIND_REGISTRY,
  validateSemanticJobRegistry,
} from '../src/lib/conditional-job/registry.mjs';
import {
  openSemanticJob,
  establishCanonicalJobEvidence,
  attachInferenceAttemptToJob,
  finalizeSemanticJob,
} from '../src/lib/conditional-job/semantic-job-evidence.mjs';
import { createExecutionEvidenceRecorder } from '../src/lib/execution-evidence/recorder.mjs';
import { ExecutionEvidenceStore } from '../src/lib/execution-evidence/store.mjs';

test('semantic job registry validates against llm-call-catalog', () => {
  const result = validateSemanticJobRegistry();
  assert.equal(result.ok, true, result.errors?.join('; '));
  assert.ok(SEMANTIC_JOB_KIND_REGISTRY.knowledge_mediation);
});

test('conditional job envelope validates', () => {
  const trigger = createTriggerRecord({
    source: 'host_prepare',
    owner: 'domain_host',
    eligibilityDecision: { outcome: 'mediation_requested' },
    inferenceRequired: true,
    evidenceRefs: [{ ref_type: 'request_id', value: 'req-1' }],
  });
  const envelope = buildOpenConditionalJobEnvelope({
    semanticJobId: 'job-1',
    jobKind: 'knowledge_mediation',
    triggerRecord: trigger,
    correlation: { hg_session_id: 'sess-1' },
  });
  const validation = validateConditionalJobEnvelope(envelope);
  assert.equal(validation.ok, true);
});

test('canonical job record and attempt joins without duplicate envelope', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-cjob-'));
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root });
  const hgSessionId = 'sess-cjob-1';
  const trigger = createTriggerRecord({
    source: 'host_prepare',
    owner: 'domain_host',
    eligibilityDecision: { outcome: 'mediation_requested' },
    inferenceRequired: true,
    evidenceRefs: [],
  });
  let handle = openSemanticJob({
    jobKind: 'knowledge_mediation',
    triggerRecord: trigger,
    correlation: { hg_session_id: hgSessionId, hg_round_id: 'round-1' },
  });
  const primaryEvidenceId = 'ev-primary';
  const store = new ExecutionEvidenceStore(root);
  store.writeAttempt({
    evidence_id: primaryEvidenceId,
    correlation: {
      hg_session_id: hgSessionId,
      hg_round_id: 'round-1',
      inference_kind: 'librarian_mediation',
    },
    request: { schema: 'hg_assembled_request_v1', contributions: [] },
    response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
  });
  handle = establishCanonicalJobEvidence(recorder, hgSessionId, primaryEvidenceId, handle, {
    canonicalInferenceKind: 'librarian_mediation',
    attemptLineageRole: 'primary',
  });
  const correctionEvidenceId = 'ev-correction';
  store.writeAttempt({
    evidence_id: correctionEvidenceId,
    correlation: {
      hg_session_id: hgSessionId,
      hg_round_id: 'round-1',
      inference_kind: 'librarian_mediation_contract_correction',
    },
    request: { schema: 'hg_assembled_request_v1', contributions: [] },
    response: { schema: 'hg_model_response_v1', assistant_text: '{}' },
  });
  handle = attachInferenceAttemptToJob(recorder, hgSessionId, handle, {
    evidenceId: correctionEvidenceId,
    canonicalInferenceKind: 'librarian_mediation_contract_correction',
    attemptLineageRole: 'correction',
  });
  handle = finalizeSemanticJob(recorder, hgSessionId, handle, {
    disposition: 'succeeded',
    consequenceSummary: { consumer: 'domain_host_finalize_librarian_mediation', mutation_class: 'derived_state' },
  });
  const canonical = store.readAttempt(hgSessionId, primaryEvidenceId);
  const correction = store.readAttempt(hgSessionId, correctionEvidenceId);
  assert.ok(canonical.conditional_job);
  assert.equal(canonical.conditional_job.job_kind, 'knowledge_mediation');
  assert.equal(canonical.conditional_job.job_disposition, 'succeeded');
  assert.equal(correction.conditional_job, undefined);
  assert.equal(correction.correlation.semantic_job_id, handle.semanticJobId);
  assert.equal(correction.correlation.canonical_job_evidence_id, primaryEvidenceId);
  const index = store.readIndex(hgSessionId);
  assert.ok(index.semantic_jobs.by_semantic_job_id[handle.semanticJobId]);
  fs.rmSync(root, { recursive: true, force: true });
});

test('zero-inference post-commit disposition carries canonical conditional job', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hg-cjob-skip-'));
  const recorder = createExecutionEvidenceRecorder({ enabled: true, root });
  const hgSessionId = 'sess-skip-1';
  const evidenceId = recorder.recordPostCommitSemanticDisposition({
    hgSessionId,
    domainCommitId: 'commit-1',
    postCommitSemanticInferenceId: 'inf-pc-1',
    eligibilityOutcome: 'no_eligible_active_issues',
    degradationMode: 'eligibility_skipped',
  });
  assert.ok(evidenceId);
  const attempt = recorder.readAttempt(hgSessionId, evidenceId);
  assert.ok(attempt.conditional_job);
  assert.equal(attempt.conditional_job.job_kind, 'post_commit_semantic');
  assert.equal(attempt.conditional_job.inference_attempt_refs.length, 0);
  assert.equal(attempt.request, null);
  fs.rmSync(root, { recursive: true, force: true });
});

/**
 * Conditional semantic job forensic helpers (#215).
 * Observational only — not continuity authority.
 */

import {
  addJobRelationship,
  buildOpenConditionalJobEnvelope,
  closeJobDisposition,
  createTriggerRecord,
  newSemanticJobId,
  registerInferenceAttemptOnEnvelope,
} from './envelope.mjs';

/**
 * @typedef {object} SemanticJobHandle
 * @property {string} semanticJobId
 * @property {string} jobKind
 * @property {object} envelope
 * @property {string|null} canonicalEvidenceId
 */

/**
 * @param {object} params
 * @returns {SemanticJobHandle}
 */
export function openSemanticJob({
  jobKind,
  triggerRecord,
  correlation = {},
  semanticJobId = null,
}) {
  const id = semanticJobId ?? newSemanticJobId();
  const envelope = buildOpenConditionalJobEnvelope({
    semanticJobId: id,
    jobKind,
    triggerRecord,
    correlation,
  });
  return {
    semanticJobId: id,
    jobKind,
    envelope,
    canonicalEvidenceId: null,
  };
}

export function mergeEvidenceContextForJob(handle, evidenceContextBase = {}, {
  attemptLineageRole = 'primary',
} = {}) {
  if (!handle?.semanticJobId) return { ...evidenceContextBase };
  return {
    ...evidenceContextBase,
    semanticJobId: handle.semanticJobId,
    canonicalJobEvidenceId: handle.canonicalEvidenceId,
    attemptLineageRole,
  };
}

/**
 * Establish canonical envelope on an existing evidence record (inference-backed or zero-inference).
 */
export function establishCanonicalJobEvidence(recorder, hgSessionId, evidenceId, handle, {
  attemptLineageRole = 'primary',
  canonicalInferenceKind = null,
} = {}) {
  if (!recorder?.isEnabled?.() || !hgSessionId || !evidenceId) return handle;
  let envelope = registerInferenceAttemptOnEnvelope(
    { ...handle.envelope, canonical_job_evidence_id: evidenceId },
    {
      evidenceId,
      canonicalInferenceKind,
      attemptLineageRole,
    },
  );
  recorder.patchConditionalJob(hgSessionId, evidenceId, envelope);
  recorder.linkAttemptToSemanticJob(hgSessionId, evidenceId, {
    semanticJobId: handle.semanticJobId,
    canonicalJobEvidenceId: evidenceId,
    attemptLineageRole,
    canonicalInferenceKind,
  });
  return {
    ...handle,
    canonicalEvidenceId: evidenceId,
    envelope,
  };
}

export function attachInferenceAttemptToJob(recorder, hgSessionId, handle, {
  evidenceId,
  canonicalInferenceKind,
  attemptLineageRole = 'primary',
}) {
  if (!recorder?.isEnabled?.() || !hgSessionId || !evidenceId || !handle.canonicalEvidenceId) {
    return handle;
  }
  recorder.linkAttemptToSemanticJob(hgSessionId, evidenceId, {
    semanticJobId: handle.semanticJobId,
    canonicalJobEvidenceId: handle.canonicalEvidenceId,
    attemptLineageRole,
    canonicalInferenceKind,
  });
  const envelope = registerInferenceAttemptOnEnvelope(handle.envelope, {
    evidenceId,
    canonicalInferenceKind,
    attemptLineageRole,
  });
  recorder.patchConditionalJob(hgSessionId, handle.canonicalEvidenceId, envelope);
  return { ...handle, envelope };
}

export function finalizeSemanticJob(recorder, hgSessionId, handle, {
  disposition,
  reasonCode = null,
  consequenceSummary = null,
  validationSummary = null,
}) {
  if (!recorder?.isEnabled?.() || !hgSessionId || !handle.canonicalEvidenceId) return handle;
  const envelope = closeJobDisposition(handle.envelope, {
    disposition,
    reasonCode,
    consequenceSummary,
    validationSummary,
  });
  recorder.patchConditionalJob(hgSessionId, handle.canonicalEvidenceId, envelope);
  return { ...handle, envelope };
}

export function openZeroInferenceSemanticJob(recorder, hgSessionId, {
  jobKind,
  triggerRecord,
  correlation,
  disposition,
  reasonCode,
  consequenceSummary = null,
  baseAttempt,
}) {
  if (!recorder?.isEnabled?.() || !hgSessionId) return null;
  const handle = openSemanticJob({ jobKind, triggerRecord, correlation });
  let envelope = closeJobDisposition(handle.envelope, {
    disposition,
    reasonCode,
    consequenceSummary,
  });
  envelope = {
    ...envelope,
    dispatch_fact: {
      dispatched: false,
      at: new Date().toISOString(),
    },
  };
  const evidenceId = recorder.writeSemanticJobCanonicalAttempt(hgSessionId, {
    ...baseAttempt,
    conditional_job: envelope,
    correlation: {
      ...(baseAttempt.correlation ?? {}),
      semantic_job_id: handle.semanticJobId,
      canonical_job_evidence_id: null,
    },
  });
  return establishCanonicalJobEvidence(recorder, hgSessionId, evidenceId, {
    ...handle,
    envelope,
  });
}

export function openQaEvaluationJob(recorder, hgSessionId, {
  targetSemanticJobId,
  targetCanonicalEvidenceId,
  evaluationPassId,
  correlation,
  inferenceKind,
}) {
  const triggerRecord = createTriggerRecord({
    source: 'semantic_qa_policy',
    owner: 'dsh_orchestration',
    eligibilityDecision: { outcome: 'evaluation_required', evaluation_pass_id: evaluationPassId },
    inferenceRequired: true,
    evidenceRefs: [
      { ref_type: 'target_semantic_job_id', value: targetSemanticJobId },
      { ref_type: 'target_canonical_job_evidence_id', value: targetCanonicalEvidenceId },
      { ref_type: 'evaluation_pass_id', value: evaluationPassId },
    ],
  });
  let handle = openSemanticJob({
    jobKind: 'semantic_quality_evaluation',
    triggerRecord,
    correlation,
  });
  handle = {
    ...handle,
    envelope: addJobRelationship(handle.envelope, {
      type: 'evaluates',
      target_semantic_job_id: targetSemanticJobId,
      target_canonical_job_evidence_id: targetCanonicalEvidenceId,
      evaluation_pass_id: evaluationPassId,
    }),
  };
  return { handle, inferenceKind };
}

export function openContextDependencyJobLink(recorder, hgSessionId, handle, {
  upstreamSemanticJobId,
  upstreamCanonicalEvidenceId,
  linkType = 'depends_on_context',
}) {
  if (!handle.canonicalEvidenceId) return handle;
  const envelope = addJobRelationship(handle.envelope, {
    type: linkType,
    upstream_semantic_job_id: upstreamSemanticJobId,
    upstream_canonical_job_evidence_id: upstreamCanonicalEvidenceId,
  });
  recorder.patchConditionalJob(hgSessionId, handle.canonicalEvidenceId, envelope);
  return { ...handle, envelope };
}

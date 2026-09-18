import crypto from 'node:crypto';

import { getRegistryEntry, inferenceKindAllowedForJobKind } from './registry.mjs';

export const CONDITIONAL_JOB_SCHEMA = 'hg_conditional_semantic_job_v1';

/**
 * @param {object} params
 * @returns {object}
 */
export function createTriggerRecord({
  source,
  owner,
  eligibilityDecision,
  inferenceRequired,
  evidenceRefs = [],
  obligationId = null,
  triggerPath = null,
}) {
  return {
    trigger_record_id: crypto.randomUUID(),
    obligation_id: obligationId ?? null,
    source: String(source ?? 'unknown'),
    owner: String(owner ?? 'dsh_orchestration'),
    eligibility_decision: eligibilityDecision ?? null,
    inference_required: Boolean(inferenceRequired),
    evidence_refs: [...evidenceRefs],
    trigger_path: triggerPath ?? null,
  };
}

/**
 * @param {object} params
 * @returns {object}
 */
export function buildOpenConditionalJobEnvelope({
  semanticJobId,
  jobKind,
  triggerRecord,
  correlation = {},
}) {
  const registryEntry = getRegistryEntry(jobKind);
  if (!registryEntry) {
    throw new Error(`unknown job_kind: ${jobKind}`);
  }
  const now = new Date().toISOString();
  return {
    schema: CONDITIONAL_JOB_SCHEMA,
    semantic_job_id: semanticJobId,
    job_kind: jobKind,
    canonical_job_evidence_id: null,
    trigger_record: triggerRecord,
    correlation: { ...correlation },
    facts: [
      { fact: 'trigger_evaluated', at: now },
    ],
    dispatch_fact: {
      dispatched: Boolean(triggerRecord?.inference_required),
      at: now,
    },
    inference_attempt_refs: [],
    job_relationships: [],
    validation_summary: null,
    consequence_summary: null,
    job_disposition: null,
    disposition_reason_code: null,
    transport_batch: null,
  };
}

export function appendJobFact(envelope, factName, details = {}) {
  const next = {
    ...envelope,
    facts: [
      ...(envelope.facts ?? []),
      { fact: factName, at: new Date().toISOString(), ...details },
    ],
  };
  return next;
}

export function registerInferenceAttemptOnEnvelope(envelope, {
  evidenceId,
  canonicalInferenceKind,
  attemptLineageRole = 'primary',
}) {
  const refs = [...(envelope.inference_attempt_refs ?? [])];
  const existing = refs.find((item) => item.evidence_id === evidenceId);
  if (!existing) {
    refs.push({
      evidence_id: evidenceId,
      canonical_inference_kind: canonicalInferenceKind ?? null,
      attempt_lineage_role: attemptLineageRole,
    });
  }
  return appendJobFact(
    { ...envelope, inference_attempt_refs: refs },
    'inference_attempt',
    { evidence_id: evidenceId, attempt_lineage_role: attemptLineageRole },
  );
}

export function addJobRelationship(envelope, relationship) {
  const relationships = [...(envelope.job_relationships ?? []), relationship];
  return { ...envelope, job_relationships: relationships };
}

export function closeJobDisposition(envelope, {
  disposition,
  reasonCode = null,
  consequenceSummary = null,
  validationSummary = null,
}) {
  return appendJobFact(
    {
      ...envelope,
      job_disposition: disposition,
      disposition_reason_code: reasonCode,
      consequence_summary: consequenceSummary ?? envelope.consequence_summary,
      validation_summary: validationSummary ?? envelope.validation_summary,
    },
    'terminal_disposition',
    { disposition, reason_code: reasonCode },
  );
}

/**
 * @param {object} envelope
 * @returns {{ ok: true } | { ok: false, errors: string[] }}
 */
export function validateConditionalJobEnvelope(envelope) {
  const errors = [];
  if (!envelope || envelope.schema !== CONDITIONAL_JOB_SCHEMA) {
    errors.push('invalid or missing schema');
    return { ok: false, errors };
  }
  if (!envelope.semantic_job_id) errors.push('missing semantic_job_id');
  if (!envelope.job_kind) errors.push('missing job_kind');
  if (!getRegistryEntry(envelope.job_kind)) errors.push(`unknown job_kind ${envelope.job_kind}`);
  if (!envelope.trigger_record?.trigger_record_id) errors.push('missing trigger_record_id');
  for (const ref of envelope.inference_attempt_refs ?? []) {
    if (ref.canonical_inference_kind
      && !inferenceKindAllowedForJobKind(envelope.job_kind, ref.canonical_inference_kind)) {
      errors.push(
        `inference kind ${ref.canonical_inference_kind} not allowed for ${envelope.job_kind}`,
      );
    }
  }
  return errors.length ? { ok: false, errors } : { ok: true };
}

export function newSemanticJobId() {
  return crypto.randomUUID();
}

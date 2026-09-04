/**
 * Observational inference-health contract (#114).
 * Reconstructable from durable attempt evidence; not Continuity authority.
 */

import { normalizeFinishKind } from '../completion-finish-kind.mjs';
import { classifyReasoningBudgetOutcome } from '../reasoning-provider-options.mjs';

export const INFERENCE_HEALTH_SCHEMA = 'hg_inference_health_v1';
export const INFERENCE_HEALTH_INDEX_SCHEMA = 'hg_inference_health_index_v1';

/** @typedef {'none' | 'attempted' | 'recovered' | 'unrecovered'} RecoveryState */

/**
 * @param {object|null|undefined} profile
 * @returns {number|null}
 */
export function resolveConfiguredMaxTokens(profile) {
  const raw = profile?.maxTokens ?? profile?.max_tokens;
  if (raw === null || raw === undefined || raw === '') return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

/**
 * @param {object|null|undefined} usage
 * @returns {number|null}
 */
export function resolveUsageTotalTokens(usage) {
  if (!usage || typeof usage !== 'object') return null;
  const total = Number(usage.totalTokens ?? usage.total_tokens);
  if (Number.isFinite(total) && total >= 0) return total;
  const parts = [
    usage.inputTokens ?? usage.input_tokens,
    usage.outputTokens ?? usage.output_tokens,
    usage.reasoningTokens ?? usage.reasoning_tokens,
  ].map((v) => Number(v)).filter((n) => Number.isFinite(n) && n >= 0);
  if (!parts.length) return null;
  return parts.reduce((sum, n) => sum + n, 0);
}

/**
 * Utilization requires a known configured ceiling. Never invents near-ceiling bands.
 * @param {object|null|undefined} usage
 * @param {number|null|undefined} configuredMaxTokens
 * @returns {number|null}
 */
export function computeUtilization(usage, configuredMaxTokens) {
  if (configuredMaxTokens == null) return null;
  const ceiling = Number(configuredMaxTokens);
  if (!Number.isFinite(ceiling) || ceiling <= 0) return null;
  const total = resolveUsageTotalTokens(usage);
  if (total == null) return null;
  return total / ceiling;
}

/**
 * @param {object|null|undefined} usage
 * @returns {object|null}
 */
export function normalizeUsageSnapshot(usage) {
  if (!usage || typeof usage !== 'object') return null;
  return {
    input_tokens: Number.isFinite(Number(usage.inputTokens ?? usage.input_tokens))
      ? Number(usage.inputTokens ?? usage.input_tokens)
      : null,
    output_tokens: Number.isFinite(Number(usage.outputTokens ?? usage.output_tokens))
      ? Number(usage.outputTokens ?? usage.output_tokens)
      : null,
    reasoning_tokens: Number.isFinite(Number(usage.reasoningTokens ?? usage.reasoning_tokens))
      ? Number(usage.reasoningTokens ?? usage.reasoning_tokens)
      : null,
    total_tokens: resolveUsageTotalTokens(usage),
  };
}

/**
 * @param {object|null|undefined} correlation
 * @returns {{ dimension: 'inference_kind' | 'role', key: string } | null}
 */
export function resolveHealthGroup(correlation) {
  const kind = String(correlation?.inference_kind ?? '').trim();
  if (kind) return { dimension: 'inference_kind', key: kind };
  const role = String(correlation?.role ?? '').trim();
  if (role) return { dimension: 'role', key: role };
  return null;
}

/**
 * @param {string|null|undefined} inferenceKind
 * @returns {boolean}
 */
export function isContractCorrectionKind(inferenceKind) {
  return String(inferenceKind ?? '').endsWith('_contract_correction');
}

/**
 * Extract objective structural signals already present on decision patches.
 * @param {object|null|undefined} decision
 * @returns {{ structural_valid: boolean|null, structural_error: string|null }}
 */
export function extractStructuralSignals(decision) {
  if (!decision || typeof decision !== 'object') {
    return { structural_valid: null, structural_error: null };
  }

  const librarian = decision.librarian_proposal;
  if (librarian && typeof librarian === 'object') {
    const err = librarian.structural_parse_error
      ?? librarian.contract_lineage?.primary_parse_error
      ?? null;
    if (err) return { structural_valid: false, structural_error: String(err) };
    if (librarian.proposal_generation_failure === 'structural_parse_failed') {
      return { structural_valid: false, structural_error: 'structural_parse_failed' };
    }
    if (librarian.proposal_generation_stage === 'contract_correction'
      && librarian.contract_lineage?.correction_used) {
      const corrErr = librarian.contract_lineage?.correction_parse_error;
      if (corrErr) return { structural_valid: false, structural_error: String(corrErr) };
      return { structural_valid: true, structural_error: null };
    }
  }

  const plot = decision.plot_cognition;
  if (plot && typeof plot === 'object') {
    const err = plot.structural_parse_error
      ?? plot.contract_lineage?.primary_parse_error
      ?? null;
    if (err) return { structural_valid: false, structural_error: String(err) };
  }

  for (const key of [
    'character_orientation',
    'librarian_mediation',
    'storyteller_advisory',
    'storyteller_orientation',
  ]) {
    const block = decision[key];
    if (!block || typeof block !== 'object') continue;
    const err = block.structural_parse_error
      ?? block.contract_lineage?.primary_parse_error
      ?? null;
    if (err) return { structural_valid: false, structural_error: String(err) };
  }

  return { structural_valid: null, structural_error: null };
}

/**
 * @param {object} params
 * @returns {{ state: RecoveryState, primary_evidence_id: string|null, related_evidence_id: string|null }}
 */
export function deriveRecoveryState({
  correlation = null,
  decision = null,
  evidenceContext = null,
  existing = null,
}) {
  const prior = existing ?? {
    state: 'none',
    primary_evidence_id: null,
    related_evidence_id: null,
  };

  const lineage = decision?.librarian_proposal?.contract_lineage
    ?? decision?.plot_cognition?.contract_lineage
    ?? decision?.character_orientation?.contract_lineage
    ?? decision?.librarian_mediation?.contract_lineage
    ?? decision?.storyteller_advisory?.contract_lineage
    ?? null;

  const isCorrection = isContractCorrectionKind(correlation?.inference_kind)
    || Boolean(correlation?.parent_inference_id)
    || Boolean(evidenceContext?.parentInferenceId)
    || Boolean(evidenceContext?.primaryEvidenceId);

  if (lineage?.correction_used === true) {
    const primaryId = lineage.primary_evidence_id ?? prior.primary_evidence_id ?? null;
    const correctionId = lineage.correction_evidence_id ?? prior.related_evidence_id ?? null;
    const correctionOk = !lineage.correction_parse_error;
    return {
      state: correctionOk ? 'recovered' : 'unrecovered',
      primary_evidence_id: primaryId,
      related_evidence_id: correctionId,
    };
  }

  if (isCorrection) {
    return {
      state: 'attempted',
      primary_evidence_id: evidenceContext?.primaryEvidenceId
        ?? prior.primary_evidence_id
        ?? null,
      related_evidence_id: correlation?.evidence_id ?? prior.related_evidence_id ?? null,
    };
  }

  if (prior.state && prior.state !== 'none') {
    return prior;
  }

  return {
    state: 'none',
    primary_evidence_id: null,
    related_evidence_id: null,
  };
}

/**
 * Build Level-1 inference health from raw attempt / recording inputs.
 * @param {object} params
 */
export function buildInferenceHealth({
  profile = null,
  requestProfile = null,
  trace = null,
  response = null,
  assistantText = '',
  evidenceContext = null,
  correlation = null,
  decision = null,
  existingHealth = null,
}) {
  const configuredFromProfile = resolveConfiguredMaxTokens(profile);
  const configuredFromRequest = resolveConfiguredMaxTokens(requestProfile);
  const configured_max_tokens = configuredFromProfile
    ?? configuredFromRequest
    ?? existingHealth?.configured_max_tokens
    ?? null;

  const usageRaw = trace?.usage ?? response?.usage ?? null;
  const usage = normalizeUsageSnapshot(usageRaw) ?? existingHealth?.usage ?? null;
  const finish = trace?.finish ?? response?.finish ?? null;
  const finish_kind_raw = finish?.kind ?? existingHealth?.finish_kind_raw ?? null;
  const failed = Boolean(trace?.failed ?? response?.failed);
  const finish_class = normalizeFinishKind(finish_kind_raw, { failed });
  const budget = classifyReasoningBudgetOutcome(
    usageRaw ?? {
      reasoningTokens: usage?.reasoning_tokens,
      outputTokens: usage?.output_tokens,
    },
    finish ?? { kind: finish_kind_raw },
    assistantText ?? response?.assistant_text ?? '',
  );
  const hard_exhaustion = finish_class === 'output_limit'
    || budget.reasoning_budget_exhausted === true;
  const utilization = computeUtilization(
    usageRaw ?? {
      totalTokens: usage?.total_tokens,
      inputTokens: usage?.input_tokens,
      outputTokens: usage?.output_tokens,
      reasoningTokens: usage?.reasoning_tokens,
    },
    configured_max_tokens,
  );

  const structural = extractStructuralSignals(decision);
  let structural_valid = structural.structural_valid;
  let structural_error = structural.structural_error;
  if (structural_valid == null && existingHealth?.structural_valid != null) {
    structural_valid = existingHealth.structural_valid;
    structural_error = existingHealth.structural_error ?? null;
  }
  // Correction evidenceContext carries the *primary* structural error for lineage,
  // not this attempt's own structural validity.
  if (
    structural_valid == null
    && evidenceContext?.structuralError
    && !isContractCorrectionKind(correlation?.inference_kind ?? evidenceContext?.inferenceKind)
    && !evidenceContext?.parentInferenceId
  ) {
    structural_valid = false;
    structural_error = String(evidenceContext.structuralError);
  }

  const recovery = deriveRecoveryState({
    correlation,
    decision,
    evidenceContext,
    existing: existingHealth?.recovery ?? null,
  });

  return {
    schema: INFERENCE_HEALTH_SCHEMA,
    configured_max_tokens,
    usage,
    utilization,
    finish_kind_raw,
    finish_class,
    reasoning_budget_exhausted: budget.reasoning_budget_exhausted,
    hard_exhaustion,
    provider_failed: failed || finish_class === 'provider_error',
    structural_valid,
    structural_error,
    recovery,
  };
}

/**
 * Derive health for an already-persisted attempt (including historical records).
 * @param {object} attempt
 */
export function deriveInferenceHealthFromAttempt(attempt) {
  if (!attempt?.request && !attempt?.response) return null;
  return buildInferenceHealth({
    requestProfile: attempt?.request?.inference_profile ?? null,
    response: attempt?.response ?? null,
    assistantText: attempt?.response?.assistant_text ?? '',
    correlation: attempt?.correlation ?? null,
    decision: attempt?.decision ?? null,
    existingHealth: attempt?.inference_health ?? null,
  });
}

function emptyBucket() {
  return {
    attempt_count: 0,
    correction_attempt_count: 0,
    recovered_primary_failure_count: 0,
    hard_exhaustion_count: 0,
    provider_failure_count: 0,
    structural_failure_count: 0,
    utilization_sample_count: 0,
    utilization_sum: 0,
    utilization_min: null,
    utilization_max: null,
  };
}

function finalizeBucket(bucket) {
  const attempts = bucket.attempt_count;
  const rate = (n) => (attempts > 0 ? n / attempts : null);
  const utilCount = bucket.utilization_sample_count;
  return {
    attempt_count: attempts,
    correction_attempt_count: bucket.correction_attempt_count,
    correction_attempt_rate: rate(bucket.correction_attempt_count),
    recovered_primary_failure_count: bucket.recovered_primary_failure_count,
    recovered_primary_failure_rate: rate(bucket.recovered_primary_failure_count),
    hard_exhaustion_count: bucket.hard_exhaustion_count,
    hard_exhaustion_rate: rate(bucket.hard_exhaustion_count),
    provider_failure_count: bucket.provider_failure_count,
    provider_failure_rate: rate(bucket.provider_failure_count),
    structural_failure_count: bucket.structural_failure_count,
    structural_failure_rate: rate(bucket.structural_failure_count),
    utilization: utilCount > 0
      ? {
        sample_count: utilCount,
        mean: bucket.utilization_sum / utilCount,
        min: bucket.utilization_min,
        max: bucket.utilization_max,
      }
      : {
        sample_count: 0,
        mean: null,
        min: null,
        max: null,
        note: 'not_observable_without_configured_ceiling',
      },
  };
}

/**
 * @returns {object}
 */
export function emptyInferenceHealthIndex() {
  return {
    schema: INFERENCE_HEALTH_INDEX_SCHEMA,
    by_group: {},
    totals: finalizeBucket(emptyBucket()),
    observability: {
      inference_attempt_count: 0,
      grouped_attempt_count: 0,
      ungrouped_attempt_count: 0,
      attempts_without_ceiling: 0,
      attempts_with_ceiling: 0,
      note: 'Historical attempts lacking ceiling/lineage report honest incompleteness; missing fields are not treated as healthy.',
    },
  };
}

/**
 * @param {object} health
 * @param {object|null|undefined} correlation
 * @returns {boolean}
 */
function isRecoveredPrimaryFailure(health, correlation) {
  if (health?.recovery?.state !== 'recovered') return false;
  if (isContractCorrectionKind(correlation?.inference_kind)) return false;
  if (correlation?.parent_inference_id) return false;
  return health.hard_exhaustion === true
    || health.structural_valid === false
    || health.provider_failed === true
    || Boolean(health.structural_error);
}

/**
 * Fold one attempt into mutable accumulator buckets.
 * @param {object} acc
 * @param {object} attempt
 * @param {object|null} health
 */
export function accumulateInferenceHealthAttempt(acc, attempt, health) {
  if (!health || health.schema !== INFERENCE_HEALTH_SCHEMA) return;
  if (!attempt?.request || !attempt?.response) return;

  acc.observability.inference_attempt_count += 1;
  const group = resolveHealthGroup(attempt.correlation);
  if (!group) {
    acc.observability.ungrouped_attempt_count += 1;
  } else {
    acc.observability.grouped_attempt_count += 1;
  }

  if (health.configured_max_tokens == null) {
    acc.observability.attempts_without_ceiling += 1;
  } else {
    acc.observability.attempts_with_ceiling += 1;
  }

  const targets = [acc._totalsBucket];
  if (group) {
    const groupKey = `${group.dimension}:${group.key}`;
    if (!acc._groupBuckets[groupKey]) {
      acc._groupBuckets[groupKey] = {
        dimension: group.dimension,
        key: group.key,
        bucket: emptyBucket(),
      };
    }
    targets.push(acc._groupBuckets[groupKey].bucket);
  }

  const isCorrectionAttempt = isContractCorrectionKind(attempt.correlation?.inference_kind);

  for (const bucket of targets) {
    bucket.attempt_count += 1;
    if (isCorrectionAttempt) {
      bucket.correction_attempt_count += 1;
    }
    if (isRecoveredPrimaryFailure(health, attempt.correlation)) {
      bucket.recovered_primary_failure_count += 1;
    }
    if (health.hard_exhaustion) bucket.hard_exhaustion_count += 1;
    if (health.provider_failed) bucket.provider_failure_count += 1;
    if (health.structural_valid === false) bucket.structural_failure_count += 1;
    if (typeof health.utilization === 'number' && Number.isFinite(health.utilization)) {
      bucket.utilization_sample_count += 1;
      bucket.utilization_sum += health.utilization;
      bucket.utilization_min = bucket.utilization_min == null
        ? health.utilization
        : Math.min(bucket.utilization_min, health.utilization);
      bucket.utilization_max = bucket.utilization_max == null
        ? health.utilization
        : Math.max(bucket.utilization_max, health.utilization);
    }
  }
}

/**
 * @returns {{ index: object, _totalsBucket: object, _groupBuckets: object, observability: object }}
 */
export function beginInferenceHealthAccumulation() {
  const observability = emptyInferenceHealthIndex().observability;
  return {
    _totalsBucket: emptyBucket(),
    _groupBuckets: {},
    observability,
  };
}

/**
 * @param {object} acc
 * @returns {object}
 */
export function finalizeInferenceHealthIndex(acc) {
  const by_group = {};
  for (const [groupKey, entry] of Object.entries(acc._groupBuckets)) {
    by_group[groupKey] = {
      dimension: entry.dimension,
      key: entry.key,
      ...finalizeBucket(entry.bucket),
    };
  }
  return {
    schema: INFERENCE_HEALTH_INDEX_SCHEMA,
    by_group,
    totals: finalizeBucket(acc._totalsBucket),
    observability: acc.observability,
  };
}

/**
 * Build Level-2 index section from attempts.
 * @param {Iterable<object>} attempts
 */
export function buildInferenceHealthIndex(attempts) {
  const acc = beginInferenceHealthAccumulation();
  for (const attempt of attempts) {
    const health = deriveInferenceHealthFromAttempt(attempt);
    accumulateInferenceHealthAttempt(acc, attempt, health);
  }
  return finalizeInferenceHealthIndex(acc);
}

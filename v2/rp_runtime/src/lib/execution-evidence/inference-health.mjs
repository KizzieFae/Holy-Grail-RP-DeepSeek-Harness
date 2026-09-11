/**
 * Observational inference-health contract (#114).
 * Reconstructable from durable attempt evidence; not Continuity authority.
 */

import { normalizeFinishKind } from '../completion-finish-kind.mjs';
import {
  isApplicationTokenQuotaEnforced,
  referenceTokenCeilingForInferenceKind,
  referenceTokenCeilingForRole,
  UNCAPPED_INFERENCE_KINDS,
} from '../../application/application-settings.mjs';
import { classifyReasoningBudgetOutcome } from '../reasoning-provider-options.mjs';

export const INFERENCE_HEALTH_SCHEMA = 'hg_inference_health_v1';
export const INFERENCE_HEALTH_INDEX_SCHEMA = 'hg_inference_health_index_v1';

/** @typedef {'none' | 'attempted' | 'recovered' | 'unrecovered'} RecoveryState */

/**
 * Baseline reference quota for telemetry/catalog comparison (not enforced).
 * @param {object|null|undefined} correlation
 * @returns {number | 'UNCAPPED' | null}
 */
export function resolveReferenceApplicationTokenQuota(correlation = null) {
  const kind = correlation?.inference_kind ?? null;
  if (kind && UNCAPPED_INFERENCE_KINDS.has(kind)) {
    return 'UNCAPPED';
  }
  if (kind) {
    const kindCeiling = referenceTokenCeilingForInferenceKind(kind);
    if (Number.isFinite(kindCeiling)) {
      return kindCeiling;
    }
  }
  const role = correlation?.role ?? null;
  if (role) {
    return referenceTokenCeilingForRole(role);
  }
  return null;
}

/**
 * @param {object|null|undefined} params
 * @returns {string}
 */
export function resolveApplicationQuotaState({
  applicationQuotaEnforced = isApplicationTokenQuotaEnforced(),
  configuredMaxTokens = null,
  characterizationMode = false,
  calibrationMode = false,
  finishClass = null,
}) {
  if (characterizationMode) {
    return applicationQuotaEnforced ? 'characterization_capped' : 'characterization_uncapped';
  }
  if (calibrationMode && applicationQuotaEnforced) {
    return 'calibration_capped';
  }
  if (!applicationQuotaEnforced) {
    if (finishClass === 'output_limit' && configuredMaxTokens == null) {
      return 'provider_or_external_limit';
    }
    return 'application_quota_disabled';
  }
  if (configuredMaxTokens == null) {
    return 'production_uncapped_kind';
  }
  if (finishClass === 'output_limit') {
    return 'production_capped_exhaustion';
  }
  return 'production_capped';
}

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
 * Token quantity constrained by configured `max_tokens` (output-generation ceiling).
 *
 * Repository evidence (`application-settings` "output headroom",
 * `classifyReasoningBudgetOutcome`): the ceiling bounds generation — visible
 * `outputTokens` plus `reasoningTokens` when present. Prompt/`inputTokens` are
 * never included; `totalTokens` is not used as a utilization numerator because it
 * mixes input with generation.
 *
 * @param {object|null|undefined} usage
 * @returns {number|null}
 */
export function resolveCeilingConstrainedTokens(usage) {
  if (!usage || typeof usage !== 'object') return null;
  const output = Number(usage.outputTokens ?? usage.output_tokens);
  const reasoning = Number(usage.reasoningTokens ?? usage.reasoning_tokens);
  const hasOutput = Number.isFinite(output) && output >= 0;
  const hasReasoning = Number.isFinite(reasoning) && reasoning >= 0;
  if (!hasOutput && !hasReasoning) return null;
  return (hasOutput ? output : 0) + (hasReasoning ? reasoning : 0);
}

/**
 * Utilization = ceiling-constrained generation tokens / configured output ceiling.
 * Requires a known configured ceiling. Never invents near-ceiling bands.
 * @param {object|null|undefined} usage
 * @param {number|null|undefined} configuredMaxTokens
 * @returns {number|null}
 */
export function computeUtilization(usage, configuredMaxTokens) {
  if (configuredMaxTokens == null) return null;
  const ceiling = Number(configuredMaxTokens);
  if (!Number.isFinite(ceiling) || ceiling <= 0) return null;
  const constrained = resolveCeilingConstrainedTokens(usage);
  if (constrained == null) return null;
  return constrained / ceiling;
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
 * @param {object} block
 * @param {{ treatAsCorrection: boolean }} options
 * @returns {{ structural_valid: boolean|null, structural_error: string|null } | null}
 */
function structuralFromDecisionBlock(block, { treatAsCorrection }) {
  if (!block || typeof block !== 'object') return null;
  const lineage = block.contract_lineage ?? null;
  const stage = String(block.proposal_generation_stage ?? block.mediation_generation_stage ?? '');

  if (treatAsCorrection || stage === 'contract_correction') {
    // Correction attempt: own structural result only — never primary_parse_error.
    const ownErr = stage === 'contract_correction'
      ? (block.structural_parse_error ?? null)
      : (block.structural_parse_error ?? null);
    const corrErr = lineage?.correction_parse_error ?? ownErr ?? null;
    if (corrErr) {
      return { structural_valid: false, structural_error: String(corrErr) };
    }
    if (lineage?.correction_used === true) {
      return { structural_valid: true, structural_error: null };
    }
    return null;
  }

  // Primary (or non-correction) attempt: own structural failure / primary lineage error.
  const err = block.structural_parse_error
    ?? lineage?.primary_parse_error
    ?? null;
  if (err) return { structural_valid: false, structural_error: String(err) };
  if (block.proposal_generation_failure === 'structural_parse_failed') {
    return { structural_valid: false, structural_error: 'structural_parse_failed' };
  }
  return null;
}

/**
 * Extract objective structural signals already present on decision patches.
 * Structural validity is evaluated for **this attempt**. Primary parse errors in
 * contract lineage remain lineage/recovery context and must not mark a successful
 * correction attempt as structurally failed.
 *
 * @param {object|null|undefined} decision
 * @param {{ correlation?: object|null }} [options]
 * @returns {{ structural_valid: boolean|null, structural_error: string|null }}
 */
export function extractStructuralSignals(decision, options = {}) {
  if (!decision || typeof decision !== 'object') {
    return { structural_valid: null, structural_error: null };
  }

  const correlation = options.correlation ?? null;
  const treatAsCorrection = isContractCorrectionKind(correlation?.inference_kind);

  const blocks = [
    decision.post_commit_semantic,
    decision.librarian_proposal,
    decision.plot_cognition,
    decision.character_orientation,
    decision.librarian_mediation,
    decision.storyteller_advisory,
    decision.storyteller_orientation,
  ];
  for (const block of blocks) {
    const signal = structuralFromDecisionBlock(block, { treatAsCorrection });
    if (signal) return signal;
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

  const lineage = decision?.post_commit_semantic?.contract_lineage
    ?? decision?.librarian_proposal?.contract_lineage
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
  inferenceWallClockMs = null,
  turnBoundaryTiming = null,
  idleBoundaryDiagnostic = null,
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
      outputTokens: usage?.output_tokens,
      reasoningTokens: usage?.reasoning_tokens,
      // input/total intentionally omitted from utilization numerator source
      inputTokens: usage?.input_tokens,
      totalTokens: usage?.total_tokens,
    },
    configured_max_tokens,
  );

  const structural = extractStructuralSignals(decision, { correlation });
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

  const application_quota_enforced = evidenceContext?.applicationTokenQuotasEnforced
    ?? existingHealth?.application_quota_enforced
    ?? isApplicationTokenQuotaEnforced();
  const calibration_mode = evidenceContext?.calibrationMode === true
    || correlation?.calibration_mode === true;
  const characterization_mode = evidenceContext?.characterizationMode === true
    || correlation?.characterization_mode === true;
  const reference_application_token_quota = evidenceContext?.referenceApplicationTokenQuota
    ?? existingHealth?.reference_application_token_quota
    ?? resolveReferenceApplicationTokenQuota(correlation);
  const application_quota_state = resolveApplicationQuotaState({
    applicationQuotaEnforced: application_quota_enforced,
    configuredMaxTokens: configured_max_tokens,
    characterizationMode: characterization_mode,
    calibrationMode: calibration_mode,
    finishClass: finish_class,
  });

  return {
    schema: INFERENCE_HEALTH_SCHEMA,
    configured_max_tokens,
    application_quota_enforced,
    reference_application_token_quota,
    application_quota_state,
    characterization_mode,
    calibration_mode,
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
    timing: buildInferenceTiming({
      turnBoundaryTiming,
      inferenceWallClockMs,
      existingTiming: existingHealth?.timing ?? null,
      idleBoundaryDiagnostic,
    }),
  };
}

/**
 * @param {object} params
 */
export function buildInferenceTiming({
  turnBoundaryTiming = null,
  inferenceWallClockMs = null,
  existingTiming = null,
  idleBoundaryDiagnostic = null,
}) {
  if (existingTiming?.timing_observed === true
    && existingTiming?.measurement === 'dsh_session_turn_boundary') {
    const next = { ...existingTiming };
    if (idleBoundaryDiagnostic && !next.diagnostics) {
      next.diagnostics = { idle_boundary: idleBoundaryDiagnostic };
    }
    return next;
  }
  if (turnBoundaryTiming && typeof turnBoundaryTiming === 'object') {
    if (turnBoundaryTiming.timing_observed === true) {
      const timing = {
        timing_observed: true,
        measurement: turnBoundaryTiming.measurement ?? 'dsh_session_turn_boundary',
        started_at: turnBoundaryTiming.started_at ?? null,
        ended_at: turnBoundaryTiming.ended_at ?? null,
        inference_wall_clock_ms: Number(turnBoundaryTiming.inference_wall_clock_ms),
        dsh_turn: turnBoundaryTiming.dsh_turn ?? null,
        dsh_inference_session_id: turnBoundaryTiming.dsh_inference_session_id ?? null,
        turn_start_seq: turnBoundaryTiming.turn_start_seq ?? null,
        turn_end_seq: turnBoundaryTiming.turn_end_seq ?? null,
      };
      if (idleBoundaryDiagnostic) {
        timing.diagnostics = { idle_boundary: idleBoundaryDiagnostic };
      }
      return timing;
    }
    const unavailable = {
      timing_observed: false,
      measurement: turnBoundaryTiming.measurement ?? 'dsh_session_turn_boundary',
      unavailable_reason: turnBoundaryTiming.unavailable_reason ?? 'turn_boundary_not_observed',
      dsh_turn: turnBoundaryTiming.dsh_turn ?? null,
      dsh_inference_session_id: turnBoundaryTiming.dsh_inference_session_id ?? null,
    };
    if (idleBoundaryDiagnostic) {
      unavailable.diagnostics = { idle_boundary: idleBoundaryDiagnostic };
    }
    return unavailable;
  }
  if (existingTiming) {
    return existingTiming;
  }
  if (Number.isFinite(Number(inferenceWallClockMs)) && Number(inferenceWallClockMs) >= 0) {
    return {
      timing_observed: true,
      inference_wall_clock_ms: Number(inferenceWallClockMs),
      measurement: 'substrate_runEphemeralInference_idle_boundary',
      legacy_idle_boundary: true,
    };
  }
  return null;
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

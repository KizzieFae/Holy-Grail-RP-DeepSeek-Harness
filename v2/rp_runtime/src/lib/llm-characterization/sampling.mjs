/**
 * Bounded adaptive sampling for LLM characterization (#152).
 */

export const CHARACTERIZATION_BASELINE_ATTEMPTS = 3;
export const CHARACTERIZATION_EXPANSION_INCREMENT = 3;
export const CHARACTERIZATION_MAX_ATTEMPTS = 9;
export const CHARACTERIZATION_CV_EXPANSION_THRESHOLD = 0.35;
export const CHARACTERIZATION_CONSECUTIVE_STOP = 3;
export const CHARACTERIZATION_FAILURE_SIGNATURE_STOP = 5;

export function shouldExpandCharacterizationSampling(validNaturalCount, totalAttempts, signals = {}) {
  if (totalAttempts >= CHARACTERIZATION_MAX_ATTEMPTS) return false;
  if (validNaturalCount >= CHARACTERIZATION_BASELINE_ATTEMPTS && !signals.forceExpansion) {
    return false;
  }
  return Boolean(
    signals.structuredFailure
    || signals.retryOrCorrection
    || signals.externalLimitTermination
    || signals.tokenTotalCvAboveThreshold
    || signals.wallClockCvAboveThreshold
    || signals.divergentFinishBehavior
    || signals.highReasoningShareObservation
    || signals.forceExpansion,
  );
}

export function coefficientOfVariation(values) {
  const nums = values.filter((v) => Number.isFinite(v));
  if (nums.length < 2) return null;
  const mean = nums.reduce((sum, n) => sum + n, 0) / nums.length;
  if (mean === 0) return null;
  const variance = nums.reduce((sum, n) => sum + ((n - mean) ** 2), 0) / nums.length;
  return Math.sqrt(variance) / mean;
}

export function isValidNaturalCompletionAttempt(attempt) {
  if (attempt?.censored === true) return false;
  if (attempt?.external_limit_hit === true) return false;
  const finish = String(attempt?.finish_kind ?? attempt?.finish ?? '').trim();
  if (finish === 'max-tokens') return false;
  if (attempt?.structured_failure === true) return false;
  return finish === 'stop' || finish === 'complete' || finish === '';
}

export function shouldStopCharacterizationSampling(state) {
  if (state.totalAttempts >= CHARACTERIZATION_MAX_ATTEMPTS) return { stop: true, reason: 'max_attempts' };
  if (state.consecutiveNonNatural >= CHARACTERIZATION_CONSECUTIVE_STOP) {
    return { stop: true, reason: 'consecutive_non_natural' };
  }
  if (state.failureSignatureCount >= CHARACTERIZATION_FAILURE_SIGNATURE_STOP) {
    return { stop: true, reason: 'repeated_failure_signature' };
  }
  return { stop: false, reason: null };
}

export function classifyCharacterizationStability({
  validNaturalAttempts,
  censoredAttempts,
  externalLimitAttempts,
  pathologicalSignal,
}) {
  if (pathologicalSignal) return 'pathological_signal';
  if (validNaturalAttempts.length === 0) return 'unstable';
  if (validNaturalAttempts.length < CHARACTERIZATION_BASELINE_ATTEMPTS) {
    return censoredAttempts > 0 || externalLimitAttempts > 0 ? 'unstable' : 'variable';
  }
  const totals = validNaturalAttempts
    .map((a) => a.total_tokens)
    .filter((v) => Number.isFinite(v));
  const cv = coefficientOfVariation(totals);
  if (cv != null && cv > CHARACTERIZATION_CV_EXPANSION_THRESHOLD) return 'variable';
  return 'stable';
}

/** Derive adaptive expansion signals from accumulated attempts. */
export function collectExpansionSignals(attempts) {
  const validNatural = attempts.filter((a) => isValidNaturalCompletionAttempt(a));
  const tokenTotals = validNatural.map((a) => a.total_tokens);
  const wallClocks = validNatural.map((a) => a.inference_wall_clock_ms);
  const finishKinds = new Set(attempts.map((a) => String(a.finish_kind ?? 'unknown')));
  const highReasoningShareObservation = validNatural.some((attempt) => {
    if (!Number.isFinite(attempt.total_tokens) || attempt.total_tokens <= 0) return false;
    if (!Number.isFinite(attempt.reasoning_tokens)) return false;
    return (attempt.reasoning_tokens / attempt.total_tokens) > 0.5;
  });
  return {
    structuredFailure: attempts.some((a) => a.structured_failure === true),
    retryOrCorrection: attempts.some((a) => a.retry_or_correction === true),
    externalLimitTermination: attempts.some((a) => a.external_limit_hit === true),
    tokenTotalCvAboveThreshold: (() => {
      const cv = coefficientOfVariation(tokenTotals);
      return cv != null && cv > CHARACTERIZATION_CV_EXPANSION_THRESHOLD;
    })(),
    wallClockCvAboveThreshold: (() => {
      const cv = coefficientOfVariation(wallClocks);
      return cv != null && cv > CHARACTERIZATION_CV_EXPANSION_THRESHOLD;
    })(),
    divergentFinishBehavior: finishKinds.size > 1,
    highReasoningShareObservation,
  };
}

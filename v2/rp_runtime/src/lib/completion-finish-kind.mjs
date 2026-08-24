/**
 * Provider-neutral completion finish normalization for inference acceptance.
 */

/** @typedef {'complete' | 'output_limit' | 'provider_error' | 'unknown'} NormalizedFinishKind */

const COMPLETE_ALIASES = new Set([
  'stop',
  'end',
  'end_turn',
  'completed',
  'done',
]);

const OUTPUT_LIMIT_ALIASES = new Set([
  'length',
  'max_tokens',
  'max_output',
  'max_tokens_reached',
  'model_length',
]);

const PROVIDER_ERROR_ALIASES = new Set([
  'error',
  'aborted',
  'cancelled',
  'canceled',
]);

/**
 * @param {string | null | undefined} rawKind
 * @param {{ failed?: boolean }} [options]
 * @returns {NormalizedFinishKind}
 */
export function normalizeFinishKind(rawKind, options = {}) {
  if (options.failed) {
    return 'provider_error';
  }
  const normalized = String(rawKind ?? '')
    .trim()
    .toLowerCase()
    .replace(/-/g, '_');
  if (!normalized) {
    return 'unknown';
  }
  if (COMPLETE_ALIASES.has(normalized)) {
    return 'complete';
  }
  if (OUTPUT_LIMIT_ALIASES.has(normalized)) {
    return 'output_limit';
  }
  if (PROVIDER_ERROR_ALIASES.has(normalized)) {
    return 'provider_error';
  }
  return 'unknown';
}

/**
 * @param {string | null | undefined} message
 * @param {object | null | undefined} trace
 * @returns {boolean}
 */
export function isPermanentProviderFailure(message, trace) {
  const text = String(message ?? trace?.failure?.message ?? '').toLowerCase();
  if (!text) {
    return false;
  }
  const permanentPatterns = [
    /\b401\b/,
    /\b403\b/,
    /\b404\b/,
    /unauthorized/,
    /forbidden/,
    /invalid api key/,
    /authentication/,
    /invalid model/,
    /model not found/,
    /unknown model/,
    /configuration/,
    /not configured/,
  ];
  return permanentPatterns.some((pattern) => pattern.test(text));
}

/**
 * @param {string | null | undefined} message
 * @returns {boolean}
 */
export function isTransientProviderFailure(message) {
  const text = String(message ?? '').toLowerCase();
  if (!text) {
    return false;
  }
  const transientPatterns = [
    /\b429\b/,
    /\b502\b/,
    /\b503\b/,
    /\b504\b/,
    /timeout/,
    /timed out/,
    /rate limit/,
    /too many requests/,
    /connection reset/,
    /econnreset/,
    /temporarily unavailable/,
  ];
  return transientPatterns.some((pattern) => pattern.test(text));
}

/**
 * @param {{
 *   attemptIndex: number,
 *   maxAttempts: number,
 *   normalizedKind: NormalizedFinishKind,
 *   permanentProviderFailure?: boolean,
 *   validationRetryable?: boolean,
 *   emptyOutput?: boolean,
 *   failureMessage?: string | null,
 * }} ctx
 * @returns {{ retryable: boolean, retryDecision: 'accept' | 'retry' | 'terminal_fallback' }}
 */
export function narratorRetryDecision(ctx) {
  const {
    attemptIndex,
    maxAttempts,
    normalizedKind,
    permanentProviderFailure = false,
    validationRetryable = false,
    emptyOutput = false,
    failureMessage = null,
  } = ctx;
  const attemptsRemain = attemptIndex < maxAttempts - 1;

  if (normalizedKind === 'complete' && !emptyOutput && !validationRetryable) {
    return { retryable: false, retryDecision: 'accept' };
  }

  if (permanentProviderFailure || !attemptsRemain) {
    return { retryable: false, retryDecision: 'terminal_fallback' };
  }

  if (
    normalizedKind === 'output_limit'
    || normalizedKind === 'unknown'
    || emptyOutput
    || validationRetryable
    || normalizedKind === 'provider_error'
    || isTransientProviderFailure(failureMessage)
  ) {
    return { retryable: true, retryDecision: 'retry' };
  }

  return { retryable: true, retryDecision: 'retry' };
}

/**
 * Map DSH inference trace to provider-neutral narrator execution outcomes for Host persistence.
 */

import { normalizeFinishKind } from './completion-finish-kind.mjs';

/**
 * @param {object | null | undefined} trace
 * @param {string} rawText
 * @returns {'succeeded' | 'empty_output' | 'inference_error' | 'output_limit'}
 */
export function classifyNarratorInferenceOutcome(trace, rawText) {
  if (trace?.failed) {
    return 'inference_error';
  }
  const text = String(rawText ?? '').trim();
  if (!text) {
    return 'empty_output';
  }
  const normalized = normalizeFinishKind(trace?.finish?.kind, { failed: false });
  if (normalized === 'output_limit') {
    return 'output_limit';
  }
  if (normalized === 'provider_error' || normalized === 'unknown') {
    return 'inference_error';
  }
  return 'succeeded';
}

/**
 * @param {string} failureMessage
 * @returns {'empty_output' | 'inference_error'}
 */
export function classifyNarratorFailureOutcome(failureMessage) {
  const message = String(failureMessage ?? '').toLowerCase();
  if (message.includes('empty presentation output')) {
    return 'empty_output';
  }
  return 'inference_error';
}

/**
 * @param {'complete' | 'output_limit' | 'provider_error' | 'unknown'} normalizedKind
 * @param {boolean} [emptyOutput]
 * @returns {'succeeded' | 'empty_output' | 'inference_error' | 'output_limit'}
 */
export function inferenceOutcomeFromNormalizedKind(normalizedKind, emptyOutput = false) {
  if (emptyOutput) {
    return 'empty_output';
  }
  if (normalizedKind === 'output_limit') {
    return 'output_limit';
  }
  if (normalizedKind === 'complete') {
    return 'succeeded';
  }
  return 'inference_error';
}

export { normalizeFinishKind } from './completion-finish-kind.mjs';

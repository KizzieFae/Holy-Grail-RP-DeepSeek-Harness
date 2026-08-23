/**
 * Map DSH inference trace to provider-neutral narrator execution outcomes for Host persistence.
 */

const OUTPUT_LIMIT_FINISH_KINDS = new Set(['length', 'max_tokens', 'max_output']);

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
  const finish = trace?.finish;
  if (finish && typeof finish === 'object') {
    const kind = String(finish.kind ?? '').toLowerCase();
    if (OUTPUT_LIMIT_FINISH_KINDS.has(kind)) {
      return 'output_limit';
    }
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

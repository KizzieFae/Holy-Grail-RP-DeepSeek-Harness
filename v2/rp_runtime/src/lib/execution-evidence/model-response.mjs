import { MODEL_RESPONSE_SCHEMA } from './config.mjs';

/**
 * @param {object} params
 * @param {object} params.trace
 * @param {string} params.assistantText
 */
export function buildModelResponse({ trace, assistantText }) {
  const reasoningText = trace?.reasoning_text;
  return {
    schema: MODEL_RESPONSE_SCHEMA,
    assistant_text: String(assistantText ?? ''),
    failed: Boolean(trace?.failed),
    failure: trace?.failure ?? null,
    finish: trace?.finish ?? null,
    usage: trace?.usage ?? null,
    provider: trace?.provider ?? null,
    model: trace?.model ?? null,
    turn_end_reason: trace?.turn_end_reason ?? null,
    ...(reasoningText ? { reasoning_text: String(reasoningText) } : {}),
  };
}

/** Supported Holy Grail reasoning profile ids (DSH adapter contract). */
export const REASONING_LEVELS = ['off', 'low', 'high', 'max'];

/**
 * Map a role inference profile reasoningEffort to provider-effective options.
 * Per-call agent options must win over mount-time defaults.
 *
 * @param {string|null|undefined} reasoningEffort
 * @returns {{ reasoningEffort: string, thinking: 'enabled' | 'disabled' }}
 */
export function mapReasoningEffortToProviderOptions(reasoningEffort) {
  const effort = String(reasoningEffort ?? 'low').trim().toLowerCase();
  if (effort === 'off') {
    return { reasoningEffort: 'off', thinking: 'disabled' };
  }
  if (!REASONING_LEVELS.includes(effort)) {
    return { reasoningEffort: 'low', thinking: 'enabled' };
  }
  return { reasoningEffort: effort, thinking: 'enabled' };
}

/**
 * @param {object|null|undefined} usage
 * @param {object|null|undefined} finish
 * @param {string} assistantText
 */
export function classifyReasoningBudgetOutcome(usage, finish, assistantText) {
  const reasoningTokens = Number(usage?.reasoningTokens ?? 0);
  const outputTokens = Number(usage?.outputTokens ?? 0);
  const finishKind = String(finish?.kind ?? '').toLowerCase();
  const emptyOutput = !String(assistantText ?? '').trim();
  const maxTokensHit = finishKind.includes('max') && finishKind.includes('token');
  return {
    reasoning_tokens: reasoningTokens,
    visible_output_tokens: outputTokens,
    reasoning_budget_exhausted: Boolean(
      maxTokensHit && emptyOutput && reasoningTokens > 0,
    ),
  };
}

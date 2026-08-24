import assert from 'node:assert/strict';
import test from 'node:test';

import {
  classifyReasoningBudgetOutcome,
  mapReasoningEffortToProviderOptions,
} from '../src/lib/reasoning-provider-options.mjs';

test('reasoning provider options: off disables thinking', () => {
  assert.deepEqual(mapReasoningEffortToProviderOptions('off'), {
    reasoningEffort: 'off',
    thinking: 'disabled',
  });
});

test('reasoning provider options: low/high/max enable thinking', () => {
  for (const effort of ['low', 'high', 'max']) {
    assert.deepEqual(mapReasoningEffortToProviderOptions(effort), {
      reasoningEffort: effort,
      thinking: 'enabled',
    });
  }
});

test('reasoning provider options: unknown effort falls back to low', () => {
  assert.deepEqual(mapReasoningEffortToProviderOptions('turbo'), {
    reasoningEffort: 'low',
    thinking: 'enabled',
  });
});

test('reasoning budget outcome: detects reasoning-only exhaustion', () => {
  const outcome = classifyReasoningBudgetOutcome(
    { reasoningTokens: 120, outputTokens: 0 },
    { kind: 'max_tokens' },
    '',
  );
  assert.equal(outcome.reasoning_budget_exhausted, true);
  assert.equal(outcome.reasoning_tokens, 120);
});

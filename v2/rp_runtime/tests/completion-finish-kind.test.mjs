import assert from 'node:assert/strict';
import test from 'node:test';

import {
  isPermanentProviderFailure,
  isTransientProviderFailure,
  normalizeFinishKind,
  narratorRetryDecision,
} from '../src/lib/completion-finish-kind.mjs';

test('normalizeFinishKind maps completion aliases', () => {
  assert.equal(normalizeFinishKind('stop'), 'complete');
  assert.equal(normalizeFinishKind('END_TURN'), 'complete');
});

test('normalizeFinishKind maps output-limit aliases including hyphenated max-tokens', () => {
  assert.equal(normalizeFinishKind('length'), 'output_limit');
  assert.equal(normalizeFinishKind('max_tokens'), 'output_limit');
  assert.equal(normalizeFinishKind('max-tokens'), 'output_limit');
  assert.equal(normalizeFinishKind('MAX-OUTPUT'), 'output_limit');
});

test('normalizeFinishKind maps provider errors and unknown', () => {
  assert.equal(normalizeFinishKind('error'), 'provider_error');
  assert.equal(normalizeFinishKind('aborted'), 'provider_error');
  assert.equal(normalizeFinishKind(null), 'unknown');
  assert.equal(normalizeFinishKind('weird_provider_kind'), 'unknown');
  assert.equal(normalizeFinishKind('stop', { failed: true }), 'provider_error');
});

test('isPermanentProviderFailure detects auth/config failures', () => {
  assert.equal(isPermanentProviderFailure('HTTP 401 unauthorized'), true);
  assert.equal(isPermanentProviderFailure('invalid model foo'), true);
  assert.equal(isPermanentProviderFailure('timeout'), false);
});

test('isTransientProviderFailure detects retryable infrastructure failures', () => {
  assert.equal(isTransientProviderFailure('HTTP 503 temporarily unavailable'), true);
  assert.equal(isTransientProviderFailure('rate limit exceeded'), true);
});

test('narratorRetryDecision respects two-attempt bound', () => {
  assert.deepEqual(
    narratorRetryDecision({
      attemptIndex: 0,
      maxAttempts: 2,
      normalizedKind: 'output_limit',
    }),
    { retryable: true, retryDecision: 'retry' },
  );
  assert.deepEqual(
    narratorRetryDecision({
      attemptIndex: 1,
      maxAttempts: 2,
      normalizedKind: 'output_limit',
    }),
    { retryable: false, retryDecision: 'terminal_fallback' },
  );
  assert.deepEqual(
    narratorRetryDecision({
      attemptIndex: 0,
      maxAttempts: 2,
      normalizedKind: 'complete',
    }),
    { retryable: false, retryDecision: 'accept' },
  );
});

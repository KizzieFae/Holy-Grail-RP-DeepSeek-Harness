import assert from 'node:assert/strict';
import test from 'node:test';

import {
  LIVE_CANDIDATE_CEILING,
  SEMANTIC_EVAL_INFRA_RETRIES,
  clampLiveCandidateLimit,
} from '../src/lib/phase-execution-policy.mjs';
import { characterCandidateLimit } from '../src/plugins/hg-phase-executors/character-candidate-budget.mjs';
import { directorSelectionLimit } from '../src/plugins/hg-phase-executors/director-candidate-budget.mjs';

test('SEMANTIC_EVAL_INFRA_RETRIES preserves one inclusive infra retry', () => {
  assert.equal(SEMANTIC_EVAL_INFRA_RETRIES, 1);
});

test('clampLiveCandidateLimit matches Character and Director budget modules', () => {
  assert.equal(LIVE_CANDIDATE_CEILING, 3);
  assert.equal(clampLiveCandidateLimit(99), 3);
  assert.equal(clampLiveCandidateLimit(1), 1);
  assert.equal(clampLiveCandidateLimit(0), 1);
  assert.equal(clampLiveCandidateLimit(Number.NaN), 1);
  assert.equal(clampLiveCandidateLimit(undefined), 3);
  assert.equal(characterCandidateLimit(99), clampLiveCandidateLimit(99));
  assert.equal(directorSelectionLimit(99), clampLiveCandidateLimit(99));
  assert.equal(characterCandidateLimit(2), directorSelectionLimit(2));
});

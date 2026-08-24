import assert from 'node:assert/strict';
import test from 'node:test';

import {
  classifyNarratorFailureOutcome,
  classifyNarratorInferenceOutcome,
  inferenceOutcomeFromNormalizedKind,
} from '../src/lib/narrator-inference-outcome.mjs';

test('classifyNarratorInferenceOutcome: succeeded', () => {
  assert.equal(
    classifyNarratorInferenceOutcome({ failed: false, finish: { kind: 'stop' } }, 'Hello'),
    'succeeded',
  );
});

test('classifyNarratorInferenceOutcome: empty_output', () => {
  assert.equal(classifyNarratorInferenceOutcome({ failed: false }, ''), 'empty_output');
});

test('classifyNarratorInferenceOutcome: inference_error from trace failure', () => {
  assert.equal(
    classifyNarratorInferenceOutcome({ failed: true, finish: { kind: 'error' } }, ''),
    'inference_error',
  );
});

test('classifyNarratorInferenceOutcome: output_limit from finish kind', () => {
  assert.equal(
    classifyNarratorInferenceOutcome(
      { failed: false, finish: { kind: 'length' } },
      'Truncated partial text',
    ),
    'output_limit',
  );
  assert.equal(
    classifyNarratorInferenceOutcome(
      { failed: false, finish: { kind: 'max-tokens' } },
      'Truncated partial text',
    ),
    'output_limit',
  );
});

test('classifyNarratorInferenceOutcome: unknown maps to inference_error', () => {
  assert.equal(
    classifyNarratorInferenceOutcome(
      { failed: false, finish: { kind: 'weird' } },
      'Some text',
    ),
    'inference_error',
  );
});

test('classifyNarratorFailureOutcome: empty vs inference_error', () => {
  assert.equal(
    classifyNarratorFailureOutcome('narrator produced empty presentation output'),
    'empty_output',
  );
  assert.equal(classifyNarratorFailureOutcome('provider timeout'), 'inference_error');
});

test('inferenceOutcomeFromNormalizedKind', () => {
  assert.equal(inferenceOutcomeFromNormalizedKind('complete'), 'succeeded');
  assert.equal(inferenceOutcomeFromNormalizedKind('output_limit'), 'output_limit');
  assert.equal(inferenceOutcomeFromNormalizedKind('unknown'), 'inference_error');
  assert.equal(inferenceOutcomeFromNormalizedKind('complete', true), 'empty_output');
});

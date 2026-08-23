import assert from 'node:assert/strict';
import test from 'node:test';

import {
  classifyNarratorFailureOutcome,
  classifyNarratorInferenceOutcome,
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
});

test('classifyNarratorFailureOutcome: empty vs inference_error', () => {
  assert.equal(
    classifyNarratorFailureOutcome('narrator produced empty presentation output'),
    'empty_output',
  );
  assert.equal(classifyNarratorFailureOutcome('provider timeout'), 'inference_error');
});

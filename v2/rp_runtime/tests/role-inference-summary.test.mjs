import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildCharacterSummary,
  buildDirectorBypassSummary,
  buildDirectorInferenceSummary,
  buildNarratorSummary,
  classifyInferenceExecution,
  finalizeRoleInferenceSummary,
  notReachedRoleSummary,
} from '../src/lib/role-inference-summary.mjs';

test('classifyInferenceExecution distinguishes completed vs attempted', () => {
  assert.equal(classifyInferenceExecution(null), 'not_executed');
  assert.equal(classifyInferenceExecution({ failed: false }), 'completed');
  assert.equal(classifyInferenceExecution({ failed: true }), 'attempted');
});

test('buildDirectorBypassSummary is non-inference bypass', () => {
  const summary = buildDirectorBypassSummary();
  assert.equal(summary.inference_execution, 'not_executed');
  assert.equal(summary.phase_outcome, 'bypassed');
  assert.equal(summary.inference_trace, null);
});

test('buildNarratorSummary marks degraded fallback with last inference trace', () => {
  const trace = { provider: 'hg-mock', failed: false };
  const summary = buildNarratorSummary({
    presentation_rendered: false,
    presentation_failed: true,
    narrator_inference_trace: trace,
    narrator_inference_session_id: 'sess-1',
    narrator_evidence_id: 'ev-1',
  });
  assert.equal(summary.phase_outcome, 'degraded');
  assert.equal(summary.inference_execution, 'completed');
  assert.equal(summary.inference_trace, trace);
  assert.equal(summary.inference_session_id, 'sess-1');
  assert.equal(summary.evidence_id, 'ev-1');
});

test('buildNarratorSummary marks prepare failure before inference', () => {
  const summary = buildNarratorSummary({
    presentation_rendered: false,
    presentation_failed: true,
    narrator_inference_trace: null,
    narrator_inference_session_id: null,
    narrator_evidence_id: null,
  });
  assert.equal(summary.phase_outcome, 'degraded');
  assert.equal(summary.inference_execution, 'not_executed');
  assert.equal(summary.inference_trace, null);
});

test('buildNarratorSummary marks boundary throw attempted without trace', () => {
  const summary = buildNarratorSummary({
    presentation_rendered: false,
    presentation_failed: true,
    narrator_inference_trace: null,
    narrator_inference_session_id: null,
    narrator_evidence_id: 'ev-final-throw',
  });
  assert.equal(summary.phase_outcome, 'degraded');
  assert.equal(summary.inference_execution, 'attempted');
  assert.equal(summary.inference_trace, null);
  assert.equal(summary.inference_session_id, null);
  assert.equal(summary.evidence_id, 'ev-final-throw');
});

test('finalizeRoleInferenceSummary fills not_reached roles', () => {
  const finalized = finalizeRoleInferenceSummary(
    buildDirectorInferenceSummary({
      accepted: true,
      directorInferenceTrace: { provider: 'hg-mock', failed: false },
      directorInferenceSessionId: 'd-1',
    }),
    null,
    null,
  );
  assert.equal(finalized.director.phase_outcome, 'succeeded');
  assert.equal(finalized.character.phase_outcome, 'not_reached');
  assert.equal(finalized.narrator.phase_outcome, 'not_reached');
});

test('buildCharacterSummary marks uncommitted failure', () => {
  const summary = buildCharacterSummary({
    committed: false,
    characterInferenceTrace: { provider: 'hg-mock', failed: true },
    characterInferenceSessionId: 'c-1',
  });
  assert.equal(summary.phase_outcome, 'failed');
  assert.equal(summary.inference_execution, 'attempted');
});

test('notReachedRoleSummary defaults', () => {
  const summary = notReachedRoleSummary();
  assert.deepEqual(summary, {
    inference_execution: 'not_executed',
    phase_outcome: 'not_reached',
    inference_trace: null,
    inference_session_id: null,
    evidence_id: null,
  });
});

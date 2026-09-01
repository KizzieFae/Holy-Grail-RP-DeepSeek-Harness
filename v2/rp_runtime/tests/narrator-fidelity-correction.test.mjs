import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildCorrectionContextFromPresentationValidation,
  extractStructuredMoveFromManifest,
  isEligibleFidelityValidationFailure,
  requiredSpeechDialoguesFromStructuredMove,
} from '../src/lib/narrator-fidelity-correction.mjs';

test('requiredSpeechDialoguesFromStructuredMove extracts v2 speech beats', () => {
  const dialogues = requiredSpeechDialoguesFromStructuredMove({
    move_schema_version: 2,
    beats: [
      { type: 'action', action: 'nods' },
      { type: 'speech', dialogue: 'Keep your voice down, Bob.' },
    ],
  });
  assert.deepEqual(dialogues, ['Keep your voice down, Bob.']);
});

test('buildCorrectionContextFromPresentationValidation preserves authoritative fields', () => {
  const context = buildCorrectionContextFromPresentationValidation(
    {
      validation_class: 'speech_verbatim',
      reason: 'required speech beat 1 missing verbatim dialogue',
    },
    {
      attemptIndex: 0,
      narratorInferenceId: 'inf-narrator-1',
      domainCommitId: 'commit-abc',
      requiredSpeechDialogues: ['Keep your voice down, Bob.'],
    },
  );
  assert.equal(context.authority, 'presentation_fidelity_validation');
  assert.equal(context.validation_class, 'speech_verbatim');
  assert.deepEqual(context.required_speech_dialogues, ['Keep your voice down, Bob.']);
  assert.equal(context.evaluation_pass_id, 'inf-narrator-1-fidelity-0');
});

test('isEligibleFidelityValidationFailure accepts retryable F1/F2 classes only', () => {
  assert.equal(isEligibleFidelityValidationFailure('speech_verbatim', true), true);
  assert.equal(isEligibleFidelityValidationFailure('speech_order', true), true);
  assert.equal(isEligibleFidelityValidationFailure('structural', true), true);
  assert.equal(isEligibleFidelityValidationFailure('speech_verbatim', false), false);
  assert.equal(isEligibleFidelityValidationFailure('accepted', true), false);
});

test('extractStructuredMoveFromManifest reads committed_move contribution', () => {
  const move = extractStructuredMoveFromManifest({
    contributions: [{
      source_kind: 'committed_move',
      content: 'Committed character move for Alice:\n{"move_schema_version":2,"beats":[]}',
    }],
  });
  assert.equal(move.move_schema_version, 2);
});

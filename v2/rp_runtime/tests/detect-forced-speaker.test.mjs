import assert from 'node:assert/strict';
import test from 'node:test';

import { detectForcedSpeaker } from '../src/application/detect-forced-speaker.mjs';

test('detectForcedSpeaker: last mentioned cast member wins', () => {
  const result = detectForcedSpeaker('Alice, what do you think? Bob, your turn.', {
    participantNames: ['Alice', 'Bob'],
  });
  assert.equal(result, 'Bob');
});

test('detectForcedSpeaker: echoes previous speaker in two-cast scene', () => {
  const result = detectForcedSpeaker('What happens next?', {
    participantNames: ['Alice', 'Bob'],
    previousParticipantSpeaker: 'Alice',
  });
  assert.equal(result, 'Alice');
});

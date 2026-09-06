import assert from 'node:assert/strict';
import test from 'node:test';

import {
  LIVE_CHARACTER_PROMPT,
  LIVE_DIRECTOR_PROMPT,
  LIVE_INFERENCE_TRANSPORT_PROMPT,
} from '../src/lib/live-inference-prompts.mjs';

const DIRECTOR_FORBIDDEN = ['next_actor', 'end_round', 'tension_shift', 'environment_event'];
const CHARACTER_FORBIDDEN = ['move_schema_version', 'beats', 'risk_level'];

function assertTransportOnly(prompt, forbidden) {
  const lower = prompt.toLowerCase();
  assert.match(lower, /json object/);
  assert.ok(!lower.includes('manifest'));
  assert.ok(!lower.includes('inference_instruction'));
  for (const token of forbidden) {
    assert.ok(!lower.includes(token), `transport prompt must not include ${token}`);
  }
}

test('issue 136: shared transport prompt is canonical DSH envelope', () => {
  assert.equal(LIVE_DIRECTOR_PROMPT, LIVE_INFERENCE_TRANSPORT_PROMPT);
  assert.equal(LIVE_CHARACTER_PROMPT, LIVE_INFERENCE_TRANSPORT_PROMPT);
  assertTransportOnly(LIVE_DIRECTOR_PROMPT, DIRECTOR_FORBIDDEN);
  assertTransportOnly(LIVE_CHARACTER_PROMPT, CHARACTER_FORBIDDEN);
});

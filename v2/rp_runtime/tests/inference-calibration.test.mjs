import assert from 'node:assert/strict';
import test from 'node:test';

import {
  DIAGNOSTIC_TOKEN_CEILING,
  PRODUCTION_TOKEN_CEILINGS,
  ROLE_REASONING_DEFAULTS,
  buildInferenceOptions,
  resolveApplicationRoleProfiles,
} from '../src/application/application-settings.mjs';
import { mapReasoningEffortToProviderOptions } from '../src/lib/reasoning-provider-options.mjs';

test('calibration defaults: per-role reasoning and production ceilings (#29)', () => {
  assert.equal(ROLE_REASONING_DEFAULTS.director, 'low');
  assert.equal(ROLE_REASONING_DEFAULTS.character, 'low');
  assert.equal(ROLE_REASONING_DEFAULTS.narrator, 'low');
  assert.equal(ROLE_REASONING_DEFAULTS.semantic_evaluator, 'off');
  assert.equal(PRODUCTION_TOKEN_CEILINGS.narrator, 8192);
  assert.equal(PRODUCTION_TOKEN_CEILINGS.semantic_evaluator, 2048);
  assert.ok(PRODUCTION_TOKEN_CEILINGS.director >= 4096);
});

test('calibration mode: diagnostic token ceiling applies to all roles', () => {
  const prev = process.env.HG_INFERENCE_CALIBRATION;
  process.env.HG_INFERENCE_CALIBRATION = '1';
  try {
    const profiles = resolveApplicationRoleProfiles({ inferenceMode: 'live' });
    assert.equal(profiles.narrator.maxTokens, DIAGNOSTIC_TOKEN_CEILING);
    assert.equal(profiles.director.maxTokens, DIAGNOSTIC_TOKEN_CEILING);
  } finally {
    if (prev === undefined) delete process.env.HG_INFERENCE_CALIBRATION;
    else process.env.HG_INFERENCE_CALIBRATION = prev;
  }
});

test('reasoning scaffolding: off maps to disabled thinking at provider boundary', () => {
  const profiles = buildInferenceOptions({ inferenceMode: 'live' });
  const evaluator = profiles.roleProfiles.semantic_evaluator;
  const mapped = mapReasoningEffortToProviderOptions(evaluator.reasoningEffort);
  assert.equal(mapped.thinking, 'disabled');
});

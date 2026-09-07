import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildInferenceOptions,
  DIAGNOSTIC_TOKEN_CEILING,
  PRODUCTION_TOKEN_CEILINGS,
  referenceTokenCeilingForRole,
  resolveApplicationRoleProfiles,
  ROLE_REASONING_DEFAULTS,
} from '../src/application/application-settings.mjs';
import { mapReasoningEffortToProviderOptions } from '../src/lib/reasoning-provider-options.mjs';

test('calibration defaults: per-role reasoning and reference production ceilings (#29)', () => {
  assert.equal(ROLE_REASONING_DEFAULTS.director, 'low');
  assert.equal(ROLE_REASONING_DEFAULTS.character, 'low');
  assert.equal(ROLE_REASONING_DEFAULTS.narrator, 'low');
  assert.equal(ROLE_REASONING_DEFAULTS.semantic_evaluator, 'off');
  assert.equal(referenceTokenCeilingForRole('narrator'), PRODUCTION_TOKEN_CEILINGS.narrator);
  assert.equal(referenceTokenCeilingForRole('semantic_evaluator'), 2048);
  assert.ok(referenceTokenCeilingForRole('director') >= 4096);
});

test('calibration mode: flag remains available but does not enforce diagnostic ceiling while quotas disabled', () => {
  const prev = process.env.HG_INFERENCE_CALIBRATION;
  process.env.HG_INFERENCE_CALIBRATION = '1';
  try {
    const profiles = resolveApplicationRoleProfiles({ inferenceMode: 'live' });
    assert.equal(profiles.narrator.maxTokens, undefined);
    assert.equal(profiles.director.maxTokens, undefined);
    assert.equal(buildInferenceOptions({ inferenceMode: 'live' }).inferenceCalibration, true);
    assert.equal(DIAGNOSTIC_TOKEN_CEILING, 4096);
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

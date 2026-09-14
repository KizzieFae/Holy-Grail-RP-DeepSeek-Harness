import assert from 'node:assert/strict';
import test from 'node:test';

import { buildPlayerDecompositionUserPrompt } from '../src/plugins/hg-phase-executors/player-decomposition-phase.mjs';
import {
  DELIBERATION_PROFILE_CONSTRAINED,
  DELIBERATION_PROFILE_DEEP,
  modelProfileForDeliberationProfile,
  resolveEnvironmentCognitionDeliberationProfile,
} from '../src/lib/narrator-environment-deliberation-profile.mjs';

test('diagnostic retry exposes uncovered substantive spans', () => {
  const prompt = buildPlayerDecompositionUserPrompt('Alpha Beta.', {
    priorFailureCode: 'sir_substantive_omission',
    priorNormalizationAudit: {
      uncovered_substantive_spans: [{ char_start: 6, char_end: 10, text: 'Beta' }],
    },
  });
  assert.match(prompt, /source\[6:10\]="Beta"/);
  assert.match(prompt, /Uncovered substantive source not represented/);
});

test('constrained deliberation profile disables reasoning effort without token cap', () => {
  const base = { kind: 'dsh', provider: 'deepseek-official', model: 'deepseek-v4-flash', reasoningEffort: 'low' };
  const constrained = modelProfileForDeliberationProfile(base, DELIBERATION_PROFILE_CONSTRAINED);
  assert.equal(constrained.reasoningEffort, 'off');
  assert.equal(constrained.maxTokens, undefined);

  const deep = modelProfileForDeliberationProfile(base, DELIBERATION_PROFILE_DEEP);
  assert.equal(deep.reasoningEffort, 'low');
});

test('prepare response deliberation profile resolves structurally', () => {
  assert.equal(
    resolveEnvironmentCognitionDeliberationProfile({ deliberation_profile: { profile: 'constrained' } }),
    DELIBERATION_PROFILE_CONSTRAINED,
  );
  assert.equal(
    resolveEnvironmentCognitionDeliberationProfile({ deliberation_profile: { profile: 'deep' } }),
    DELIBERATION_PROFILE_DEEP,
  );
  assert.equal(resolveEnvironmentCognitionDeliberationProfile({}), DELIBERATION_PROFILE_DEEP);
});

import assert from 'node:assert/strict';
import test from 'node:test';

import { startDomainApi } from './helpers/domain-api.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { deepseekInferenceProfile } from '../src/lib/inference-profile.mjs';

const hasLiveKey = Boolean(process.env.DEEPSEEK_API_KEY?.trim());

test('live reasoning scaffolding: off disables provider thinking (#29)', {
  skip: hasLiveKey ? false : 'DEEPSEEK_API_KEY not set',
  timeout: 120_000,
}, async (t) => {
  const port = 32765 + Math.floor(Math.random() * 1000);
  const host = await startDomainApi(port);
  t.after(() => host.stop());

  const { phaseExecutors } = await createHolyGrailRpContext({
    domainApi: { baseUrl: host.baseUrl },
    inference: { mountDeepSeek: true },
  });

  // Non-manifest infrastructure probe (#140): no Host-prepared PromptContributionManifest.
  const manifest = { contributions: [] };

  const run = await phaseExecutors.runEphemeralInference({
    inferenceId: 'reasoning-off-live',
    prompt: 'Reply with exactly: OK',
    manifest,
    modelProfile: deepseekInferenceProfile({
      reasoningEffort: 'off',
      maxTokens: 64,
    }),
    evidenceContext: {
      role: 'semantic_evaluator',
      inferenceKind: 'infrastructure_provider_probe',
    },
  });

  const trace = run.trace;
  assert.equal(trace.reasoning_effort, 'off');
  assert.equal(trace.effective_thinking, 'disabled');
  assert.equal(trace.stream.reasoning_delta_count, 0);
  assert.equal(trace.reasoning_text.trim(), '');
  assert.ok(trace.assistant_text.includes('OK'));
});

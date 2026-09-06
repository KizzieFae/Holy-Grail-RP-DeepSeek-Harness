import assert from 'node:assert/strict';
import test from 'node:test';

import { createInferenceSubstrate } from '../src/plugins/hg-phase-executors/inference-substrate.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';

test('runEphemeralInference: invalid manifest rejects before agent allocation', async (t) => {
  const { ctx } = await createHolyGrailRpContext();
  t.after(async () => {
    await ctx.fiber.dispose();
  });

  let createCalls = 0;
  const originalCreate = ctx.agentLoop.create.bind(ctx.agentLoop);
  ctx.agentLoop.create = (...args) => {
    createCalls += 1;
    return originalCreate(...args);
  };

  const { runEphemeralInference } = createInferenceSubstrate({
    executionEvidence: { enabled: false },
  });

  const invalidManifest = {
    manifest_id: 'manifest-invalid-substrate',
    inference_id: 'inf-invalid-substrate',
    inference_kind: 'narrator_presentation',
    contributions: [
      {
        contribution_id: 'bad-env-cog',
        source_kind: 'narrator_environment_cognition',
        content: '{"forensic":"audit"}',
      },
    ],
  };

  await assert.rejects(
    () =>
      runEphemeralInference(ctx, {
        inferenceId: 'inf-invalid-substrate',
        prompt: 'ignored',
        manifest: invalidManifest,
        mockResponses: ['{}'],
        modelProfile: 'mock',
        evidenceContext: { inferenceKind: 'narrator_presentation' },
      }),
    /model-context package rejected/,
  );

  assert.equal(createCalls, 0, 'ephemeral agent must not be allocated for invalid manifest');
});

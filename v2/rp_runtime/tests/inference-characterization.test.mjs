import assert from 'node:assert/strict';
import test from 'node:test';

import {
  assertMutuallyExclusiveInferenceModes,
  buildInferenceOptions,
  isCharacterizationModeEnabled,
  modelProfileForInferenceKind,
  resolveApplicationRoleProfiles,
  stripApplicationMaxTokens,
  tokenCeilingForRole,
} from '../src/application/application-settings.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createInferenceSubstrate } from '../src/plugins/hg-phase-executors/inference-substrate.mjs';

test('characterization mode strips application maxTokens from role profiles', () => {
  const prev = process.env.HG_INFERENCE_CHARACTERIZATION;
  process.env.HG_INFERENCE_CHARACTERIZATION = '1';
  try {
    const profiles = resolveApplicationRoleProfiles({ inferenceMode: 'live' });
    assert.equal(profiles.narrator.maxTokens, undefined);
    assert.equal(profiles.director.reasoningEffort, 'low');
    assert.equal(tokenCeilingForRole('narrator', {}, {}), null);
  } finally {
    if (prev === undefined) delete process.env.HG_INFERENCE_CHARACTERIZATION;
    else process.env.HG_INFERENCE_CHARACTERIZATION = prev;
  }
});

test('characterization and calibration modes are mutually exclusive', () => {
  const prevChar = process.env.HG_INFERENCE_CHARACTERIZATION;
  const prevCal = process.env.HG_INFERENCE_CALIBRATION;
  process.env.HG_INFERENCE_CHARACTERIZATION = '1';
  process.env.HG_INFERENCE_CALIBRATION = '1';
  try {
    assert.throws(
      () => assertMutuallyExclusiveInferenceModes({}, {}),
      /cannot both be active/,
    );
  } finally {
    if (prevChar === undefined) delete process.env.HG_INFERENCE_CHARACTERIZATION;
    else process.env.HG_INFERENCE_CHARACTERIZATION = prevChar;
    if (prevCal === undefined) delete process.env.HG_INFERENCE_CALIBRATION;
    else process.env.HG_INFERENCE_CALIBRATION = prevCal;
  }
});

test('characterization preserves kind reasoning overrides', () => {
  const prev = process.env.HG_INFERENCE_CHARACTERIZATION;
  process.env.HG_INFERENCE_CHARACTERIZATION = '1';
  try {
    const opening = resolveApplicationRoleProfiles({ inferenceMode: 'live' }).opening;
    const profile = modelProfileForInferenceKind(opening, 'opening_segmentation', {}, {});
    assert.equal(profile.reasoningEffort, 'off');
    assert.equal(profile.maxTokens, undefined);
  } finally {
    if (prev === undefined) delete process.env.HG_INFERENCE_CHARACTERIZATION;
    else process.env.HG_INFERENCE_CHARACTERIZATION = prev;
  }
});

test('runEphemeralInference characterization: no maxTokens at agentLoop.create', async (t) => {
  const prev = process.env.HG_INFERENCE_CHARACTERIZATION;
  process.env.HG_INFERENCE_CHARACTERIZATION = '1';
  const { ctx } = await createHolyGrailRpContext();
  t.after(async () => {
    if (prev === undefined) delete process.env.HG_INFERENCE_CHARACTERIZATION;
    else process.env.HG_INFERENCE_CHARACTERIZATION = prev;
    await ctx.fiber.dispose();
  });

  let captured = null;
  const originalCreate = ctx.agentLoop.create.bind(ctx.agentLoop);
  ctx.agentLoop.create = (sessionId, options) => {
    captured = options;
    return originalCreate(sessionId, options);
  };

  const { runEphemeralInference } = createInferenceSubstrate({
    inferenceCharacterization: true,
    executionEvidence: { enabled: false },
  });

  await runEphemeralInference(ctx, {
    inferenceId: 'char-proof',
    prompt: 'Return {}',
    manifest: {
      manifest_id: 'm-char-proof',
      inference_id: 'char-proof',
      inference_kind: 'director_turn',
      contributions: [{
        contribution_id: 'i1',
        source_kind: 'inference_instruction',
        authority_class: 'instruction',
        priority: 1,
        content: 'Return JSON',
      }],
    },
    mockResponses: ['{"next_actor":"Ayame","environment_event":"","tension_shift":"steady","reason":"x","end_round":false}'],
    modelProfile: stripApplicationMaxTokens(
      buildInferenceOptions({ inferenceMode: 'live' }).roleProfiles.director,
    ),
    evidenceContext: { inferenceKind: 'director_turn', characterizationMode: true },
  });

  assert.ok(captured);
  assert.equal(captured.maxTokens, undefined);
});

test('buildInferenceOptions exposes characterization flag from env', () => {
  const prev = process.env.HG_INFERENCE_CHARACTERIZATION;
  process.env.HG_INFERENCE_CHARACTERIZATION = '1';
  try {
    assert.equal(isCharacterizationModeEnabled({}, {}), true);
    assert.equal(buildInferenceOptions({ inferenceMode: 'live' }).inferenceCharacterization, true);
  } finally {
    if (prev === undefined) delete process.env.HG_INFERENCE_CHARACTERIZATION;
    else process.env.HG_INFERENCE_CHARACTERIZATION = prev;
  }
});

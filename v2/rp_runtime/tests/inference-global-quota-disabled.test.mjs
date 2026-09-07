import assert from 'node:assert/strict';
import test from 'node:test';

import {
  APPLICATION_TOKEN_QUOTAS_ENFORCED,
  buildInferenceOptions,
  isApplicationTokenQuotaEnforced,
  modelProfileForInferenceKind,
  referenceTokenCeilingForInferenceKind,
  referenceTokenCeilingForRole,
  resolveApplicationRoleProfiles,
  stripApplicationMaxTokens,
  tokenCeilingForRole,
} from '../src/application/application-settings.mjs';
import {
  PRIMARY_RUNTIME_CATALOG,
  PRIMARY_RUNTIME_CALL_IDS,
} from '../src/application/llm-call-catalog.mjs';
import {
  resolveCatalogProductionProfile,
  resolveCatalogReferenceApplicationTokenQuota,
} from '../src/application/llm-call-catalog-policy.mjs';
import { createHolyGrailRpContext } from '../src/bootstrap.mjs';
import { createInferenceSubstrate } from '../src/plugins/hg-phase-executors/inference-substrate.mjs';

test('global quota policy: enforcement flag is disabled', () => {
  assert.equal(APPLICATION_TOKEN_QUOTAS_ENFORCED, false);
  assert.equal(isApplicationTokenQuotaEnforced(), false);
});

test('global quota policy: reference role ceilings remain available', () => {
  assert.equal(referenceTokenCeilingForRole('narrator'), 8192);
  assert.equal(referenceTokenCeilingForRole('semantic_evaluator'), 2048);
  assert.equal(referenceTokenCeilingForInferenceKind('player_visibility_triage'), 32);
});

test('global quota policy: runtime role profiles omit maxTokens', () => {
  const profiles = resolveApplicationRoleProfiles({ inferenceMode: 'live' });
  for (const role of Object.keys(profiles)) {
    assert.equal(profiles[role].maxTokens, undefined, `${role} must be uncapped`);
  }
  assert.equal(tokenCeilingForRole('narrator', {}, {}), null);
});

test('global quota policy: advanced role-profile maxTokens cannot bypass uncapping', () => {
  const profiles = resolveApplicationRoleProfiles({
    inferenceMode: 'live',
    roleRouting: 'advanced',
    roleProfiles: {
      director: { kind: 'dsh', provider: 'deepseek-official', model: 'x', maxTokens: 900 },
      character: { kind: 'dsh', provider: 'deepseek-official', model: 'y', maxTokens: 700 },
      narrator: { kind: 'dsh', provider: 'deepseek-official', model: 'z', maxTokens: 200 },
    },
  });
  assert.equal(profiles.director.maxTokens, undefined);
  assert.equal(profiles.character.maxTokens, undefined);
  assert.equal(profiles.narrator.maxTokens, undefined);
});

test('global quota policy: all 25 primary catalog identities resolve uncapped at runtime', () => {
  assert.equal(PRIMARY_RUNTIME_CALL_IDS.length, 25);
  for (const entry of PRIMARY_RUNTIME_CATALOG) {
    const profile = resolveCatalogProductionProfile(entry, { inferenceMode: 'live' }, {});
    assert.equal(profile.maxTokens, undefined, `${entry.call_id} must be uncapped`);
    const reference = resolveCatalogReferenceApplicationTokenQuota(entry, {}, {});
    assert.ok(
      reference === 'UNCAPPED' || Number.isFinite(reference),
      `${entry.call_id} reference quota unresolved`,
    );
  }
});

test('global quota policy: kind reasoning overrides preserved without maxTokens', () => {
  const opening = resolveApplicationRoleProfiles({ inferenceMode: 'live' }).opening;
  const profile = modelProfileForInferenceKind(opening, 'opening_segmentation', {}, {});
  assert.equal(profile.reasoningEffort, 'off');
  assert.equal(profile.maxTokens, undefined);
});

test('global quota policy: calibration flag does not reintroduce 4096 ceiling', () => {
  const prev = process.env.HG_INFERENCE_CALIBRATION;
  process.env.HG_INFERENCE_CALIBRATION = '1';
  try {
    const profiles = resolveApplicationRoleProfiles({ inferenceMode: 'live' });
    assert.equal(profiles.narrator.maxTokens, undefined);
    assert.equal(profiles.director.maxTokens, undefined);
    assert.equal(buildInferenceOptions({ inferenceMode: 'live' }).inferenceCalibration, true);
  } finally {
    if (prev === undefined) delete process.env.HG_INFERENCE_CALIBRATION;
    else process.env.HG_INFERENCE_CALIBRATION = prev;
  }
});

test('global quota policy: direct modelProfile maxTokens stripped at substrate boundary', async (t) => {
  const { ctx } = await createHolyGrailRpContext();
  t.after(async () => { await ctx.fiber.dispose(); });

  let captured = null;
  const originalCreate = ctx.agentLoop.create.bind(ctx.agentLoop);
  ctx.agentLoop.create = (sessionId, options) => {
    captured = options;
    return originalCreate(sessionId, options);
  };

  const { runEphemeralInference } = createInferenceSubstrate({
    executionEvidence: { enabled: false },
  });

  await runEphemeralInference(ctx, {
    inferenceId: 'direct-bypass-proof',
    prompt: 'Return {}',
    manifest: {
      manifest_id: 'm-direct-bypass',
      inference_id: 'direct-bypass-proof',
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
    modelProfile: {
      kind: 'mock',
      provider: 'hg-mock',
      model: 'deterministic-v2',
      maxTokens: 8192,
    },
    evidenceContext: { inferenceKind: 'director_turn' },
  });

  assert.ok(captured);
  assert.equal(captured.maxTokens, undefined);
});

test('global quota policy: ordinary runtime omits maxTokens at agentLoop.create', async (t) => {
  const { ctx } = await createHolyGrailRpContext();
  t.after(async () => { await ctx.fiber.dispose(); });

  let captured = null;
  const originalCreate = ctx.agentLoop.create.bind(ctx.agentLoop);
  ctx.agentLoop.create = (sessionId, options) => {
    captured = options;
    return originalCreate(sessionId, options);
  };

  const { runEphemeralInference } = createInferenceSubstrate({
    executionEvidence: { enabled: false },
  });

  await runEphemeralInference(ctx, {
    inferenceId: 'runtime-uncapped-proof',
    prompt: 'Return {}',
    manifest: {
      manifest_id: 'm-runtime-uncapped',
      inference_id: 'runtime-uncapped-proof',
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
    evidenceContext: { inferenceKind: 'director_turn', role: 'director' },
  });

  assert.ok(captured);
  assert.equal(captured.maxTokens, undefined);
});

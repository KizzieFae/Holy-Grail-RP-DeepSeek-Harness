import { performance } from 'node:perf_hooks';

import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import {
  isCharacterizationModeEnabled,
  stripApplicationMaxTokens,
} from '../../application/application-settings.mjs';
import { createExecutionEvidenceRecorder } from '../../lib/execution-evidence/recorder.mjs';
import {
  agentOptionsFromProfile,
  resolveInferenceProfile,
} from '../../lib/inference-profile.mjs';
import { extractInferenceTrace } from '../../lib/inference-trace.mjs';
import { waitForIdle } from '../../lib/inference-utils.mjs';
import { HgMockLlmAdapter } from '../../mock-llm-adapter.mjs';
import { validateBridgeManifest } from '../../lib/manifest-validation.mjs';

function resolveCharacterizationActive(inferenceConfig = {}) {
  return isCharacterizationModeEnabled(
    inferenceConfig.settings ?? {},
    {
      inferenceCharacterization: inferenceConfig.inferenceCharacterization,
      inferenceCalibration: inferenceConfig.inferenceCalibration,
    },
  );
}

function prepareProfileForInference(profile, characterizationActive) {
  if (!characterizationActive) return profile;
  const stripped = stripApplicationMaxTokens(profile);
  if (stripped?.maxTokens !== undefined || stripped?.max_tokens !== undefined) {
    throw new Error(
      'characterization mode: Holy-Grail maxTokens must not reach inference substrate',
    );
  }
  return stripped;
}

/**
 * Shared ephemeral inference substrate for all RP phase executors.
 */
export function createInferenceSubstrate(inferenceConfig = {}) {
  const recorder = createExecutionEvidenceRecorder({
    enabled: inferenceConfig.executionEvidence?.enabled,
    root: inferenceConfig.executionEvidence?.root,
    systemPersona: inferenceConfig.systemPersona ?? 'Holy Grail RP runtime.',
  });

  async function runEphemeralInference(ctx, {
    inferenceId,
    prompt,
    manifest,
    mockResponses,
    modelProfile,
    evidenceContext = null,
  }) {
    const characterizationActive = resolveCharacterizationActive(inferenceConfig);
    const resolvedProfile = prepareProfileForInference(
      resolveInferenceProfile(inferenceConfig, modelProfile),
      characterizationActive,
    );
    const agentOpts = agentOptionsFromProfile(resolvedProfile);
    if (characterizationActive && agentOpts.maxTokens !== undefined) {
      throw new Error(
        'characterization mode: agent options must not include Holy-Grail maxTokens',
      );
    }
    const resolvedEvidenceContext = {
      ...(evidenceContext ?? {}),
      characterizationMode: characterizationActive,
      inferenceKind: evidenceContext?.inferenceKind
        ?? manifest?.inference_kind
        ?? null,
    };
    validateBridgeManifest({
      manifest,
      inferenceKind: resolvedEvidenceContext.inferenceKind ?? null,
    });
    let disposeAdapter = () => {};
    let disposeRequestHook = () => {};

    if (resolvedProfile.kind === 'mock') {
      const adapter = new HgMockLlmAdapter(
        mockResponses.length ? mockResponses : ['{}'],
      );
      disposeAdapter = ctx.llm.registerAdapter([resolvedProfile.provider], adapter);
    }

    const agentCreateOptions = {
      provider: agentOpts.provider,
      model: agentOpts.model,
    };
    if (agentOpts.maxTokens !== undefined) {
      agentCreateOptions.maxTokens = agentOpts.maxTokens;
    }

    const agent = ctx.agentLoop.create(
      SessionId(`hg-inf-${inferenceId}`),
      agentCreateOptions,
    );
    if (agentOpts.reasoningEffort !== undefined) {
      disposeRequestHook = agent.ctx.on('agent/request', async (_payload, next) => {
        const resolved = await next();
        return {
          ...resolved,
          reasoningEffort: agentOpts.reasoningEffort,
        };
      });
    }
    const contextRegistration = ctx.hgContextBridge.registerManifest({
      agent,
      manifest,
      inferenceKind: resolvedEvidenceContext.inferenceKind ?? null,
    });
    agent.followup(
      createUserMessage({
        content: [{ type: 'text', text: prompt }],
        source: { kind: 'user' },
      }),
    );
    const inferenceStartedAt = performance.now();
    await waitForIdle(ctx, agent);
    const inferenceWallClockMs = performance.now() - inferenceStartedAt;

    const trace = extractInferenceTrace(agent.session.events, {
      provider: resolvedProfile.provider,
      model: resolvedProfile.model,
      reasoningEffort: resolvedProfile.reasoningEffort ?? null,
      manifestId: contextRegistration.manifestId,
      contributionIds: contextRegistration.contributionIds,
    });
    const raw = trace.assistant_text;
    const evidenceId = recorder.recordInferenceAttempt({
      evidenceContext: resolvedEvidenceContext,
      manifest,
      contextRegistration,
      prompt,
      profile: resolvedProfile,
      trace,
      assistantText: raw,
      inferenceSessionId: String(agent.id),
      inferenceWallClockMs,
    });
    contextRegistration.dispose();
    disposeRequestHook();
    disposeAdapter();

    return {
      raw,
      inferenceSessionId: String(agent.id),
      trace,
      failed: trace.failed,
      failure: trace.failure,
      inferenceSessionEvents: [...agent.session.events],
      evidenceId,
      inferenceWallClockMs,
      characterizationMode: characterizationActive,
    };
  }

  return { runEphemeralInference, recorder };
}

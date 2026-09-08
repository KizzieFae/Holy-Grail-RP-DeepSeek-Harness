import { performance } from 'node:perf_hooks';

import { createUserMessage } from '@deepseek-ai/dsh-llm';
import { SessionId } from '@deepseek-ai/dsh-session';

import {
  isApplicationTokenQuotaEnforced,
  isCharacterizationModeEnabled,
  stripApplicationMaxTokens,
} from '../../application/application-settings.mjs';
import { createExecutionEvidenceRecorder } from '../../lib/execution-evidence/recorder.mjs';
import {
  agentOptionsFromProfile,
  resolveInferenceProfile,
} from '../../lib/inference-profile.mjs';
import { extractInferenceTrace } from '../../lib/inference-trace.mjs';
import {
  extractTurnBoundaryTiming,
  idleBoundaryDiagnostic,
  waitForTurnEnd,
  waitForTurnStart,
} from '../../lib/inference-turn-timing.mjs';
import { HgMockLlmAdapter } from '../../mock-llm-adapter.mjs';
import { waitForIdle } from '../../lib/inference-utils.mjs';
import { validateBridgeManifest } from '../../lib/manifest-validation.mjs';

const MOCK_RUNTIME_KEY = Symbol.for('hg.mockInferenceRuntime');
const MOCK_GATE_KEY = Symbol.for('hg.mockInferenceGate');

function fiberStore(ctx) {
  return ctx?.fiber?._store ?? ctx?.fiber?.store ?? null;
}

function createAsyncGate() {
  let tail = Promise.resolve();
  return async (fn) => {
    let release = () => {};
    const prev = tail;
    tail = prev.then(() => new Promise((resolve) => {
      release = resolve;
    }));
    await prev;
    try {
      return await fn();
    } finally {
      release();
    }
  };
}

function mockInferenceGate(ctx) {
  const store = fiberStore(ctx);
  if (!store) {
    return createAsyncGate();
  }
  if (!store[MOCK_GATE_KEY]) {
    store[MOCK_GATE_KEY] = createAsyncGate();
  }
  return store[MOCK_GATE_KEY];
}

function prepareMockAdapter(ctx, provider, mockResponses) {
  const store = fiberStore(ctx);
  if (!store) {
    throw new Error('mock inference requires Cordis fiber store');
  }
  let runtime = store[MOCK_RUNTIME_KEY];
  if (!runtime?.initialized) {
    const adapter = new HgMockLlmAdapter(['{}']);
    const dispose = ctx.llm.registerAdapter([provider], adapter);
    runtime = { adapter, dispose, initialized: true };
    store[MOCK_RUNTIME_KEY] = runtime;
  }
  runtime.adapter.responses = mockResponses.length ? [...mockResponses] : ['{}'];
  runtime.adapter.callIndex = 0;
}

function resolveCharacterizationActive(inferenceConfig = {}) {
  return isCharacterizationModeEnabled(
    inferenceConfig.settings ?? {},
    {
      inferenceCharacterization: inferenceConfig.inferenceCharacterization,
      inferenceCalibration: inferenceConfig.inferenceCalibration,
    },
  );
}

function prepareProfileForInference(profile) {
  const stripped = stripApplicationMaxTokens(profile);
  if (stripped?.maxTokens !== undefined || stripped?.max_tokens !== undefined) {
    throw new Error(
      'Holy-Grail maxTokens must not reach inference substrate while application quotas are disabled',
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
    );
    const agentOpts = agentOptionsFromProfile(resolvedProfile);
    if (agentOpts.maxTokens !== undefined) {
      throw new Error(
        'agent options must not include Holy-Grail maxTokens while application quotas are disabled',
      );
    }
    const resolvedEvidenceContext = {
      ...(evidenceContext ?? {}),
      characterizationMode: characterizationActive,
      calibrationMode: inferenceConfig.inferenceCalibration === true,
      applicationTokenQuotasEnforced: isApplicationTokenQuotaEnforced(),
      inferenceKind: evidenceContext?.inferenceKind
        ?? manifest?.inference_kind
        ?? null,
    };
    validateBridgeManifest({
      manifest,
      inferenceKind: resolvedEvidenceContext.inferenceKind ?? null,
    });

    const executeInference = async () => {
      let disposeRequestHook = () => {};
      let contextRegistration = null;
      let agent = null;
      let expectedTurn = null;
      let idleBoundaryMs = null;

      try {
        if (resolvedProfile.kind === 'mock') {
          prepareMockAdapter(ctx, resolvedProfile.provider, mockResponses);
        }

        const agentCreateOptions = {
          provider: agentOpts.provider,
          model: agentOpts.model,
        };
        if (agentOpts.maxTokens !== undefined) {
          agentCreateOptions.maxTokens = agentOpts.maxTokens;
        }

        agent = ctx.agentLoop.create(
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
        contextRegistration = ctx.hgContextBridge.registerManifest({
          agent,
          manifest,
          inferenceKind: resolvedEvidenceContext.inferenceKind ?? null,
        });
        const eventsBeforeFollowup = agent.session.events.length;
        agent.followup(
          createUserMessage({
            content: [{ type: 'text', text: prompt }],
            source: { kind: 'user' },
          }),
        );
        const idleStartedAt = performance.now();
        expectedTurn = await waitForTurnStart(agent, { afterEventCount: eventsBeforeFollowup });
        await waitForTurnEnd(agent, expectedTurn);
        await waitForIdle(ctx, agent);
        idleBoundaryMs = performance.now() - idleStartedAt;

        const trace = extractInferenceTrace(agent.session.events, {
          provider: resolvedProfile.provider,
          model: resolvedProfile.model,
          reasoningEffort: resolvedProfile.reasoningEffort ?? null,
          manifestId: contextRegistration.manifestId,
          contributionIds: contextRegistration.contributionIds,
        });
        const raw = trace.assistant_text;
        const turnBoundaryTiming = extractTurnBoundaryTiming(
          agent.session.events,
          expectedTurn,
          String(agent.id),
        );
        const evidenceId = recorder.recordInferenceAttempt({
          evidenceContext: resolvedEvidenceContext,
          manifest,
          contextRegistration,
          prompt,
          profile: resolvedProfile,
          trace,
          assistantText: raw,
          inferenceSessionId: String(agent.id),
          turnBoundaryTiming,
          idleBoundaryDiagnostic: idleBoundaryDiagnostic(idleBoundaryMs),
        });

        return {
          raw,
          inferenceSessionId: String(agent.id),
          trace,
          failed: trace.failed,
          failure: trace.failure,
          inferenceSessionEvents: [...agent.session.events],
          evidenceId,
          inferenceWallClockMs: turnBoundaryTiming?.timing_observed === true
            ? turnBoundaryTiming.inference_wall_clock_ms
            : null,
          turnBoundaryTiming,
          characterizationMode: characterizationActive,
          applicationTokenQuotasEnforced: isApplicationTokenQuotaEnforced(),
        };
      } finally {
        contextRegistration?.dispose?.();
        disposeRequestHook();
      }
    };

    if (resolvedProfile.kind === 'mock') {
      return mockInferenceGate(ctx)(executeInference);
    }
    return executeInference();
  }

  return { runEphemeralInference, recorder };
}

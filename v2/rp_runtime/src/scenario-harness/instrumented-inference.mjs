import {
  agentOptionsFromProfile,
  resolveInferenceProfile,
} from '../lib/inference-profile.mjs';
import { boundText } from './production-capture.mjs';

function isLiveInference(params, runtimeConfig) {
  const profile = resolveInferenceProfile(runtimeConfig, params.modelProfile);
  const hasMock = Array.isArray(params.mockResponses) && params.mockResponses.length > 0;
  return profile.kind === 'dsh' && !hasMock;
}

function resolvedProfileRecord(params, runtimeConfig) {
  const profile = resolveInferenceProfile(runtimeConfig, params.modelProfile);
  const agentOpts = agentOptionsFromProfile(profile);
  return {
    kind: profile.kind,
    provider: agentOpts.provider,
    model: agentOpts.model,
    reasoning_effort: agentOpts.reasoningEffort ?? profile.reasoningEffort ?? null,
    max_tokens: agentOpts.maxTokens ?? profile.maxTokens ?? null,
  };
}

/**
 * Wrap production runEphemeralInference with campaign accounting and timing.
 */
export function createInstrumentedInference({
  phaseExecutors,
  campaignLimits,
  runtimeConfig = {},
  onInference = null,
  rawStore = null,
} = {}) {
  const calls = [];

  async function runEphemeralInference(params) {
    campaignLimits?.assertCanInfer?.();
    const started = performance.now();
    const result = await phaseExecutors.runEphemeralInference(params);
    const durationMs = Math.round(performance.now() - started);
    const live = isLiveInference(params, runtimeConfig);
    if (live) {
      campaignLimits?.recordInference?.();
    }
    const entry = {
      inference_id: params.inferenceId,
      inference_kind: params.evidenceContext?.inferenceKind ?? null,
      live,
      controlled: !live,
      duration_ms: durationMs,
      evidence_id: result.evidenceId ?? null,
      failed: result.failed === true,
      profile: resolvedProfileRecord(params, runtimeConfig),
      usage: result.trace?.usage ?? null,
      provider: result.trace?.provider ?? null,
      model: result.trace?.model ?? null,
    };
    calls.push(entry);
    if (rawStore) {
      rawStore.push({
        inference_id: params.inferenceId,
        inference_kind: entry.inference_kind,
        evidence_id: entry.evidence_id,
        raw: boundText(result.raw),
        failed: result.failed === true,
      });
    }
    onInference?.(entry);
    return result;
  }

  return {
    runEphemeralInference,
    calls,
    summarize() {
      const liveCalls = calls.filter((c) => c.live);
      const byKind = {};
      for (const call of liveCalls) {
        const kind = call.inference_kind ?? 'unknown';
        byKind[kind] = (byKind[kind] ?? 0) + 1;
      }
      return {
        total_calls: calls.length,
        live_calls: liveCalls.length,
        controlled_calls: calls.filter((c) => c.controlled).length,
        by_kind: byKind,
        calls,
      };
    },
  };
}

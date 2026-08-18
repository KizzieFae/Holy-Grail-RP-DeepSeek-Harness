import { HG_MOCK_MODEL, HG_MOCK_PROVIDER } from '../mock-llm-adapter.mjs';

/** DSH provider route registered by @deepseek-ai/dsh-llm-deepseek. */
export const HG_DEEPSEEK_PROVIDER = 'deepseek-official';

/** Default production model aligned with V1 Holy Grail policy. */
export const HG_DEEPSEEK_DEFAULT_MODEL = 'deepseek-v4-flash';

/**
 * Transport-neutral inference profile. Role orchestration passes a profile;
 * provider implementation stays in DSH adapters.
 *
 * @typedef {object} MockInferenceProfile
 * @property {'mock'} kind
 * @property {string} provider
 * @property {string} model
 *
 * @typedef {object} DshInferenceProfile
 * @property {'dsh'} kind
 * @property {string} provider
 * @property {string} model
 * @property {string} [reasoningEffort] adapter-owned effort id (off|low|high|max)
 * @property {number} [temperature]
 * @property {number} [maxTokens]
 *
 * @typedef {MockInferenceProfile | DshInferenceProfile} InferenceProfile
 */

/** Deterministic test-only profile (not production architecture). */
export function mockInferenceProfile() {
  return {
    kind: 'mock',
    provider: HG_MOCK_PROVIDER,
    model: HG_MOCK_MODEL,
  };
}

/** Default real DeepSeek profile for integration validation. */
export function deepseekInferenceProfile(overrides = {}) {
  return {
    kind: 'dsh',
    provider: HG_DEEPSEEK_PROVIDER,
    model: HG_DEEPSEEK_DEFAULT_MODEL,
    reasoningEffort: 'low',
    ...overrides,
  };
}

/**
 * Resolve the effective profile for one inference call.
 * Explicit per-call profile wins, then runtime default, then mock.
 */
export function resolveInferenceProfile(runtimeConfig, callProfile) {
  if (callProfile) return callProfile;
  if (runtimeConfig?.defaultProfile) return runtimeConfig.defaultProfile;
  return mockInferenceProfile();
}

/** Agent options derived from a profile (provider semantics only). */
export function agentOptionsFromProfile(profile) {
  const options = {
    provider: profile.provider,
    model: profile.model,
  };
  if (profile.reasoningEffort) {
    options.reasoningEffort = profile.reasoningEffort;
  }
  if (profile.temperature !== undefined) {
    options.temperature = profile.temperature;
  }
  if (profile.maxTokens !== undefined) {
    options.maxTokens = profile.maxTokens;
  }
  return options;
}

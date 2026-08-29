import { HG_MOCK_MODEL, HG_MOCK_PROVIDER } from '../mock-llm-adapter.mjs';
import { mapReasoningEffortToProviderOptions } from './reasoning-provider-options.mjs';

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
  if (profile.kind === 'dsh' || profile.reasoningEffort !== undefined) {
    const mapped = mapReasoningEffortToProviderOptions(profile.reasoningEffort ?? 'low');
    options.reasoningEffort = mapped.reasoningEffort;
    options.thinking = mapped.thinking;
  }
  if (profile.temperature !== undefined) {
    options.temperature = profile.temperature;
  }
  if (profile.maxTokens !== undefined) {
    options.maxTokens = profile.maxTokens;
  }
  return options;
}

/**
 * Resolve per-role inference profiles from runtime options.
 * Each role may later use a different model; all may share one profile in this slice.
 */
export function resolveRoleProfiles(options = {}, runtimeConfig = {}) {
  const grouped = options.roleProfiles ?? options.role_profiles ?? {};
  const shared = options.modelProfile
    ?? options.model_profile
    ?? grouped.default
    ?? runtimeConfig?.defaultProfile
    ?? null;

  const fallback = shared ?? mockInferenceProfile();

  return {
    director: grouped.director ?? grouped.directorProfile ?? options.directorProfile ?? fallback,
    character: grouped.character ?? grouped.characterProfile ?? options.characterProfile ?? fallback,
    narrator: grouped.narrator ?? grouped.narratorProfile ?? options.narratorProfile ?? fallback,
    semantic_evaluator:
      grouped.semantic_evaluator
      ?? grouped.semanticEvaluator
      ?? options.semanticEvaluatorProfile
      ?? grouped.semantic_evaluator_profile
      ?? fallback,
    plot_cognition_epistemic_evaluator:
      grouped.plot_cognition_epistemic_evaluator
      ?? grouped.plotCognitionEpistemicEvaluator
      ?? options.plotCognitionEpistemicEvaluatorProfile
      ?? grouped.semantic_evaluator
      ?? grouped.semanticEvaluator
      ?? fallback,
    character_advisory_generator:
      grouped.character_advisory_generator
      ?? grouped.characterAdvisoryGenerator
      ?? options.characterAdvisoryGeneratorProfile
      ?? grouped.storyteller
      ?? grouped.storytellerProfile
      ?? fallback,
    storyteller:
      grouped.storyteller
      ?? grouped.storytellerProfile
      ?? options.storytellerProfile
      ?? fallback,
  };
}

/** Attempt budget when mock responses are not supplied. */
export function inferenceAttemptLimit(mockResponses, liveMaxAttempts = 3) {
  return mockResponses.length > 0 ? mockResponses.length : liveMaxAttempts;
}

/** Whether any role profile targets the real DSH provider. */
export function usesLiveProvider(roleProfiles) {
  return Object.values(roleProfiles).some((profile) => profile?.kind === 'dsh');
}

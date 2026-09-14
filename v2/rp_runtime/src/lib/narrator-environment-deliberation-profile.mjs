/** Structural deliberation profile transport for narrator environmental cognition (#194). */

export const DELIBERATION_PROFILE_DEEP = 'deep';
export const DELIBERATION_PROFILE_CONSTRAINED = 'constrained';

const DEEP_CATEGORIES = new Set(['C', 'cannot_safely_resolve']);

/** Post-mediation outcomes indicating reconciliation complexity (not pre-mediation placeholders). */
const DEEP_MEDIATION_OUTCOMES = new Set([
  'match',
  'ambiguous',
  'forbidden',
  'retrieval_failure',
  'mediation_failure',
]);

/**
 * @param {object|null|undefined} prepareResponse
 * @returns {string}
 */
export function resolveEnvironmentCognitionDeliberationProfile(prepareResponse) {
  const profile = prepareResponse?.deliberation_profile?.profile;
  if (profile === DELIBERATION_PROFILE_CONSTRAINED) {
    return DELIBERATION_PROFILE_CONSTRAINED;
  }
  return DELIBERATION_PROFILE_DEEP;
}

/**
 * Post-cognition structural guard (mirrors domain_api narrator_environment_deliberation_profile).
 *
 * @param {object|null|undefined} cognitionResult
 * @returns {string}
 */
export function classifyCognitionResultDeliberationProfile(cognitionResult) {
  if (!cognitionResult || typeof cognitionResult !== 'object') {
    return DELIBERATION_PROFILE_DEEP;
  }
  const needs = Array.isArray(cognitionResult.information_needs)
    ? cognitionResult.information_needs
    : [];
  const resolutions = Array.isArray(cognitionResult.resolutions)
    ? cognitionResult.resolutions
    : [];
  if (needs.length > 1) {
    return DELIBERATION_PROFILE_DEEP;
  }
  const categories = new Set(
    resolutions
      .filter((item) => item && typeof item === 'object')
      .map((item) => String(item.category ?? '').trim())
      .filter(Boolean),
  );
  for (const category of categories) {
    if (DEEP_CATEGORIES.has(category)) {
      return DELIBERATION_PROFILE_DEEP;
    }
  }
  if (resolutions.some((item) => (
    item
    && typeof item === 'object'
    && DEEP_MEDIATION_OUTCOMES.has(String(item.mediation_outcome ?? '').trim())
  ))) {
    return DELIBERATION_PROFILE_DEEP;
  }
  if (needs.length === 1 && categories.size > 0 && [...categories].every((c) => c === 'B2')) {
    return DELIBERATION_PROFILE_CONSTRAINED;
  }
  return DELIBERATION_PROFILE_DEEP;
}

/**
 * @param {string} initialProfile
 * @param {object|null|undefined} cognitionResult
 * @returns {boolean}
 */
export function shouldEscalateConstrainedCognitionToDeep(initialProfile, cognitionResult) {
  if (initialProfile !== DELIBERATION_PROFILE_CONSTRAINED) {
    return false;
  }
  return classifyCognitionResultDeliberationProfile(cognitionResult) === DELIBERATION_PROFILE_DEEP;
}

/**
 * @param {object|null|undefined} baseProfile
 * @param {string} deliberationProfile
 * @returns {object|null|undefined}
 */
export function modelProfileForDeliberationProfile(baseProfile, deliberationProfile) {
  if (!baseProfile || deliberationProfile !== DELIBERATION_PROFILE_CONSTRAINED) {
    return baseProfile;
  }
  return {
    ...baseProfile,
    reasoningEffort: 'off',
  };
}

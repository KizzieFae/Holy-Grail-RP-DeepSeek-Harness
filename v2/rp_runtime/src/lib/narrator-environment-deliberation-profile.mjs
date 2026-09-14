/** Structural deliberation profile transport for narrator environmental cognition (#194). */

export const DELIBERATION_PROFILE_DEEP = 'deep';
export const DELIBERATION_PROFILE_CONSTRAINED = 'constrained';

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

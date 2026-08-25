/** Stubs Domain API Character cognition endpoints for unit/orchestration tests (#38). */

export function attachCharacterCognitionApiStubs(api) {
  if (typeof api.prepareCharacterOrientationContext === 'function') {
    return api;
  }
  return {
    ...api,
    async prepareCharacterOrientationContext(body) {
      return {
        manifest_id: `manifest-char-orient-${body.inference_id}`,
        contributions: [],
        upstream_fingerprint: 'test-upstream-fp',
      };
    },
    async finalizeCharacterOrientation() {
      return { accepted: false, reason: 'test_skip_cognition' };
    },
  };
}

/** Character move inference evidence (excludes orientation substrate calls). */
export function findCharacterMoveAttempt(attempts) {
  return attempts.find((entry) => (
    entry.correlation?.role === 'character'
    && (entry.decision?.outcome != null || entry.decision?.parse != null)
  ));
}

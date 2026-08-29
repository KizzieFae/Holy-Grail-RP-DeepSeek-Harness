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
    async preparePlotCognitionProjection() {
      return {
        accepted: true,
        batch_id: 'batch-test-stub',
        candidate_count: 0,
        batch: { batch_id: 'batch-test-stub', binding_digest: 'binding-stub' },
        evaluator_manifests: {},
        items: [],
      };
    },
    async registerPlotCognitionProjectionSemanticResult() {
      return { accepted: true, reason: 'registered' };
    },
    async preparePlotCognitionProjectionRegeneration() {
      return { accepted: false, reason: 'test_stub' };
    },
    async finalizePlotCognitionProjectionRegeneration() {
      return { accepted: false, reason: 'test_stub' };
    },
    async finalizePlotCognitionProjection() {
      return {
        accepted: true,
        batch_id: 'batch-test-stub',
        binding: {
          batch_id: 'batch-test-stub',
          binding_digest: 'binding-stub',
          character_id: 'Alice',
          hg_round_id: 'round-test',
          turn_index: 0,
        },
        contributions: [],
      };
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

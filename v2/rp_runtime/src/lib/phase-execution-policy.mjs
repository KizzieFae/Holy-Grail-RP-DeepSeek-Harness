/**
 * Shared DSH phase execution-policy primitives (#102).
 *
 * Owns only cross-phase numeric policy duplicated across executors.
 * Does NOT own phase-specific retry loops, budget state machines,
 * Narrator/opening/decomposition attempt policy, or inferenceAttemptLimit().
 */

/** Inclusive infra retries when semantic QA/evaluation substrate fails (2 tries total). */
export const SEMANTIC_EVAL_INFRA_RETRIES = 1;

/** Effective Character/Director live candidate ceiling (see clampLiveCandidateLimit). */
export const LIVE_CANDIDATE_CEILING = 3;

/**
 * Clamp liveMaxAttempts to the shared candidate ceiling with floor 1.
 * liveMaxAttempts is an upper-bound input; values above LIVE_CANDIDATE_CEILING
 * do not increase Character/Director candidate budgets.
 */
export function clampLiveCandidateLimit(liveMaxAttempts = LIVE_CANDIDATE_CEILING) {
  const configured = Number(liveMaxAttempts ?? LIVE_CANDIDATE_CEILING);
  if (!Number.isFinite(configured) || configured < 1) {
    return 1;
  }
  return Math.min(configured, LIVE_CANDIDATE_CEILING);
}

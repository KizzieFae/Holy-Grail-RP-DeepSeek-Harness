/**
 * Configuration owner for Narrator environment-cognition Librarian mediation parallelism (#165).
 * Authoritative default aligns with StorytellerOrchestrationPolicy.max_parallel_epistemic_evals (=4).
 */

export const DEFAULT_MAX_PARALLEL_NARRATOR_MEDIATION_INFERENCES = 4;

/**
 * @param {object} [inferenceConfig]
 * @returns {number}
 */
export function resolveMaxParallelNarratorMediationInferences(inferenceConfig = {}) {
  const narratorMediation = inferenceConfig.narratorMediation ?? {};
  const raw = narratorMediation.maxParallelInferences
    ?? inferenceConfig.maxParallelNarratorMediationInferences;
  if (raw === undefined || raw === null) {
    return DEFAULT_MAX_PARALLEL_NARRATOR_MEDIATION_INFERENCES;
  }
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed < 1) {
    throw new Error(
      'maxParallelNarratorMediationInferences must be a positive integer',
    );
  }
  return Math.floor(parsed);
}

/**
 * @param {number} needCount
 * @param {number} maxParallel
 * @returns {number}
 */
export function effectiveNarratorMediationParallelism(needCount, maxParallel) {
  if (needCount <= 1) {
    return 1;
  }
  return Math.min(needCount, maxParallel);
}

/**
 * @param {number} needCount
 * @param {number} maxParallel
 * @returns {'serial' | 'parallel'}
 */
export function narratorMediationExecutionMode(needCount, maxParallel) {
  if (needCount <= 1 || maxParallel <= 1) {
    return 'serial';
  }
  return 'parallel';
}

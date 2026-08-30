/** Structured forensic attribution for Narrator phase and #49 env cognition (#70). */

export const ENV_COGNITION_STAGES = {
  PREPARE: 'environment_cognition_prepare',
  INFERENCE: 'cognition_inference',
  KAR_BUILD: 'knowledge_request_build',
  LIBRARIAN_MEDIATION: 'librarian_mediation',
  FINALIZE: 'environment_cognition_finalize',
};

export const FORENSIC_BOUNDARIES = {
  DOMAIN_API: 'domain_api',
  INFERENCE_PROVIDER: 'inference_provider',
  INTERNAL: 'internal',
};

export const NARRATOR_FAILURE_CLASSES = {
  CONTEXT_PREPARE: 'context_prepare',
  INFERENCE_BOUNDARY_THROW: 'inference_boundary_throw',
  INFERENCE_RETURNED_FAILURE: 'inference_returned_failure',
  VALIDATION: 'validation',
  SEMANTIC_QA: 'semantic_qa',
  PRESENTATION_DEGRADATION: 'presentation_degradation',
};

export class NarratorEnvironmentCognitionError extends Error {
  /**
   * @param {object} params
   * @param {string} params.stage
   * @param {string} params.boundary
   * @param {unknown} params.cause
   */
  constructor({ stage, boundary, cause }) {
    const reason = String(cause?.message ?? cause ?? 'environment_cognition_failed');
    super(reason);
    this.name = 'NarratorEnvironmentCognitionError';
    this.stage = stage;
    this.boundary = boundary;
    this.cause = cause;
  }
}

/**
 * @param {unknown} error
 * @param {string} [defaultBoundary]
 */
export function classifyFailureBoundary(error, defaultBoundary = FORENSIC_BOUNDARIES.INTERNAL) {
  if (error?.name === 'DomainApiTransportError' || error?.failureClass === 'transport_error') {
    return FORENSIC_BOUNDARIES.DOMAIN_API;
  }
  if (error?.failureClass === 'host_internal_error' || error?.errorKind === 'host_internal_error') {
    return FORENSIC_BOUNDARIES.DOMAIN_API;
  }
  const message = String(error?.message ?? error ?? '');
  if (/^Domain API .+ failed \(\d+\)/.test(message)) {
    return FORENSIC_BOUNDARIES.DOMAIN_API;
  }
  if (defaultBoundary) {
    return defaultBoundary;
  }
  return FORENSIC_BOUNDARIES.INTERNAL;
}

/**
 * @param {unknown} error
 */
export function extractEnvironmentCognitionFailure(error) {
  if (error instanceof NarratorEnvironmentCognitionError) {
    return {
      stage: error.stage,
      boundary: error.boundary,
      reason: String(error.cause?.message ?? error.message),
    };
  }
  if (error?.name === 'DomainApiTransportError') {
    const code = error.transportCode ? `${error.transportCode}: ` : '';
    return {
      stage: 'substrate_exception',
      boundary: FORENSIC_BOUNDARIES.DOMAIN_API,
      reason: `${code}${error.message}`,
    };
  }
  if (error?.failureClass === 'host_internal_error') {
    return {
      stage: 'substrate_exception',
      boundary: FORENSIC_BOUNDARIES.DOMAIN_API,
      reason: 'host_internal_error',
    };
  }
  return {
    stage: 'substrate_exception',
    boundary: classifyFailureBoundary(error, FORENSIC_BOUNDARIES.INTERNAL),
    reason: String(error?.message ?? error),
  };
}

/**
 * @param {string} stage
 * @param {string} boundary
 * @param {() => Promise<unknown>} fn
 */
export async function runEnvironmentCognitionStage(stage, boundary, fn) {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof NarratorEnvironmentCognitionError) {
      throw error;
    }
    throw new NarratorEnvironmentCognitionError({
      stage,
      boundary: classifyFailureBoundary(error, boundary),
      cause: error,
    });
  }
}

/**
 * @param {object} params
 */
export function buildForensicAttribution({
  failureClass,
  boundary,
  stage,
  failureReason = null,
}) {
  return {
    failure_class: failureClass,
    boundary,
    stage,
    failure_reason: failureReason,
  };
}

/**
 * Ephemeral round-result projection for per-role inference execution vs phase outcome (#94).
 * Durable execution evidence remains authoritative for full forensic chains.
 */

/**
 * @returns {import('./role-inference-summary.mjs').RoleInferenceSummary}
 */
export function notReachedRoleSummary() {
  return {
    inference_execution: 'not_executed',
    phase_outcome: 'not_reached',
    inference_trace: null,
    inference_session_id: null,
    evidence_id: null,
  };
}

/**
 * @param {object|null|undefined} trace
 * @returns {'not_executed'|'attempted'|'completed'}
 */
export function classifyInferenceExecution(trace) {
  if (!trace) return 'not_executed';
  if (trace.failed) return 'attempted';
  return 'completed';
}

/**
 * @param {object} params
 * @returns {RoleInferenceSummary}
 */
export function buildInferenceSummary({
  inference_execution,
  phase_outcome,
  inference_trace = null,
  inference_session_id = null,
  evidence_id = null,
}) {
  const hasTrace = inference_trace != null;
  const hasSession = Boolean(inference_session_id);
  let execution = inference_execution;
  if (execution == null) {
    if (hasTrace || hasSession) {
      execution = classifyInferenceExecution(inference_trace);
    } else {
      execution = 'not_executed';
    }
  }
  return {
    inference_execution: execution,
    phase_outcome,
    inference_trace: hasTrace ? inference_trace : null,
    inference_session_id: hasSession ? inference_session_id : null,
    evidence_id: evidence_id ?? null,
  };
}

/** @returns {RoleInferenceSummary} */
export function buildDirectorBypassSummary() {
  return buildInferenceSummary({
    inference_execution: 'not_executed',
    phase_outcome: 'bypassed',
  });
}

/**
 * @param {object} directorPhase
 * @returns {RoleInferenceSummary}
 */
export function buildDirectorInferenceSummary(directorPhase) {
  const trace = directorPhase.directorInferenceTrace ?? null;
  const sessionId = directorPhase.directorInferenceSessionId ?? null;
  return buildInferenceSummary({
    inference_execution: classifyInferenceExecution(trace),
    phase_outcome: directorPhase.accepted ? 'succeeded' : 'failed',
    inference_trace: trace,
    inference_session_id: sessionId,
    evidence_id: directorPhase.directorEvidenceId ?? null,
  });
}

/**
 * @param {object} characterTurn
 * @returns {RoleInferenceSummary}
 */
export function buildCharacterSummary(characterTurn) {
  const trace = characterTurn.characterInferenceTrace ?? null;
  return buildInferenceSummary({
    inference_execution: classifyInferenceExecution(trace),
    phase_outcome: characterTurn.committed ? 'succeeded' : 'failed',
    inference_trace: trace,
    inference_session_id: characterTurn.characterInferenceSessionId ?? null,
    evidence_id: characterTurn.committedCharacterEvidenceId ?? null,
  });
}

/**
 * @param {object} narratorResult
 * @returns {RoleInferenceSummary}
 */
export function buildNarratorSummary(narratorResult) {
  const trace = narratorResult.narrator_inference_trace ?? null;
  const sessionId = narratorResult.narrator_inference_session_id ?? null;
  const evidenceId = narratorResult.narrator_evidence_id ?? null;
  const inferenceRan = Boolean(trace || sessionId || evidenceId);

  let phase_outcome = 'failed';
  if (narratorResult.presentation_rendered) {
    phase_outcome = 'succeeded';
  } else if (narratorResult.presentation_failed) {
    phase_outcome = 'degraded';
  }

  let inference_execution = 'not_executed';
  if (inferenceRan) {
    inference_execution = trace
      ? classifyInferenceExecution(trace)
      : 'attempted';
  }

  return buildInferenceSummary({
    inference_execution,
    phase_outcome,
    inference_trace: trace,
    inference_session_id: sessionId,
    evidence_id: evidenceId,
  });
}

/**
 * @typedef {object} RoleInferenceSummary
 * @property {'not_executed'|'attempted'|'completed'} inference_execution
 * @property {'not_reached'|'bypassed'|'succeeded'|'degraded'|'failed'} phase_outcome
 * @property {object|null} inference_trace
 * @property {string|null} inference_session_id
 * @property {string|null} evidence_id
 */

/**
 * @param {object|null} directorSummary
 * @param {object|null} characterSummary
 * @param {object|null} narratorSummary
 * @returns {{ director: RoleInferenceSummary, character: RoleInferenceSummary, narrator: RoleInferenceSummary }}
 */
export function finalizeRoleInferenceSummary(directorSummary, characterSummary, narratorSummary) {
  return {
    director: directorSummary ?? notReachedRoleSummary(),
    character: characterSummary ?? notReachedRoleSummary(),
    narrator: narratorSummary ?? notReachedRoleSummary(),
  };
}

/**
 * Deterministic Character structural correction context (#201).
 *
 * Enriches validation-driven retry guidance for v2 move-schema parse failures.
 * Repair-only: preserves narrative intent; does not relax ingress validation.
 */

/** @typedef {{ validation_class?: string, reason?: string, retryable?: boolean, accepted?: boolean }} StructuralValidation */

const STRUCTURAL_REPAIR_INSTRUCTION = (
  'Preserve your intended Character move, but serialize it in the required v2 JSON structure. '
  + 'Do not change narrative intent, story facts, Player stimulus, or evaluator expectations. '
  + 'Output replacement RP as JSON only.'
);

const REQUIRED_MOVE_SCHEMA_VERSION = {
  move_schema_version: 2,
};

const ACTION_BEAT_EXEMPLAR = {
  type: 'action',
  action: '...',
};

const SPEECH_BEAT_EXEMPLAR = {
  type: 'speech',
  dialogue: '...',
};

/**
 * @param {string} reason
 * @returns {string[]}
 */
export function classifyStructuralFailureClasses(reason) {
  const normalized = String(reason ?? '');
  const classes = [];
  if (
    normalized.includes('move_schema_version is required')
    || normalized.includes('move_schema_version must be')
    || normalized.includes('Unsupported move_schema_version')
  ) {
    classes.push('missing_or_invalid_move_schema_version');
  }
  if (normalized.includes('invalid beat type')) {
    classes.push('missing_or_invalid_beat_type');
  }
  return classes;
}

/**
 * @param {StructuralValidation | null | undefined} validation
 */
export function isEligibleStructuralValidationFailure(validation) {
  if (!validation || validation.accepted) return false;
  if (!validation.retryable) return false;
  if (String(validation.validation_class ?? '') !== 'parse_error') return false;
  return classifyStructuralFailureClasses(validation.reason).length > 0;
}

/**
 * @param {string[]} failureClasses
 */
export function buildStructuralRepairGuidance(failureClasses) {
  const lines = [STRUCTURAL_REPAIR_INSTRUCTION];
  if (failureClasses.includes('missing_or_invalid_move_schema_version')) {
    lines.push(
      'Required top-level field: include move_schema_version as integer 2.',
      `Canonical fragment: ${JSON.stringify(REQUIRED_MOVE_SCHEMA_VERSION)}`,
    );
  }
  if (failureClasses.includes('missing_or_invalid_beat_type')) {
    lines.push(
      'Every beat in beats[] requires a valid type field: action or speech.',
      `Action beat example: ${JSON.stringify(ACTION_BEAT_EXEMPLAR)}`,
      `Speech beat example: ${JSON.stringify(SPEECH_BEAT_EXEMPLAR)}`,
    );
  }
  return lines.join('\n');
}

/**
 * @param {StructuralValidation} validation
 * @param {object} [params]
 * @param {number} [params.attemptIndex]
 * @param {string} [params.characterInferenceId]
 */
export function buildCorrectionContextFromStructuralValidation(validation, {
  attemptIndex = null,
  characterInferenceId = null,
} = {}) {
  const failureClasses = classifyStructuralFailureClasses(validation.reason);
  const context = {
    source: 'objective_validation',
    validation_class: validation.validation_class,
    reason: validation.reason,
    structural_failure_classes: failureClasses,
    structural_repair_instruction: STRUCTURAL_REPAIR_INSTRUCTION,
    structural_repair_guidance: buildStructuralRepairGuidance(failureClasses),
  };
  if (failureClasses.includes('missing_or_invalid_move_schema_version')) {
    context.required_move_schema_version = REQUIRED_MOVE_SCHEMA_VERSION;
  }
  if (failureClasses.includes('missing_or_invalid_beat_type')) {
    context.required_beat_structure_examples = {
      action: ACTION_BEAT_EXEMPLAR,
      speech: SPEECH_BEAT_EXEMPLAR,
    };
  }
  if (attemptIndex != null) {
    context.attempt_index = attemptIndex;
  }
  if (characterInferenceId && attemptIndex != null) {
    context.evaluation_pass_id = `${characterInferenceId}-structural-${attemptIndex}`;
  }
  return context;
}

/**
 * @param {StructuralValidation} validation
 * @param {object} [params]
 * @param {number} [params.attemptIndex]
 * @param {string} [params.characterInferenceId]
 */
export function enrichObjectiveValidationCorrectionContext(validation, params = {}) {
  if (isEligibleStructuralValidationFailure(validation)) {
    return buildCorrectionContextFromStructuralValidation(validation, params);
  }
  return {
    source: 'objective_validation',
    validation_class: validation.validation_class,
    reason: validation.reason,
  };
}

/**
 * Deterministic Narrator F1/F2 fidelity correction context (#93).
 */

const ELIGIBLE_FIDELITY_VALIDATION_CLASSES = new Set([
  'speech_verbatim',
  'speech_order',
  'structural',
]);

/**
 * @param {object | null | undefined} manifest
 * @returns {object | null}
 */
export function extractStructuredMoveFromManifest(manifest) {
  const contributions = manifest?.contributions ?? [];
  for (const contribution of contributions) {
    if (contribution?.source_kind !== 'committed_move') continue;
    const content = String(contribution.content ?? '');
    const jsonStart = content.indexOf('{');
    if (jsonStart < 0) continue;
    try {
      const parsed = JSON.parse(content.slice(jsonStart));
      if (parsed && typeof parsed === 'object') return parsed;
    } catch {
      // try next contribution
    }
  }
  return null;
}

/**
 * @param {object | null | undefined} structuredMove
 * @returns {string[]}
 */
export function requiredSpeechDialoguesFromStructuredMove(structuredMove) {
  if (!structuredMove || typeof structuredMove !== 'object') return [];
  if (structuredMove.move_schema_version !== 2) return [];
  const beats = structuredMove.beats;
  if (!Array.isArray(beats)) return [];
  const dialogues = [];
  for (const beat of beats) {
    if (!beat || beat.type !== 'speech') continue;
    const dialogue = String(beat.dialogue ?? '').trim();
    if (dialogue) dialogues.push(dialogue);
  }
  return dialogues;
}

/**
 * @param {string | null | undefined} validationClass
 * @param {boolean} [retryable]
 */
export function isEligibleFidelityValidationFailure(validationClass, retryable = true) {
  return Boolean(retryable)
    && ELIGIBLE_FIDELITY_VALIDATION_CLASSES.has(String(validationClass ?? ''));
}

/**
 * @param {object} validation
 * @param {object} params
 * @param {number} params.attemptIndex
 * @param {string} params.narratorInferenceId
 * @param {string} params.domainCommitId
 * @param {string[]} params.requiredSpeechDialogues
 */
export function buildCorrectionContextFromPresentationValidation(validation, {
  attemptIndex,
  narratorInferenceId,
  domainCommitId,
  requiredSpeechDialogues,
}) {
  return {
    source: 'presentation_fidelity_validation',
    authority: 'presentation_fidelity_validation',
    validation_class: validation.validation_class,
    reason: validation.reason ?? '',
    required_speech_dialogues: [...(requiredSpeechDialogues ?? [])],
    attempt_index: attemptIndex,
    evaluation_pass_id: `${narratorInferenceId}-fidelity-${attemptIndex}`,
    domain_commit_id: domainCommitId,
  };
}

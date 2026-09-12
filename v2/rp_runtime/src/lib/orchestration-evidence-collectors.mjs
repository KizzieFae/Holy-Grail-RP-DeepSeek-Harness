/**
 * Collect inference evidence ids for orchestration span linkage (#173).
 * Observability-only; does not alter inference behavior.
 */

function pushUnique(target, value) {
  if (!value) return;
  const id = String(value);
  if (!target.includes(id)) target.push(id);
}

/**
 * @param {object|null|undefined} storytellerResult
 * @returns {string[]}
 */
export function collectStorytellerEvidenceIds(storytellerResult) {
  const ids = [];
  if (!storytellerResult) return ids;
  pushUnique(ids, storytellerResult.orientationRun?.evidenceId);
  pushUnique(ids, storytellerResult.mediation?.mediationEvidenceId);
  pushUnique(ids, storytellerResult.assessmentRun?.evidenceId);
  pushUnique(ids, storytellerResult.audit?.assessment_evidence_id);
  return ids;
}

/**
 * @param {object|null|undefined} resumeSummary
 * @returns {string[]}
 */
export function collectPlotCognitionResumeEvidenceIds(resumeSummary) {
  const ids = [];
  if (!resumeSummary) return ids;
  const updateResult = resumeSummary.updateResult ?? null;
  pushUnique(ids, updateResult?.inferenceEvidenceId);
  pushUnique(ids, updateResult?.inferRun?.evidenceId);
  for (const run of updateResult?.inferRuns ?? []) {
    pushUnique(ids, run?.evidenceId);
  }
  return ids;
}

/**
 * @param {object|null|undefined} directorPhase
 * @returns {string[]}
 */
export function collectDirectorEvidenceIds(directorPhase) {
  if (!directorPhase) return [];
  if (Array.isArray(directorPhase.orchestrationEvidenceIds)) {
    return [...new Set(directorPhase.orchestrationEvidenceIds.filter(Boolean))];
  }
  const ids = [];
  pushUnique(ids, directorPhase.directorEvidenceId);
  return ids;
}

/**
 * @param {object|null|undefined} characterTurn
 * @returns {string[]}
 */
export function collectCharacterPrepEvidenceIds(characterTurn) {
  if (!characterTurn) return [];
  if (Array.isArray(characterTurn.orchestrationEvidenceIds)) {
    return [...new Set(characterTurn.orchestrationEvidenceIds.filter(Boolean))];
  }
  const ids = [];
  pushUnique(ids, characterTurn.committedCharacterEvidenceId);
  return ids;
}

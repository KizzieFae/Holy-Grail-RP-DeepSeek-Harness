export const SEMANTIC_RUBRIC_VERSION = 'hg_storyteller_semantic_rubric_v1';

export function createSemanticCharacterization({
  fixtureId,
  repetitionIndex = 0,
  dimensions = {},
  categoricalFindings = [],
  governanceFlags = [],
  evaluatorEvidenceId = null,
  evaluatorRaw = null,
  notes = [],
} = {}) {
  return {
    rubric_version: SEMANTIC_RUBRIC_VERSION,
    fixture_id: fixtureId,
    repetition_index: repetitionIndex,
    dimensions,
    categorical_findings: categoricalFindings,
    governance_flags: governanceFlags,
    evaluator_evidence_id: evaluatorEvidenceId,
    evaluator_raw: evaluatorRaw,
    notes,
  };
}

/**
 * Semantic characterization must never mutate objective_status.
 */
export function attachSemanticCharacterization(scenarioResult, semanticCharacterization) {
  return {
    ...scenarioResult,
    semantic_characterization: semanticCharacterization,
    objective_status: scenarioResult.objective_status,
    objective_pass: scenarioResult.objective_pass,
    certification_class: scenarioResult.certification_class ?? 'live_semantic',
  };
}

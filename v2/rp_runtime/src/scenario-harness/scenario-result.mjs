import crypto from 'node:crypto';

export const SCENARIO_RESULT_SCHEMA = 'hg_storyteller_tier1_scenario_result_v1';

/**
 * Structured objective certification result for a Tier-1 scenario run.
 * Semantic-quality fields are reserved for Phase C; not populated in Phase B.
 */
export function createScenarioResult(scenarioId, {
  runId = `tier1-run-${crypto.randomUUID()}`,
  fixtureId = null,
  objectivePass = false,
  objectiveGates = {},
  operationSequence = [],
  authorityCommits = [],
  overlayRevisions = [],
  inferenceCounts = {},
  regenerationCount = 0,
  consumerContributions = {},
  withheld = [],
  evidenceIds = [],
  chronicleKeys = [],
  integrityGaps = [],
  phaseDurationsMs = {},
  notes = [],
  semanticCharacterization = null,
} = {}) {
  return {
    schema: SCENARIO_RESULT_SCHEMA,
    scenario_id: scenarioId,
    run_id: runId,
    fixture_id: fixtureId,
    objective_pass: objectivePass,
    objective_gates: objectiveGates,
    operation_sequence: operationSequence,
    authority_commits: authorityCommits,
    overlay_revisions: overlayRevisions,
    inference_counts: inferenceCounts,
    regeneration_count: regenerationCount,
    consumer_contributions: consumerContributions,
    withheld,
    evidence_ids: evidenceIds,
    chronicle_keys: chronicleKeys,
    integrity_gaps: integrityGaps,
    phase_durations_ms: phaseDurationsMs,
    notes,
    semantic_characterization: semanticCharacterization,
    certification_class: 'objective_deterministic',
  };
}

export function finalizeScenarioResult(result) {
  const gates = Object.values(result.objective_gates ?? {});
  const pass = gates.length > 0 && gates.every((gate) => gate.pass === true);
  return { ...result, objective_pass: pass && result.integrity_gaps.length === 0 };
}

export function gate(name, pass, detail = null) {
  return { name, pass: Boolean(pass), detail };
}

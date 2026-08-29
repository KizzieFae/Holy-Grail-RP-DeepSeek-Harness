import crypto from 'node:crypto';

export const SCENARIO_RESULT_SCHEMA = 'hg_storyteller_tier1_scenario_result_v1';

export const OBJECTIVE_STATUS = {
  CERTIFIED: 'certified',
  BLOCKED: 'blocked',
  NOT_PROVEN: 'not_proven',
};

/**
 * Structured objective certification result for a Tier-1 scenario run.
 * Semantic-quality fields are reserved for Phase C; not populated in Phase B.
 */
export function createScenarioResult(scenarioId, {
  runId = `tier1-run-${crypto.randomUUID()}`,
  fixtureId = null,
  objectivePass = false,
  objectiveStatus = OBJECTIVE_STATUS.NOT_PROVEN,
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
  durableEvidence = null,
} = {}) {
  return {
    schema: SCENARIO_RESULT_SCHEMA,
    scenario_id: scenarioId,
    run_id: runId,
    fixture_id: fixtureId,
    objective_pass: objectivePass,
    objective_status: objectiveStatus,
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
    durable_evidence: durableEvidence,
    certification_class: 'objective_deterministic',
  };
}

export function finalizeScenarioResult(result, { blocked = false } = {}) {
  const gates = Object.values(result.objective_gates ?? {});
  const gatesPass = gates.length > 0 && gates.every((entry) => entry.pass === true);
  const integrityOk = (result.integrity_gaps ?? []).length === 0;
  let objectiveStatus = OBJECTIVE_STATUS.NOT_PROVEN;
  if (blocked) {
    objectiveStatus = OBJECTIVE_STATUS.BLOCKED;
  } else if (gatesPass && integrityOk) {
    objectiveStatus = OBJECTIVE_STATUS.CERTIFIED;
  }
  return {
    ...result,
    objective_status: objectiveStatus,
    objective_pass: objectiveStatus === OBJECTIVE_STATUS.CERTIFIED,
  };
}

export function gate(name, pass, detail = null) {
  return { name, pass: Boolean(pass), detail };
}

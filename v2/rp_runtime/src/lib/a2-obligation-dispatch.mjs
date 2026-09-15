/**
 * Issue #201 G3 — harness-local deterministic obligation dispatch (no LLM router).
 */

export const OBLIGATION_SIGNALS = [
  'actor_multiplicity',
  'entitlement_divergence',
  'retrieval_obligation',
  'environmental_obligation',
  'plot_obligation',
  'state_mutation_risk',
  'repair_requirement',
];

/**
 * @param {object} input
 * @param {string} input.scenarioKey
 * @param {string[]} [input.eligibleActors]
 * @param {Record<string, string>} [input.roleAssignments]
 * @param {boolean} [input.uniformProjectionEligible]
 * @param {boolean} [input.retrievalManifestGap]
 */
export function deriveObligationSignals({
  scenarioKey,
  eligibleActors = [],
  roleAssignments = {},
  uniformProjectionEligible = false,
  retrievalManifestGap = false,
}) {
  const signals = [];
  const authorizations = [];
  const notAuthorized = [];

  if (eligibleActors.length > 1) {
    signals.push({
      signal: 'actor_multiplicity',
      source: 'eligible_actors.length',
      deterministic: true,
      value: eligibleActors.length,
    });
    authorizations.push('multi_character_path');
    authorizations.push('isolated_actor_packages');
  }

  const roleSet = new Set(
    eligibleActors.map((actor) => roleAssignments[actor]).filter(Boolean),
  );
  if (roleSet.size > 1) {
    signals.push({
      signal: 'entitlement_divergence',
      source: 'distinct_roles_among_eligible_actors',
      deterministic: true,
      value: [...roleSet],
    });
    authorizations.push('per_actor_character_cognition');
  }

  if (retrievalManifestGap) {
    signals.push({
      signal: 'retrieval_obligation',
      source: 'context_manifest_gap',
      deterministic: true,
      value: true,
    });
    authorizations.push('indexed_retrieval');
  }

  if (scenarioKey === 'arkham_stress') {
    signals.push({
      signal: 'environmental_obligation',
      source: 'scenario_key_dispatch',
      deterministic: true,
      value: 'logged_only_g3a',
    });
  }

  if (!uniformProjectionEligible) {
    signals.push({
      signal: 'state_mutation_risk',
      source: 'non_uniform_player_path',
      deterministic: true,
      value: true,
    });
    authorizations.push('player_decomposition');
  }

  notAuthorized.push(
    'storyteller_preamble',
    'director_semantic_qa',
    'narrator_semantic_qa',
    'default_environment_cognition',
    'character_orientation_llm',
    'default_librarian_mediation',
    'synchronous_plot',
    'character_semantic_evaluation_f1',
    'llm_obligation_router',
  );

  return {
    schema: 'issue201_g3_obligation_dispatch_v1',
    scenario_key: scenarioKey,
    signals,
    authorizations,
    not_authorized: notAuthorized,
    beat_class: scenarioKey === 'ayame_controlled' ? 'simple' : 'complex',
  };
}

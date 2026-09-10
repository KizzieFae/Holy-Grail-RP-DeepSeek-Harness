/**
 * Current-runtime LLM call metadata registry (#152).
 * Quota/reasoning values are derived at generation time from application-settings.mjs.
 */

/** @typedef {'runtime_primary' | 'harness_annex'} CatalogScope */

/**
 * @typedef {object} LlmCallCatalogEntry
 * @property {string} call_id
 * @property {CatalogScope} catalog_scope
 * @property {string} canonical_inference_kind
 * @property {string[]} evidence_aliases
 * @property {string} role_agent
 * @property {string} subsystem
 * @property {string} purpose
 * @property {string} owner_module
 * @property {string} owner_export
 * @property {string} invocation_condition
 * @property {'role_profile' | 'kind_override' | 'parent_role' | 'uncapped'} profile_source
 * @property {string|null} profile_role
 * @property {string|null} kind_override
 * @property {string|null} parent_role
 * @property {string|null} current_exception_note
 */

/** @type {readonly LlmCallCatalogEntry[]} */
export const PRIMARY_RUNTIME_CATALOG = Object.freeze([
  entry('director_turn', 'director_turn', ['director_decision'], 'director', 'round/director', 'Select next actor and orchestration decision', 'plugins/hg-phase-executors/director-phase.mjs', 'runDirectorPhase', 'Every round after participation resolution', 'role_profile', 'director'),
  entry('director_semantic_qa', 'director_semantic_qa', [], 'semantic_evaluator', 'round/director-qa', 'Bounded semantic QA on director candidate', 'plugins/hg-phase-executors/director-semantic-qa.mjs', 'runDirectorSemanticEvaluation', 'After director candidate generation when QA enabled', 'role_profile', 'semantic_evaluator'),
  entry('character_turn', 'character_turn', ['character_move'], 'character', 'round/character', 'Generate structured character move', 'plugins/hg-phase-executors/character-phase.mjs', 'runCharacterPhase', 'Selected actor character turn', 'role_profile', 'character'),
  entry('character_semantic_evaluation', 'character_semantic_evaluation', [], 'semantic_evaluator', 'round/character-qa', 'Post-move semantic evaluation', 'plugins/hg-phase-executors/character-semantic-evaluation.mjs', 'runSemanticEvaluation', 'After character move commit path when eval runs', 'role_profile', 'semantic_evaluator'),
  entry('character_orientation', 'character_orientation', [], 'character', 'character/cognition', 'Pre-move orientation cognition', 'lib/character-cognition-substrate.mjs', 'runCharacterKnowledgeCognition', 'Before character move when cognition enabled', 'role_profile', 'character'),
  entry('librarian_mediation@character', 'librarian_mediation', [], 'character', 'librarian/mediation', 'Librarian contextual mediation from character parent profile', 'lib/librarian-mediation-substrate.mjs', 'runLibrarianMediation', 'When mediation requested from character cognition path', 'parent_role', null, null, 'character'),
  entry('librarian_mediation@narrator', 'librarian_mediation', [], 'narrator', 'librarian/mediation', 'Librarian contextual mediation from narrator/storyteller parent profile', 'lib/librarian-mediation-substrate.mjs', 'runLibrarianMediation', 'When mediation requested from narrator env cognition or storyteller paths', 'parent_role', null, null, 'narrator'),
  entry('storyteller_post_commit_issue_pressure', 'storyteller_post_commit_issue_pressure', [], 'storyteller', 'semantic/post-commit', 'Narrow Storyteller post-commit issue-pressure assessment (#164)', 'lib/librarian-proposal-substrate.mjs', 'runLibrarianProposalGeneration', 'After character commit when ACTIVE/ESCALATING issues exist (0–1 per commit)', 'role_profile', 'storyteller'),
  entry('storyteller_post_commit_issue_pressure_contract_correction', 'storyteller_post_commit_issue_pressure_contract_correction', [], 'storyteller', 'semantic/post-commit', 'Contract correction for post-commit issue-pressure assessment', 'lib/contract-correction-substrate.mjs', 'runInferenceWithContractCorrection', 'Primary post-commit issue-pressure structural parse failure (max 1)', 'kind_override', 'storyteller', 'storyteller_post_commit_issue_pressure_contract_correction'),
  entry('narrator_presentation', 'narrator_presentation', [], 'narrator', 'round/narrator', 'Render narrator presentation prose', 'plugins/hg-phase-executors/narrator-phase.mjs', 'runNarratorPhase', 'End of round narrator phase', 'role_profile', 'narrator'),
  entry('narrator_environment_cognition', 'narrator_environment_cognition', [], 'narrator', 'narrator/env-cognition', 'Structured environment cognition for material obligations', 'lib/narrator-environment-cognition-substrate.mjs', 'runNarratorEnvironmentCognition', 'When environment cognition obligation path is active', 'role_profile', 'narrator'),
  entry('narrator_semantic_qa', 'narrator_semantic_qa', [], 'semantic_evaluator', 'round/narrator-qa', 'Bounded semantic QA on narrator presentation', 'plugins/hg-phase-executors/narrator-semantic-qa.mjs', 'runNarratorSemanticEvaluation', 'After narrator presentation when QA enabled', 'role_profile', 'semantic_evaluator'),
  entry('opening', 'opening', [], 'opening', 'session/opening', 'Generate scene opening prose', 'plugins/hg-phase-executors/opening-phase.mjs', 'runOpeningPhase', 'Scene bootstrap when opening generation requested', 'role_profile', 'opening'),
  entry('opening_segmentation', 'opening_segmentation', [], 'opening', 'session/opening', 'Segment long opener for validation', 'plugins/hg-phase-executors/opening-segmentation-phase.mjs', 'runOpeningSegmentationPhase', 'Long template opener segmentation path', 'kind_override', 'opening', 'opening_segmentation', null, 'Thinking disabled (#110); 4096 kind ceiling'),
  entry('player_visibility_triage', 'player_visibility_triage', [], 'player_visibility_triage', 'player-turn/pvr', 'Route uniform vs full player decomposition', 'plugins/hg-phase-executors/player-visibility-triage-phase.mjs', 'runPlayerVisibilityTriagePhase', 'Every player turn submit', 'kind_override', 'character', 'player_visibility_triage', null, '32-token kind ceiling (#121); reasoning off'),
  entry('player_decomposition', 'player_decomposition', [], 'character', 'player-turn/pvr', 'Semantic player turn decomposition', 'plugins/hg-phase-executors/player-decomposition-phase.mjs', 'runPlayerDecompositionPhase', 'Non-uniform player visibility path', 'uncapped', 'character', 'player_decomposition', null, 'Application UNCAPPED since #124'),
  entry('storyteller_orientation', 'storyteller_orientation', [], 'storyteller', 'storyteller/cognition', 'Storyteller orientation cognition', 'lib/storyteller-cognition-substrate.mjs', 'runStorytellerCognition', 'Round-start storyteller cognition hook', 'role_profile', 'storyteller'),
  entry('storyteller_assessment', 'storyteller_assessment', [], 'storyteller', 'storyteller/cognition', 'Storyteller assessment after librarian bundle', 'lib/storyteller-cognition-substrate.mjs', 'runStorytellerCognition', 'Paired with storyteller orientation in cognition lifecycle', 'role_profile', 'storyteller'),
  entry('plot_cognition_init', 'plot_cognition_init', [], 'storyteller', 'plot/cognition', 'Initialize plot cognition pending work', 'lib/plot-cognition-orchestration.mjs', 'runPlotCognitionPendingWorkLifecycle', 'When plot cognition init work is pending', 'role_profile', 'storyteller'),
  entry('plot_cognition_init_contract_correction', 'plot_cognition_init_contract_correction', [], 'storyteller', 'plot/cognition', 'Contract correction for plot cognition init', 'lib/contract-correction-substrate.mjs', 'runInferenceWithContractCorrection', 'Plot init structural parse failure (max 1)', 'role_profile', 'storyteller'),
  entry('plot_cognition_update', 'plot_cognition_update', [], 'storyteller', 'plot/cognition', 'Plot cognition update generation', 'lib/plot-cognition-update-substrate.mjs', 'runPlotCognitionUpdateGeneration', 'Plot resume/update lifecycle', 'kind_override', 'storyteller', 'plot_cognition_update', null, '8192 kind headroom (#111)'),
  entry('plot_cognition_update_contract_correction', 'plot_cognition_update_contract_correction', [], 'storyteller', 'plot/cognition', 'Contract correction for plot cognition update', 'lib/contract-correction-substrate.mjs', 'runInferenceWithContractCorrection', 'Plot update structural parse failure (max 1)', 'kind_override', 'storyteller', 'plot_cognition_update_contract_correction'),
  entry('plot_cognition_epistemic_eval', 'plot_cognition_epistemic_eval', [], 'semantic_evaluator', 'plot/projection', 'Epistemic evaluation for character advisory projection', 'plugins/hg-phase-executors/plot-cognition-character-projection.mjs', 'runEpistemicEval', 'When plot character projection epistemic eval runs', 'role_profile', 'semantic_evaluator'),
  entry('plot_cognition_epistemic_eval_contract_correction', 'plot_cognition_epistemic_eval_contract_correction', [], 'semantic_evaluator', 'plot/projection', 'Contract correction for epistemic eval', 'lib/contract-correction-substrate.mjs', 'runInferenceWithContractCorrection', 'Epistemic eval structural parse failure (max 1)', 'role_profile', 'semantic_evaluator'),
  entry('character_advisory_generation', 'character_advisory_generation', [], 'semantic_evaluator', 'plot/projection', 'Regenerate character advisory content', 'plugins/hg-phase-executors/plot-cognition-character-projection.mjs', 'runRegenerationGeneration', 'When advisory regeneration generation runs', 'role_profile', 'semantic_evaluator'),
]);

/** @type {readonly LlmCallCatalogEntry[]} */
export const HARNESS_ANNEX_CATALOG = Object.freeze([
  annex('storyteller_certification_eval', 'storyteller_certification_eval', 'harness/certification', 'Scenario harness certification evaluator', 'scenario-harness/certification-evaluator.mjs', 'evaluateStorytellerCertification'),
  annex('infrastructure_provider_probe', 'infrastructure_provider_probe', 'test/probe', 'Infrastructure provider probe (tests only)', 'tests/manifest-validation.test.mjs', 'infrastructure probe tests'),
]);

/**
 * @param {string} callId
 * @param {string} kind
 * @param {string[]} aliases
 * @param {string} role
 * @param {string} subsystem
 * @param {string} purpose
 * @param {string} ownerModule
 * @param {string} ownerExport
 * @param {string} invocation
 * @param {LlmCallCatalogEntry['profile_source']} profileSource
 * @param {string|null} profileRole
 * @param {string|null} [kindOverride=null]
 * @param {string|null} [parentRole=null]
 * @param {string|null} [exceptionNote=null]
 * @returns {LlmCallCatalogEntry}
 */
function entry(
  callId,
  kind,
  aliases,
  role,
  subsystem,
  purpose,
  ownerModule,
  ownerExport,
  invocation,
  profileSource,
  profileRole,
  kindOverride = null,
  parentRole = null,
  exceptionNote = null,
) {
  return Object.freeze({
    call_id: callId,
    catalog_scope: 'runtime_primary',
    canonical_inference_kind: kind,
    evidence_aliases: aliases,
    role_agent: role,
    subsystem,
    purpose,
    owner_module: ownerModule,
    owner_export: ownerExport,
    invocation_condition: invocation,
    profile_source: profileSource,
    profile_role: profileRole,
    kind_override: kindOverride,
    parent_role: parentRole,
    current_exception_note: exceptionNote,
  });
}

function annex(callId, kind, subsystem, purpose, ownerModule, ownerExport) {
  return Object.freeze({
    call_id: callId,
    catalog_scope: 'harness_annex',
    canonical_inference_kind: kind,
    evidence_aliases: [],
    role_agent: 'storyteller',
    subsystem,
    purpose,
    owner_module: ownerModule,
    owner_export: ownerExport,
    invocation_condition: 'Harness or test invocation only',
    profile_source: 'role_profile',
    profile_role: 'storyteller',
    kind_override: null,
    parent_role: null,
    current_exception_note: 'Non-blocking for runtime latency characterization',
  });
}

/** @param {string} callId */
export function findCatalogEntry(callId) {
  return PRIMARY_RUNTIME_CATALOG.find((row) => row.call_id === callId)
    ?? HARNESS_ANNEX_CATALOG.find((row) => row.call_id === callId)
    ?? null;
}

export const PRIMARY_RUNTIME_CALL_IDS = PRIMARY_RUNTIME_CATALOG.map((row) => row.call_id);

export const CATALOG_SCHEMA = 'hg_llm_call_catalog_v1';

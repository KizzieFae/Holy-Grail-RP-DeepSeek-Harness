/** Model-only prompt contribution allowlists (#134). Keep aligned with manifest_projection_policy.py */

const SCENE_AUTHORITY = new Set([
  'scene_setup',
  'scene_state',
  'scene_progression',
  'recent_environment',
  'continuity_canon',
  'scene_grounding',
  'active_constraints',
]);

const STORYTELLER_ADVISORY = new Set([
  'storyteller_narrative_priorities',
  'storyteller_active_tensions',
  'storyteller_progression_opportunities',
  'storyteller_unresolved_threads',
  'storyteller_thematic_context',
  'storyteller_progression_hooks',
  'storyteller_emphasis_guidance',
]);

const PLOT_OVERLAY = new Set([
  'overlay_goal',
  'overlay_pressure',
  'overlay_character_candidate',
]);

const DIRECTOR_DIGESTS = new Set([
  'recent_orchestration',
  'actor_suitability',
  'scene_pressures',
  'user_turn_source',
  'user_steering_hints',
]);

const CHARACTER_LANES = new Set([
  'character_identity',
  'character_expression',
  'character_relationships',
  'scene_context',
  'scene_pressures',
  'director_context',
  'character_private',
  'character_memory',
  'recent_scene_transcript',
  'user_turn_trigger',
  'continuity_summary',
  'librarian_knowledge',
  'librarian_synthesis',
  'authored_character_knowledge',
  'learned_world_knowledge',
  'scene_reference',
  'user_profile',
]);

const NARRATOR_PRESENTATION_LANES = new Set([
  'narrator_environment_baseline',
  'immediate_user_turn_context',
  'triggering_user_context',
  'committed_move',
  'director_decision',
  'environmental_response_obligation',
]);

const NARRATOR_ENV_COGNITION_LANES = new Set([
  'narrator_environment_baseline',
  'immediate_user_turn_context',
  'triggering_user_context',
  'narrator_environment_cognition',
]);

const COMMON_INSTRUCTION = new Set(['inference_instruction']);
const CORRECTION = new Set(['semantic_correction']);
const PLOT_COGNITION_INIT = new Set(['active_constraints']);
const PLOT_COGNITION_UPDATE = new Set(['active_constraints', 'advisory_context']);
const PLOT_COGNITION_EPISTEMIC = new Set(['active_constraints', 'derived']);

/** @type {Record<string, Set<string>>} */
export const ALLOWED_SOURCE_KINDS = {
  character_turn: union(
    SCENE_AUTHORITY,
    STORYTELLER_ADVISORY,
    PLOT_OVERLAY,
    CHARACTER_LANES,
    COMMON_INSTRUCTION,
    CORRECTION,
  ),
  character_orientation: union(
    SCENE_AUTHORITY,
    STORYTELLER_ADVISORY,
    PLOT_OVERLAY,
    CHARACTER_LANES,
    COMMON_INSTRUCTION,
  ),
  character_semantic_evaluation: union(
    SCENE_AUTHORITY,
    CHARACTER_LANES,
    COMMON_INSTRUCTION,
    new Set(['active_constraints']),
  ),
  director_turn: union(
    SCENE_AUTHORITY,
    STORYTELLER_ADVISORY,
    PLOT_OVERLAY,
    DIRECTOR_DIGESTS,
    COMMON_INSTRUCTION,
    CORRECTION,
    new Set(['director_scratch']),
  ),
  director_semantic_qa: union(
    SCENE_AUTHORITY,
    DIRECTOR_DIGESTS,
    COMMON_INSTRUCTION,
    new Set(['active_constraints']),
  ),
  narrator_presentation: union(
    SCENE_AUTHORITY,
    STORYTELLER_ADVISORY,
    NARRATOR_PRESENTATION_LANES,
    COMMON_INSTRUCTION,
    CORRECTION,
  ),
  narrator_environment_cognition: union(
    NARRATOR_ENV_COGNITION_LANES,
    COMMON_INSTRUCTION,
  ),
  narrator_semantic_qa: union(
    SCENE_AUTHORITY,
    NARRATOR_PRESENTATION_LANES,
    COMMON_INSTRUCTION,
    new Set(['active_constraints']),
  ),
  librarian_mediation: union(COMMON_INSTRUCTION, new Set(['active_constraints'])),
  librarian_proposal: union(
    COMMON_INSTRUCTION,
    new Set(['active_constraints', 'librarian_knowledge']),
  ),
  librarian_proposal_contract_correction: union(
    COMMON_INSTRUCTION,
    new Set(['active_constraints', 'librarian_knowledge']),
  ),
  opening: union(
    SCENE_AUTHORITY,
    COMMON_INSTRUCTION,
    new Set(['scene_reference', 'character_profile']),
  ),
  opening_segmentation: union(
    SCENE_AUTHORITY,
    COMMON_INSTRUCTION,
    new Set(['opening_text', 'scene_reference']),
  ),
  player_decomposition: union(
    COMMON_INSTRUCTION,
    new Set(['player_pvr_entitlement_context']),
  ),
  player_visibility_triage: COMMON_INSTRUCTION,
  storyteller_orientation: union(
    DIRECTOR_DIGESTS,
    COMMON_INSTRUCTION,
    new Set(['scene_pressures', 'scene_state']),
  ),
  storyteller_assessment: union(
    COMMON_INSTRUCTION,
    new Set(['librarian_knowledge']),
  ),
  plot_cognition_init: PLOT_COGNITION_INIT,
  plot_cognition_init_contract_correction: PLOT_COGNITION_INIT,
  plot_cognition_update: PLOT_COGNITION_UPDATE,
  plot_cognition_update_contract_correction: PLOT_COGNITION_UPDATE,
  plot_cognition_epistemic_eval: PLOT_COGNITION_EPISTEMIC,
  plot_cognition_epistemic_eval_contract_correction: PLOT_COGNITION_EPISTEMIC,
  character_advisory_generation: PLOT_COGNITION_EPISTEMIC,
};

const INFERENCE_KIND_ALIASES = {
  director_decision: 'director_turn',
  character_move: 'character_turn',
};

/**
 * @param {string} inferenceKind
 * @returns {string}
 */
export function resolveInferenceKind(inferenceKind) {
  const key = String(inferenceKind || '').trim();
  return INFERENCE_KIND_ALIASES[key] ?? key;
}

/**
 * @param {string} inferenceKind
 * @param {Array<{ contribution_id?: string, source_kind?: string }>} contributions
 */
export function assertValidModelContextPackage(inferenceKind, contributions) {
  const resolved = resolveInferenceKind(inferenceKind);
  const allowed = ALLOWED_SOURCE_KINDS[resolved];
  if (!allowed) {
    throw new Error(`model-context package rejected: unknown inference_kind '${resolved}'`);
  }
  const violations = [];
  for (const contribution of contributions ?? []) {
    const kind = String(contribution?.source_kind ?? '');
    if (!allowed.has(kind)) {
      violations.push(
        `${contribution?.contribution_id ?? '<unknown>'}: disallowed source_kind '${kind}' for inference_kind '${resolved}'`,
      );
    }
  }
  if (violations.length > 0) {
    throw new Error(`model-context package rejected: ${violations.join('; ')}`);
  }
}

/** @param {Set<string>} sets */
function union(...sets) {
  const out = new Set();
  for (const current of sets) {
    for (const value of current) {
      out.add(value);
    }
  }
  return out;
}

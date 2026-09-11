import { findCatalogEntry } from '../../application/llm-call-catalog.mjs';
import { ALLOWED_SOURCE_KINDS } from '../manifest-projection-policy.mjs';

function contribution(sourceKind, content = 'fixture', authorityClass = null) {
  return {
    contribution_id: `fixture-${sourceKind}`,
    source_kind: sourceKind,
    authority_class: authorityClass ?? (sourceKind === 'inference_instruction' ? 'instruction' : 'authoritative'),
    priority: 1,
    content,
  };
}

function instruction(content = 'Return minimal valid JSON for this inference path.') {
  return contribution('inference_instruction', content);
}

/** Minimum valid model-facing contributions per inference kind (#134 allowlists). */
const MINIMUM_CONTRIBUTIONS_BY_KIND = {
  director_turn: ['inference_instruction', 'recent_orchestration'],
  director_semantic_qa: ['inference_instruction', 'active_constraints'],
  character_turn: ['inference_instruction', 'user_turn_trigger'],
  character_orientation: ['inference_instruction', 'scene_context'],
  character_semantic_evaluation: ['inference_instruction', 'active_constraints'],
  narrator_presentation: ['inference_instruction', 'committed_move'],
  narrator_environment_cognition: ['inference_instruction', 'narrator_environment_baseline'],
  narrator_semantic_qa: ['inference_instruction', 'active_constraints'],
  opening: ['inference_instruction', 'scene_reference'],
  opening_segmentation: ['inference_instruction', 'opening_text'],
  player_visibility_triage: ['inference_instruction'],
  player_decomposition: ['inference_instruction', 'player_pvr_entitlement_context'],
  librarian_mediation: ['inference_instruction', 'active_constraints'],
  librarian_mediation_contract_correction: ['inference_instruction', 'active_constraints'],
  librarian_proposal: ['inference_instruction', 'active_constraints'],
  librarian_proposal_contract_correction: ['inference_instruction', 'active_constraints'],
  storyteller_post_commit_issue_pressure: ['inference_instruction', 'active_constraints'],
  storyteller_post_commit_issue_pressure_contract_correction: ['inference_instruction', 'active_constraints'],
  storyteller_orientation: ['inference_instruction', 'scene_state'],
  storyteller_assessment: ['inference_instruction', 'librarian_knowledge'],
  plot_cognition_init: ['active_constraints'],
  plot_cognition_init_contract_correction: ['active_constraints'],
  plot_cognition_update: ['active_constraints', 'advisory_context'],
  plot_cognition_update_contract_correction: ['active_constraints', 'advisory_context'],
  plot_cognition_epistemic_eval: ['active_constraints', 'derived'],
  plot_cognition_epistemic_eval_contract_correction: ['active_constraints', 'derived'],
  character_advisory_generation: ['active_constraints', 'derived'],
};

function manifestForKind(inferenceKind) {
  const allowed = ALLOWED_SOURCE_KINDS[inferenceKind];
  if (!allowed) {
    throw new Error(`characterization fixture missing allowlist for ${inferenceKind}`);
  }
  const sourceKinds = MINIMUM_CONTRIBUTIONS_BY_KIND[inferenceKind] ?? ['inference_instruction'];
  const contributions = sourceKinds.map((sourceKind) => {
    if (!allowed.has(sourceKind)) {
      throw new Error(
        `characterization fixture uses disallowed source_kind '${sourceKind}' for ${inferenceKind}`,
      );
    }
    if (sourceKind === 'inference_instruction') return instruction();
    if (sourceKind === 'player_pvr_entitlement_context') {
      return contribution(sourceKind, '{"schema_version":1,"session_cast":[],"present_characters":[],"offstage_characters":[],"role_assignments":{}}');
    }
    if (sourceKind === 'derived' || sourceKind === 'active_constraints') {
      return contribution(sourceKind, '[]');
    }
    return contribution(sourceKind, 'fixture content');
  });
  return {
    manifest_id: `manifest-fixture-${inferenceKind}`,
    inference_id: `inf-fixture-${inferenceKind}`,
    inference_kind: inferenceKind,
    role: 'fixture',
    contributions,
  };
}

const MOCK_BY_KIND = {
  director_turn: '{"next_actor":"Ayame","environment_event":"","tension_shift":"steady","reason":"test","end_round":false}',
  character_turn: '{"beats":[{"action":"test","type":"action"}],"move_schema_version":2}',
  character_orientation: '{"orientation":"ready","schema":"hg_character_orientation_v1"}',
  character_semantic_evaluation: '{"schema":"hg_semantic_evaluation_result_v1","overall_result":"pass","findings":[]}',
  director_semantic_qa: '{"schema":"hg_semantic_qa_result_v1","overall_result":"pass","findings":[],"evaluation_target_role":"director","evaluation_pass_id":"qa-0"}',
  narrator_semantic_qa: '{"schema":"hg_semantic_qa_result_v1","overall_result":"pass","findings":[],"evaluation_target_role":"narrator","evaluation_pass_id":"qa-0"}',
  narrator_presentation: '{"presentation_text":"The scene continues.","perceptual_visibility":{"schema":"hg_perceptual_visibility_v2","units":[]}}',
  narrator_environment_cognition: '{"material_obligation":"respond","baseline_sufficient":false,"environment_observations":["door ajar"]}',
  opening: '{"presentation_text":"Rain begins.","perceptual_visibility":{"schema":"hg_perceptual_visibility_v2","units":[]}}',
  opening_segmentation: '{"segments":[{"text":"Rain begins.","unit_type":"speech"}]}',
  player_visibility_triage: '{"uniform_projection_safe":true}',
  player_decomposition: '{"schema":"hg_player_decomposition_v1","units":[]}',
  librarian_mediation: '{"schema":"hg_librarian_mediation_result_v1","selected_items":[]}',
  librarian_mediation_contract_correction: '{"schema":"hg_librarian_mediation_result_v1","selected_items":[]}',
  librarian_proposal: '{"proposal_generation_stage":"primary","proposal":{}}',
  librarian_proposal_contract_correction: '{"proposal_generation_stage":"contract_correction","proposal":{}}',
  storyteller_post_commit_issue_pressure: '{"proposal_generation_stage":"primary","proposal":{}}',
  storyteller_post_commit_issue_pressure_contract_correction: '{"proposal_generation_stage":"contract_correction","proposal":{}}',
  plot_cognition_init: '{"plot_cognition":{"stage":"init","proposal":{}}}',
  plot_cognition_init_contract_correction: '{"plot_cognition":{"stage":"contract_correction","proposal":{}}}',
  plot_cognition_update: '{"plot_cognition":{"stage":"update","proposal":{}}}',
  plot_cognition_update_contract_correction: '{"plot_cognition":{"stage":"contract_correction","proposal":{}}}',
  plot_cognition_epistemic_eval: '{"epistemic_eval":{"result":"pass"}}',
  plot_cognition_epistemic_eval_contract_correction: '{"epistemic_eval":{"stage":"contract_correction","result":"pass"}}',
  character_advisory_generation: '{"advisory":{"text":"observe"}}',
  storyteller_orientation: '{"orientation":{"focus":"scene"}}',
  storyteller_assessment: '{"assessment":{"focus":"thread"}}',
};

/**
 * @param {string} callId
 */
export function getCharacterizationFixture(callId) {
  const entry = findCatalogEntry(callId);
  if (!entry) throw new Error(`unknown characterization call_id: ${callId}`);
  const kind = entry.canonical_inference_kind;
  return {
    callId,
    inferenceKind: kind,
    manifest: manifestForKind(kind),
    prompt: `Characterization fixture prompt for ${callId}.`,
    mockResponses: [MOCK_BY_KIND[kind] ?? '{}'],
  };
}

export function listPrimaryCharacterizationFixtures() {
  return [
    'director_turn',
    'director_semantic_qa',
    'character_turn',
    'character_semantic_evaluation',
    'character_orientation',
    'librarian_mediation@character',
    'librarian_mediation@narrator',
    'storyteller_post_commit_issue_pressure',
    'storyteller_post_commit_issue_pressure_contract_correction',
    'narrator_presentation',
    'narrator_environment_cognition',
    'narrator_semantic_qa',
    'opening',
    'opening_segmentation',
    'player_visibility_triage',
    'player_decomposition',
    'storyteller_orientation',
    'storyteller_assessment',
    'plot_cognition_init',
    'plot_cognition_init_contract_correction',
    'plot_cognition_update',
    'plot_cognition_update_contract_correction',
    'plot_cognition_epistemic_eval',
    'plot_cognition_epistemic_eval_contract_correction',
    'character_advisory_generation',
  ];
}

import crypto from 'node:crypto';

import {
  PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
  REPLAN_EVALUATION_SCHEMA,
  REPLAN_PROPOSAL_SCHEMA,
  UPDATE_EVALUATION_SCHEMA,
  UPDATE_PROPOSAL_SCHEMA,
  buildNoChangeUpdateInference,
} from '../lib/plot-cognition-update-envelope.mjs';

export {
  epistemicPass,
  epistemicWithhold,
  epistemicRewriteRequired,
  epistemicMalformed,
  REGENERATION_GUIDANCE,
} from '../../tests/helpers/plot-cognition-projection-fixtures.mjs';

export { buildNoChangeUpdateInference };

function newId(prefix) {
  return `${prefix}-${crypto.randomUUID()}`;
}

export function buildInitProposal(initPrepare) {
  const snapshot = initPrepare?.source_snapshot ?? {};
  const pressureId = newId('hg-plot-pressure');
  return {
    schema: 'hg_plot_cognition_init_proposal_v1',
    proposal_id: newId('hg-plot-init-proposal'),
    source_snapshot_id: snapshot.snapshot_id ?? '',
    source_snapshot_fingerprint: initPrepare?.source_snapshot_fingerprint ?? snapshot.fingerprint ?? '',
    plot_cognition_scope_id: snapshot.plot_cognition_scope_id ?? '',
    adoption_rationale: 'Adopt initial pressure from authored motivation without steering action.',
    goals: [],
    pressures: [{
      schema: 'hg_unresolved_narrative_pressure_v1',
      pressure_id: pressureId,
      pressure_text: "Alice's unresolved tension remains present.",
      dramatic_rationale: 'Maintains narrative pressure without prescribing action.',
      basis_note: 'Authored motivation present.',
      basis_refs: [{ ref_kind: 'character_card', stable_ref: 'alice:goals' }],
      continuity_issue_refs: [],
      applicability: {
        applicability_kind: 'character',
        primary_character_id: 'Alice',
        involved_character_ids: ['Alice'],
      },
      creation_provenance: { source: 'storyteller' },
      activity_state: 'active',
    }],
    global_frame: null,
  };
}

export function buildReplanUpdateInference(prepareResponse, {
  supersededGoalId = 'hg-plot-goal-superseded',
  replacementGoalId = newId('hg-plot-goal'),
} = {}) {
  const snapshot = prepareResponse?.source_snapshot ?? {};
  const proposalId = newId('hg-plot-update-proposal');
  const replanProposalId = newId('hg-plot-replan-proposal');
  const replacementGoal = {
    schema: 'hg_plot_goal_v1',
    goal_id: replacementGoalId,
    intended_direction: 'Pursue reconciliation instead of revenge.',
    basis_note: null,
    basis_refs: [{ ref_kind: 'character_card', stable_ref: 'alice:goals' }],
    applicability: {
      applicability_kind: 'character',
      primary_character_id: 'Alice',
      involved_character_ids: ['Alice'],
    },
    planning_horizon: 'MEDIUM',
    creation_provenance: { source: 'storyteller' },
    lineage: { superseded_goal_ids: [supersededGoalId] },
    activity_state: 'active',
  };
  return JSON.stringify({
    schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
    update_proposal: {
      schema: UPDATE_PROPOSAL_SCHEMA,
      proposal_id: proposalId,
      source_snapshot_id: snapshot.snapshot_id ?? '',
      source_snapshot_fingerprint: prepareResponse.authority_source_fingerprint ?? '',
      plot_cognition_scope_id: snapshot.plot_cognition_scope_id ?? '',
      prior_store_revision: prepareResponse.prior_store_revision ?? 0,
      assimilation_rationale: 'Semantic divergence requires replan.',
      goals: [],
      pressures: [],
      global_frame: null,
      replan_required: true,
    },
    update_evaluation: {
      schema: UPDATE_EVALUATION_SCHEMA,
      evaluation_id: newId('hg-plot-update-eval'),
      proposal_id: proposalId,
      overall_result: 'accept',
      findings: [],
    },
    replan_proposal: {
      schema: REPLAN_PROPOSAL_SCHEMA,
      proposal_id: replanProposalId,
      source_snapshot_id: snapshot.snapshot_id ?? '',
      source_snapshot_fingerprint: prepareResponse.authority_source_fingerprint ?? '',
      plot_cognition_scope_id: snapshot.plot_cognition_scope_id ?? '',
      prior_store_revision: prepareResponse.prior_store_revision ?? 0,
      replan_rationale: 'Pursuit direction must change after refusal.',
      trigger_summary: 'Character refused prior pursuit.',
      goals: [replacementGoal],
      pressures: [],
      global_frame: null,
      superseded_goal_ids: [supersededGoalId],
      superseded_pressure_ids: [],
      retained_goal_ids: [],
      retained_pressure_ids: [],
    },
    replan_evaluation: {
      schema: REPLAN_EVALUATION_SCHEMA,
      evaluation_id: newId('hg-plot-replan-eval'),
      proposal_id: replanProposalId,
      overall_result: 'accept',
      findings: [],
      accepted_item_ids: [replacementGoalId],
    },
  });
}

export const VALID_CHARACTER_MOVE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'checks the latch carefully' }],
  motivation: {
    goal: 'inspect',
    tactic: 'slow check',
    emotional_driver: 'wary',
    risk_level: 'low',
  },
  semantic_evaluation: { decision: 'no_covered_change' },
};

export function directorFor(characterName) {
  return JSON.stringify({
    next_actor: characterName,
    end_round: false,
    reason: `${characterName} should speak next.`,
    environment_event: '',
    tension_shift: 'steady',
  });
}

export const NARRATOR_PROSE = 'Alice checked the latch with deliberate care.';

export function semanticPassCharacter() {
  return JSON.stringify({
    schema: 'hg_semantic_evaluation_result_v1',
    overall_result: 'pass',
    findings: [],
  });
}

export function createTrackingInference(mockResponses = []) {
  const calls = [];
  const startedAt = new Map();
  async function runEphemeralInference({
    inferenceId,
    manifest,
    mockResponses: localMocks = [],
    evidenceContext = {},
    ...rest
  }) {
    startedAt.set(inferenceId, Date.now());
    const queue = localMocks.length ? localMocks : mockResponses;
    const raw = queue[calls.length] ?? queue.at(-1) ?? '';
    calls.push({
      inferenceId,
      inferenceKind: evidenceContext.inferenceKind ?? null,
      evaluationPassId: evidenceContext.evaluationPassId ?? null,
      regenerationPrepareId: evidenceContext.regenerationPrepareId ?? null,
      parentInferenceId: evidenceContext.parentInferenceId ?? null,
      manifestContributionCount: manifest?.contributions?.length ?? 0,
      durationMs: Date.now() - (startedAt.get(inferenceId) ?? Date.now()),
      ...rest,
    });
    return {
      failed: false,
      raw,
      evidenceId: `ev-${inferenceId}`,
      inferenceSessionId: `sess-${inferenceId}`,
      trace: {},
    };
  }
  return { runEphemeralInference, calls };
}

export function summarizeInferenceCounts(calls) {
  const counts = {};
  for (const call of calls) {
    const kind = call.inferenceKind ?? 'unknown';
    counts[kind] = (counts[kind] ?? 0) + 1;
  }
  return counts;
}

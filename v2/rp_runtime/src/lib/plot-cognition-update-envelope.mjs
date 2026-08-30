import crypto from 'node:crypto';

import { parseJsonObject } from './inference-utils.mjs';

export const PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA = 'hg_plot_cognition_update_inference_v1';
export const UPDATE_PROPOSAL_SCHEMA = 'hg_plot_cognition_update_proposal_v1';
export const UPDATE_EVALUATION_SCHEMA = 'hg_plot_cognition_update_eval_v1';
export const REPLAN_PROPOSAL_SCHEMA = 'hg_plot_cognition_replan_proposal_v1';
export const REPLAN_EVALUATION_SCHEMA = 'hg_plot_cognition_replan_eval_v1';
export const PRIOR_OPERATIVE_COGNITION_SCHEMA = 'hg_plot_cognition_prior_operative_cognition_v1';

export function buildPlotCognitionUpdatePrompt(prepareResponse = null) {
  const snapshot = prepareResponse?.source_snapshot ?? {};
  const scopeId = snapshot.plot_cognition_scope_id ?? '';
  const fingerprint = prepareResponse?.authority_source_fingerprint
    ?? snapshot.authority_source_fingerprint
    ?? '';
  const snapshotId = snapshot.snapshot_id ?? '';
  const priorRevision = prepareResponse?.prior_store_revision ?? snapshot.prior_store_revision ?? 0;

  return [
    'You are the Plot Cognition update/replan semantic producer.',
    'Compare new authoritative semantic evidence (authority_projection and semantic_authority_excerpts)',
    'against prior_operative_cognition supplied in the manifest.',
    'prior_operative_cognition is advisory comparison context only — not authoritative evidence.',
    'Authoritative Continuity-derived excerpts override prior Storyteller cognition when they conflict.',
    '',
    'Semantic decision criteria (#61):',
    '- no_change: authoritative change does not materially require cognition alteration;',
    '  set update_evaluation.overall_result to no_change with no_change_rationale and replan_required false.',
    '- assimilable update: new authority changes relevant cognition but the operative strategic',
    '  direction remains viable; set replan_required false and propose incremental goal/pressure/frame',
    '  adjustments with overall_result accept.',
    '- invalidation replan: new authoritative developments materially invalidate assumptions,',
    '  trajectories, targets, or strategic direction such that prior cognition is no longer adequate;',
    '  set replan_required true and include replan_proposal and replan_evaluation.',
    'Base these judgments on semantic comparison — not keyword lists, event types, or pattern rules.',
    '',
    `Return ONLY one JSON object (no markdown fences, no commentary) with top-level schema ${PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA}.`,
    'Required top-level fields: schema, update_proposal, update_evaluation.',
    `update_proposal.schema must be "${UPDATE_PROPOSAL_SCHEMA}".`,
    `update_evaluation.schema must be "${UPDATE_EVALUATION_SCHEMA}".`,
    'update_proposal required fields: proposal_id, source_snapshot_id, source_snapshot_fingerprint,',
    'plot_cognition_scope_id, prior_store_revision, assimilation_rationale, replan_required (boolean).',
    `Copy plot_cognition_scope_id verbatim: "${scopeId}".`,
    `Copy source_snapshot_fingerprint verbatim: "${fingerprint}".`,
    `source_snapshot_id: "${snapshotId}". prior_store_revision: ${priorRevision}.`,
    'update_evaluation.overall_result must be one of: accept, revise, reject, no_change.',
    'When overall_result is no_change, include no_change_rationale.',
    'When replan_required is true, include replan_proposal and replan_evaluation with accepted replan.',
    'Do NOT omit the top-level schema field.',
    'Do NOT use alternate wrapper names or synonym fields.',
    'Serialization shape reference only (not a decision default):',
    `  ${JSON.stringify({
      schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
      update_proposal: {
        schema: UPDATE_PROPOSAL_SCHEMA,
        proposal_id: '<proposal_id>',
        source_snapshot_id: snapshotId,
        source_snapshot_fingerprint: fingerprint,
        plot_cognition_scope_id: scopeId,
        prior_store_revision: priorRevision,
        assimilation_rationale: '<comparison of authority vs prior cognition>',
        replan_required: '<boolean per semantic comparison>',
      },
      update_evaluation: {
        schema: UPDATE_EVALUATION_SCHEMA,
        evaluation_id: '<evaluation_id>',
        proposal_id: '<proposal_id>',
        overall_result: '<accept|revise|reject|no_change>',
      },
    })}`,
  ].join('\n');
}

export function buildPlotCognitionUpdateCorrectionPrompt({ priorRaw, structuralError, context }) {
  const prior = typeof priorRaw === 'string' ? priorRaw : JSON.stringify(priorRaw ?? {});
  const contractPrompt = buildPlotCognitionUpdatePrompt(context);
  return [
    'CONTRACT CORRECTION: Your previous response did not satisfy the required machine contract.',
    'Preserve the semantic judgment from that response unless satisfying the contract logically requires otherwise.',
    'Correct only the representation/serialization. Output JSON only — no markdown, no commentary.',
    '',
    `Previous response:\n${prior}`,
    '',
    `Structural validation error: ${structuralError}`,
    '',
    'Required contract:',
    contractPrompt,
    '',
    'Re-emit the result using exactly the required JSON contract.',
  ].join('\n');
}

export function manifestFromPlotCognitionUpdatePrepare(prepareResponse) {
  const snapshot = prepareResponse?.source_snapshot ?? {};
  const body = snapshot.canonical_body ?? {};
  const excerpts = snapshot.semantic_authority_excerpts ?? {};
  const priorOperativeCognition = snapshot.prior_operative_cognition ?? {};
  const payload = {
    authority_projection: body,
    semantic_authority_excerpts: excerpts,
    prior_operative_cognition: priorOperativeCognition,
  };
  const contributions = [
    {
      contribution_id: `${prepareResponse.manifest_id}-authority`,
      source_kind: 'active_constraints',
      authority_class: 'derived',
      knowledge_ids: ['plot_cognition:authority_projection'],
      priority: 10,
      content: JSON.stringify(payload).slice(0, 12000),
      provenance: {
        snapshot_id: snapshot.snapshot_id ?? null,
        authority_source_fingerprint: prepareResponse.authority_source_fingerprint ?? null,
      },
    },
  ];
  if (priorOperativeCognition && Object.keys(priorOperativeCognition).length > 0) {
    contributions.push({
      contribution_id: `${prepareResponse.manifest_id}-prior-operative-cognition`,
      source_kind: 'advisory_context',
      authority_class: 'advisory',
      knowledge_ids: ['plot_cognition:prior_operative_cognition'],
      priority: 20,
      content: JSON.stringify(priorOperativeCognition).slice(0, 8000),
      provenance: {
        snapshot_id: snapshot.snapshot_id ?? null,
        store_revision: priorOperativeCognition.store_revision ?? snapshot.prior_store_revision ?? null,
      },
    });
  }
  return { contributions };
}

function newId(prefix) {
  return `${prefix}-${crypto.randomUUID()}`;
}

export function parsePlotCognitionUpdateInference(raw, prepareResponse) {
  let parsed;
  try {
    parsed = typeof raw === 'string' ? parseJsonObject(raw) : raw;
  } catch (error) {
    return { ok: false, error: String(error?.message ?? error ?? 'parse_error'), result: null };
  }
  if (parsed?.schema !== PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA) {
    return { ok: false, error: 'schema_mismatch', result: null };
  }

  const snapshot = prepareResponse?.source_snapshot ?? {};
  const proposalRaw = parsed.update_proposal ?? {};
  const evaluationRaw = parsed.update_evaluation ?? {};
  const proposalId = String(proposalRaw.proposal_id ?? newId('hg-plot-update-proposal'));
  const evaluationId = String(evaluationRaw.evaluation_id ?? newId('hg-plot-update-eval'));

  const updateProposal = {
    schema: UPDATE_PROPOSAL_SCHEMA,
    proposal_id: proposalId,
    source_snapshot_id: String(proposalRaw.source_snapshot_id ?? snapshot.snapshot_id ?? ''),
    source_snapshot_fingerprint: String(
      proposalRaw.source_snapshot_fingerprint
      ?? prepareResponse.authority_source_fingerprint
      ?? snapshot.authority_source_fingerprint
      ?? '',
    ),
    plot_cognition_scope_id: String(
      proposalRaw.plot_cognition_scope_id ?? snapshot.plot_cognition_scope_id ?? '',
    ),
    prior_store_revision: Number(
      proposalRaw.prior_store_revision ?? prepareResponse.prior_store_revision ?? snapshot.prior_store_revision ?? 0,
    ),
    assimilation_rationale: String(
      proposalRaw.assimilation_rationale ?? 'Assimilate authoritative post-commit delta.',
    ),
    goals: Array.isArray(proposalRaw.goals) ? proposalRaw.goals : [],
    pressures: Array.isArray(proposalRaw.pressures) ? proposalRaw.pressures : [],
    global_frame: proposalRaw.global_frame ?? null,
    retained_goal_ids: proposalRaw.retained_goal_ids ?? [],
    retained_pressure_ids: proposalRaw.retained_pressure_ids ?? [],
    inactivated_goal_ids: proposalRaw.inactivated_goal_ids ?? [],
    inactivated_pressure_ids: proposalRaw.inactivated_pressure_ids ?? [],
    replan_required: Boolean(proposalRaw.replan_required),
    per_item_rationale: proposalRaw.per_item_rationale ?? [],
    revision_of_proposal_id: proposalRaw.revision_of_proposal_id ?? null,
  };

  const updateEvaluation = {
    schema: UPDATE_EVALUATION_SCHEMA,
    evaluation_id: evaluationId,
    proposal_id: proposalId,
    overall_result: String(evaluationRaw.overall_result ?? 'no_change'),
    findings: Array.isArray(evaluationRaw.findings) ? evaluationRaw.findings : [],
    revision_brief: evaluationRaw.revision_brief ?? null,
    accepted_item_ids: evaluationRaw.accepted_item_ids ?? [],
    no_change_rationale: String(
      evaluationRaw.no_change_rationale ?? 'No cognition adjustment warranted.',
    ),
  };

  let replanProposal = null;
  let replanEvaluation = null;
  if (updateProposal.replan_required) {
    const replanRaw = parsed.replan_proposal ?? {};
    const replanEvalRaw = parsed.replan_evaluation ?? {};
    const replanProposalId = String(replanRaw.proposal_id ?? newId('hg-plot-replan-proposal'));
    const replanEvaluationId = String(replanEvalRaw.evaluation_id ?? newId('hg-plot-replan-eval'));
    replanProposal = {
      schema: REPLAN_PROPOSAL_SCHEMA,
      proposal_id: replanProposalId,
      source_snapshot_id: updateProposal.source_snapshot_id,
      source_snapshot_fingerprint: updateProposal.source_snapshot_fingerprint,
      plot_cognition_scope_id: updateProposal.plot_cognition_scope_id,
      prior_store_revision: updateProposal.prior_store_revision,
      replan_rationale: String(replanRaw.replan_rationale ?? 'Replan pursuit direction.'),
      trigger_summary: String(replanRaw.trigger_summary ?? 'Update flagged replan_required.'),
      goals: Array.isArray(replanRaw.goals) ? replanRaw.goals : [],
      pressures: Array.isArray(replanRaw.pressures) ? replanRaw.pressures : [],
      global_frame: replanRaw.global_frame ?? null,
      superseded_goal_ids: replanRaw.superseded_goal_ids ?? [],
      superseded_pressure_ids: replanRaw.superseded_pressure_ids ?? [],
      retained_goal_ids: replanRaw.retained_goal_ids ?? [],
      retained_pressure_ids: replanRaw.retained_pressure_ids ?? [],
    };
    replanEvaluation = {
      schema: REPLAN_EVALUATION_SCHEMA,
      evaluation_id: replanEvaluationId,
      proposal_id: replanProposalId,
      overall_result: String(replanEvalRaw.overall_result ?? 'reject'),
      findings: Array.isArray(replanEvalRaw.findings) ? replanEvalRaw.findings : [],
      revision_brief: replanEvalRaw.revision_brief ?? null,
      accepted_item_ids: replanEvalRaw.accepted_item_ids ?? [],
    };
    if (replanEvaluation.overall_result !== 'accept') {
      return { ok: false, error: 'replan_required_without_accept', result: null };
    }
  }

  return {
    ok: true,
    error: null,
    result: {
      update_proposal: updateProposal,
      update_evaluation: updateEvaluation,
      replan_proposal: replanProposal,
      replan_evaluation: replanEvaluation,
    },
  };
}

export function buildNoChangeUpdateInference(prepareResponse) {
  const snapshot = prepareResponse?.source_snapshot ?? {};
  const proposalId = newId('hg-plot-update-proposal');
  return JSON.stringify({
    schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
    update_proposal: {
      schema: UPDATE_PROPOSAL_SCHEMA,
      proposal_id: proposalId,
      source_snapshot_id: snapshot.snapshot_id ?? '',
      source_snapshot_fingerprint: prepareResponse.authority_source_fingerprint ?? '',
      plot_cognition_scope_id: snapshot.plot_cognition_scope_id ?? '',
      prior_store_revision: prepareResponse.prior_store_revision ?? 0,
      assimilation_rationale: 'Assimilate authoritative post-commit delta.',
      goals: [],
      pressures: [],
      global_frame: null,
      replan_required: false,
    },
    update_evaluation: {
      schema: UPDATE_EVALUATION_SCHEMA,
      evaluation_id: newId('hg-plot-update-eval'),
      proposal_id: proposalId,
      overall_result: 'no_change',
      findings: [],
      no_change_rationale: 'No cognition adjustment warranted after commit.',
    },
  });
}

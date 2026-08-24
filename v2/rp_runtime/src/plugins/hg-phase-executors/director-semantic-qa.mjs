import { SEMANTIC_QA_RESULT_SCHEMA } from '../../lib/semantic-qa-envelope.mjs';
import { runSemanticQaEvaluation } from '../../lib/semantic-qa-substrate.mjs';
import { canApplySoftRegeneration } from './director-candidate-budget.mjs';

export const DIRECTOR_QA_CONFIG_ID = 'director_semantic_qa_v1';

export const VALID_DIMENSIONS = new Set([
  'dir_actor_suitability',
  'dir_scene_contradiction',
  'dir_env_event',
  'dir_pacing_tension',
  'dir_reason_coherence',
]);

function classifySemanticQaResult(result) {
  const findings = Array.isArray(result?.findings) ? result.findings : [];
  const hasHard = String(result?.overall_result ?? '') === 'reject_hard'
    || findings.some((finding) => finding.severity === 'hard');
  const hasSoft = !hasHard && (
    String(result?.overall_result ?? '') === 'reject_soft'
    || findings.some((finding) => finding.severity === 'soft')
  );
  return { findings, hasHard, hasSoft };
}

export function buildDirectorEvaluatorPrompt({
  schema = SEMANTIC_QA_RESULT_SCHEMA,
  evaluationTargetRole = 'director',
  evaluationPassId,
}) {
  const dimensions = [...VALID_DIMENSIONS].join(', ');
  return [
    'You are a bounded semantic QA evaluator for a Director decision candidate.',
    `Return ONLY one JSON object (no markdown) with schema ${schema}.`,
    `Set evaluation_target_role to "${evaluationTargetRole}" and evaluation_pass_id to "${evaluationPassId}".`,
    `Use overall_result pass|reject_soft|reject_hard and findings[] with dimensions: ${dimensions}.`,
    'Rubric:',
    '- dir_actor_suitability: eligible-actor fit, explicit user addressee, spotlight balance.',
    '  Hard findings may cite authoritative user:* and orch:* refs only.',
    '- dir_scene_contradiction: contradiction with committed scene facts.',
    '  Hard findings require authoritative refs (ground:*, event:*, canon:*, orch:*, issue:*:status|last_change).',
    '- dir_env_event: non-empty environment_event redundancy or implausibility.',
    '  Hard allowed for near-duplicate committed environment evidence.',
    '- dir_pacing_tension: tension_shift vs scene phase/pressures. Soft by default;',
    '  advisory issue:*:required_next_step refs cannot support hard findings.',
    '- dir_reason_coherence: reason explains chosen actor/tension/env. Soft only.',
    'Authority rules:',
    '- Hard findings require valid authoritative_citation.ref_id from the authority references block.',
    '- Do not judge missing context, global creative optimality, or replacement actor choice.',
    '- Do not emit replacement Director JSON or bind next_actor.',
    `If no issues, return {"schema":"${schema}","evaluation_target_role":"${evaluationTargetRole}",`,
    `"evaluation_pass_id":"${evaluationPassId}","overall_result":"pass","findings":[]}.`,
  ].join(' ');
}

export function buildCorrectionContextFromDirectorQa(qaResult, { evaluationPassId }) {
  const findings = (qaResult?.findings ?? []).map((finding) => ({
    dimension: finding.dimension,
    severity: finding.severity,
    finding: finding.finding,
    rationale: finding.rationale,
    ref_ids: finding.authoritative_citation?.ref_id
      ? [finding.authoritative_citation.ref_id]
      : [],
  }));
  return {
    source: 'semantic_qa',
    evaluation_pass_id: evaluationPassId,
    schema: SEMANTIC_QA_RESULT_SCHEMA,
    overall_result: qaResult?.overall_result ?? null,
    findings,
    evaluator_summary: qaResult?.evaluator_summary ?? null,
    instruction:
      'Revise your Director decision JSON for defensibility against the semantic QA findings. '
      + 'Do not invent replacement orchestration authority. Output replacement Director JSON only.',
  };
}

export function applyDirectorSemanticPolicy(evalOutcome, budget) {
  if (!evalOutcome || evalOutcome.infrastructureFailure || !evalOutcome.result) {
    return {
      action: 'infra_fail',
      evaluatorError: evalOutcome?.evaluatorError ?? 'semantic_qa_failed',
    };
  }

  const { findings, hasHard, hasSoft } = classifySemanticQaResult(evalOutcome.result);

  if (!hasHard && !hasSoft) {
    const advisoryFindings = findings.filter((finding) => finding.severity === 'soft');
    const residual = [
      ...advisoryFindings,
      ...(Array.isArray(evalOutcome.result.residual_soft_concerns)
        ? evalOutcome.result.residual_soft_concerns.map((item) => ({
          dimension: 'advisory',
          severity: 'soft',
          finding: String(item),
          rationale: 'residual_soft_concern',
        }))
        : []),
    ];
    return {
      action: 'pass',
      result: evalOutcome.result,
      residualSoftConcerns: residual.length ? residual : [],
    };
  }

  if (hasHard) {
    if (budget.attemptsUsed < budget.limit - 1) {
      return {
        action: 'hard_regen',
        result: evalOutcome.result,
        findings,
      };
    }
    if (budget.retentionEligibleCandidate) {
      return {
        action: 'retain',
        result: evalOutcome.result,
        findings,
        candidate: budget.retentionEligibleCandidate,
      };
    }
    return {
      action: 'hard_regen',
      result: evalOutcome.result,
      findings,
      exhausted: true,
    };
  }

  if (canApplySoftRegeneration(budget)) {
    return {
      action: 'soft_regen',
      result: evalOutcome.result,
      findings,
    };
  }

  return {
    action: 'accept_with_residuals',
    result: evalOutcome.result,
    residualSoftConcerns: findings,
  };
}

export async function runDirectorSemanticEvaluation({
  api,
  runEphemeralInference,
  directorInferenceId,
  hgSceneId,
  hgRoundId,
  hgSessionId,
  turnIndex,
  evaluationPassId,
  candidateDecision,
  rawModelOutput,
  actorsUsedThisRound,
  semanticEvaluatorProfile,
  mockSemanticResponse,
  parentDirectorEvidenceId,
  infrastructureAttempt = 0,
}) {
  return runSemanticQaEvaluation({
    runEphemeralInference,
    prepareContext: () => api.prepareDirectorSemanticQaContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: directorInferenceId,
      turn_index: turnIndex,
      evaluation_pass_id: evaluationPassId,
      candidate_decision: candidateDecision,
      raw_model_output: rawModelOutput,
      actors_used_this_round: actorsUsedThisRound ?? [],
    }),
    buildEvaluatorPrompt: buildDirectorEvaluatorPrompt,
    evidenceContextBase: {
      hgSessionId,
      hgSceneId,
      hgRoundId,
      inferenceId: directorInferenceId,
      attemptIndex: 0,
    },
    evaluationPassId,
    evaluationTargetRole: 'director',
    parentCandidateEvidenceId: parentDirectorEvidenceId,
    mockResponse: mockSemanticResponse,
    modelProfile: semanticEvaluatorProfile,
    infrastructureAttempt,
  });
}

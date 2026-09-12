import { CITATION_STATUS, SEMANTIC_QA_RESULT_SCHEMA } from '../../lib/semantic-qa-envelope.mjs';
import { runSemanticQaEvaluation } from '../../lib/semantic-qa-substrate.mjs';

export const NARRATOR_QA_CONFIG_ID = 'narrator_semantic_qa_v1';

export const VALID_DIMENSIONS = new Set([
  'nar_attribution_error',
  'nar_committed_contradiction',
  'nar_action_intention_distortion',
  'nar_psychological_invention',
  'nar_framing_distortion',
  'nar_environmental_contradiction',
  'nar_environmental_under_description',
  'nar_environmental_repetition',
  'nar_environmental_invention',
]);

function findingHasAuthoritativeHardSupport(finding, findingIndex, citationValidations) {
  if (finding?.severity !== 'hard') return false;
  const validations = citationValidations ?? [];
  if (!validations.length) return true;
  const citation = validations.find(
    (entry) => entry.finding_index === findingIndex,
  );
  if (!citation) return false;
  return citation.status === CITATION_STATUS.VALID
    && citation.resolved_authority_class === 'authoritative';
}

export function classifySemanticQaResult(result, citationValidations = []) {
  const findings = Array.isArray(result?.findings) ? result.findings : [];
  const hasAuthoritativeHard = findings.some(
    (finding, index) => findingHasAuthoritativeHardSupport(finding, index, citationValidations),
  );
  const hasHard = hasAuthoritativeHard;
  const hasSoft = !hasHard && (
    String(result?.overall_result ?? '') === 'reject_soft'
    || String(result?.overall_result ?? '') === 'reject_hard'
    || findings.some((finding) => finding.severity === 'soft')
    || findings.some(
      (finding, index) => finding.severity === 'hard'
        && !findingHasAuthoritativeHardSupport(finding, index, citationValidations),
    )
  );
  return { findings, hasHard, hasSoft, hasAuthoritativeHard };
}

export function buildNarratorEvaluatorPrompt({
  schema = SEMANTIC_QA_RESULT_SCHEMA,
  evaluationTargetRole = 'narrator',
  evaluationPassId,
}) {
  return [
    'You are a bounded semantic QA evaluator for a Narrator presentation candidate.',
    `Return ONLY one JSON object (no markdown) with schema ${schema}.`,
    `Set evaluation_target_role to "${evaluationTargetRole}" and evaluation_pass_id to "${evaluationPassId}".`,
    'Apply the rubric and authority references supplied in the manifest contributions.',
    'Hard findings require authoritative_citation.ref_id with authority_class authoritative from the authority references block.',
    '- orch:* and derived refs cannot support hard rejection.',
    '- Do not duplicate F1/F2 speech verbatim/order checks.',
    '- Do not emit replacement Narrator prose.',
    `If no issues, return {"schema":"${schema}","evaluation_target_role":"${evaluationTargetRole}",`,
    `"evaluation_pass_id":"${evaluationPassId}","overall_result":"pass","findings":[]}.`,
  ].join(' ');
}

export function buildCorrectionContextFromNarratorQa(qaResult, { evaluationPassId }) {
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
      'Revise your Narrator presentation for fidelity against the semantic QA findings. '
      + 'Do not invent replacement authoritative prose bindings. Output replacement narration only.',
  };
}

export function applyNarratorSemanticPolicy(evalOutcome, { attemptIndex, maxAttempts = 2 }) {
  if (!evalOutcome || evalOutcome.infrastructureFailure || !evalOutcome.result) {
    return {
      action: 'infra_fail',
      evaluatorError: evalOutcome?.evaluatorError ?? 'semantic_qa_failed',
    };
  }

  const { findings, hasHard, hasSoft } = classifySemanticQaResult(
    evalOutcome.result,
    evalOutcome.citationValidations,
  );

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
    if (attemptIndex < maxAttempts - 1) {
      return {
        action: 'hard_regen',
        result: evalOutcome.result,
        findings,
      };
    }
    return {
      action: 'exhausted_fallback',
      result: evalOutcome.result,
      findings,
    };
  }

  if (attemptIndex < maxAttempts - 1) {
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

export async function runNarratorSemanticEvaluation({
  api,
  runEphemeralInference,
  narratorInferenceId,
  hgSceneId,
  hgRoundId,
  hgSessionId,
  characterId,
  domainCommitId,
  continuityTurnIndex,
  evaluationPassId,
  candidatePresentation,
  rawModelOutput,
  semanticEvaluatorProfile,
  mockSemanticResponse,
  parentNarratorEvidenceId,
  infrastructureAttempt = 0,
}) {
  return runSemanticQaEvaluation({
    runEphemeralInference,
    prepareContext: () => api.prepareNarratorSemanticQaContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: narratorInferenceId,
      character_id: characterId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
      evaluation_pass_id: evaluationPassId,
      candidate_presentation: candidatePresentation,
      raw_model_output: rawModelOutput,
    }),
    buildEvaluatorPrompt: buildNarratorEvaluatorPrompt,
    evidenceContextBase: {
      hgSessionId,
      hgSceneId,
      hgRoundId,
      inferenceId: narratorInferenceId,
      attemptIndex: 0,
      characterId,
      domainCommitId,
      continuityTurnIndex,
    },
    evaluationPassId,
    evaluationTargetRole: 'narrator',
    parentCandidateEvidenceId: parentNarratorEvidenceId,
    mockResponse: mockSemanticResponse,
    modelProfile: semanticEvaluatorProfile,
    infrastructureAttempt,
  });
}

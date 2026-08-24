/**
 * Shared semantic-QA decision evidence patch (#25).
 */

export function semanticQaDecisionPatch({
  evaluationPassId,
  evaluationTargetRole,
  evaluatorEvidenceId,
  result = null,
  rawEvaluatorOutput = null,
  infrastructureFailure = false,
  citationValidations = null,
  parseWarnings = null,
}) {
  return {
    semantic_qa: {
      evaluation_pass_id: evaluationPassId ?? null,
      evaluation_target_role: evaluationTargetRole ?? null,
      evaluator_evidence_id: evaluatorEvidenceId ?? null,
      infrastructure_failure: Boolean(infrastructureFailure),
      result,
      raw_evaluator_output: rawEvaluatorOutput,
      citation_validations: citationValidations ?? null,
      parse_warnings: parseWarnings ?? null,
    },
  };
}

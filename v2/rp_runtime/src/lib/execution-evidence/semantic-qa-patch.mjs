/**
 * Shared semantic-QA decision evidence patch (#25, #28 canonical placement).
 */

export function buildSemanticQaDecisionFields({
  evaluationPassId,
  evaluationTargetRole,
  evaluatorEvidenceId,
  policyAction = null,
  result = null,
  rawEvaluatorOutput = null,
  infrastructureFailure = false,
  citationValidations = null,
  parseWarnings = null,
  playerAuthorshipRepairObligation = null,
  playerAuthorshipRepairVerification = null,
  playerAuthorshipRepairCleared = false,
  playerAuthorshipRepairFailureReason = null,
}) {
  return {
    evaluation_pass_id: evaluationPassId ?? null,
    evaluation_target_role: evaluationTargetRole ?? null,
    evaluator_evidence_id: evaluatorEvidenceId ?? null,
    policy_action: policyAction ?? null,
    infrastructure_failure: Boolean(infrastructureFailure),
    result,
    raw_evaluator_output: rawEvaluatorOutput,
    citation_validations: citationValidations ?? null,
    parse_warnings: parseWarnings ?? null,
    player_authorship_repair_obligation: playerAuthorshipRepairObligation ?? null,
    player_authorship_repair_verification: playerAuthorshipRepairVerification ?? null,
    player_authorship_repair_cleared: Boolean(playerAuthorshipRepairCleared),
    player_authorship_repair_failure_reason: playerAuthorshipRepairFailureReason ?? null,
  };
}

/** @deprecated Use buildSemanticQaDecisionFields under decision.semantic_qa */
export function semanticQaDecisionPatch(args) {
  return {
    decision: {
      semantic_qa: buildSemanticQaDecisionFields(args),
    },
  };
}

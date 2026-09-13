import { CITATION_STATUS, SEMANTIC_QA_RESULT_SCHEMA } from '../../lib/semantic-qa-envelope.mjs';
import { runSemanticQaEvaluation } from '../../lib/semantic-qa-substrate.mjs';

export const NARRATOR_QA_CONFIG_ID = 'narrator_semantic_qa_v1';

export const PLAYER_AUTHORSHIP_DIMENSION = 'nar_player_authorship';

export const VALID_DIMENSIONS = new Set([
  'nar_attribution_error',
  'nar_committed_contradiction',
  'nar_action_intention_distortion',
  PLAYER_AUTHORSHIP_DIMENSION,
  'nar_psychological_invention',
  'nar_framing_distortion',
  'nar_environmental_contradiction',
  'nar_environmental_under_description',
  'nar_environmental_repetition',
  'nar_environmental_invention',
]);

export function findingHasAuthoritativeHardSupport(finding, findingIndex, citationValidations) {
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

export function extractPlayerAuthorshipHardFinding(findings, citationValidations = []) {
  const list = Array.isArray(findings) ? findings : [];
  return list.find(
    (finding, index) => finding?.dimension === PLAYER_AUTHORSHIP_DIMENSION
      && findingHasAuthoritativeHardSupport(finding, index, citationValidations),
  ) ?? null;
}

export function hasPlayerAuthorshipFinding(findings) {
  const list = Array.isArray(findings) ? findings : [];
  return list.some((finding) => finding?.dimension === PLAYER_AUTHORSHIP_DIMENSION);
}

export function buildPlayerAuthorshipRepairObligation({
  evalOutcome,
  evaluationPassId,
  attemptIndex,
  candidatePresentation = null,
}) {
  const findings = evalOutcome?.result?.findings ?? [];
  const citationValidations = evalOutcome?.citationValidations ?? [];
  const hardFinding = extractPlayerAuthorshipHardFinding(findings, citationValidations)
    ?? findings.find(
      (finding) => finding?.dimension === PLAYER_AUTHORSHIP_DIMENSION
        && finding?.severity === 'hard',
    )
    ?? null;
  if (!hardFinding) return null;
  const findingIndex = findings.indexOf(hardFinding);
  const citation = citationValidations.find((entry) => entry.finding_index === findingIndex);
  return {
    kind: 'nar_player_authorship_hard_repair',
    dimension: PLAYER_AUTHORSHIP_DIMENSION,
    status: 'pending',
    source_evaluation_pass_id: evaluationPassId,
    source_attempt_index: attemptIndex,
    offending_assertion: hardFinding.finding
      ?? hardFinding.candidate_evidence
      ?? null,
    rationale: hardFinding.rationale ?? null,
    authoritative_citation: hardFinding.authoritative_citation ?? null,
    candidate_presentation_excerpt: candidatePresentation ?? null,
    citation_status: citation?.status ?? null,
  };
}

export function assessPlayerAuthorshipRepairVerification(obligation, evalOutcome) {
  if (!obligation) {
    return { status: 'none' };
  }
  const { findings, hasHard, hasSoft } = classifySemanticQaResult(
    evalOutcome?.result,
    evalOutcome?.citationValidations ?? [],
  );
  const citationValidations = evalOutcome?.citationValidations ?? [];
  const persistingHard = extractPlayerAuthorshipHardFinding(findings, citationValidations);
  if (persistingHard) {
    return {
      status: 'persists',
      finding: persistingHard,
      reason: 'hard_nar_player_authorship_remains',
    };
  }
  const softPlayerAuthorship = findings.find(
    (finding) => finding?.dimension === PLAYER_AUTHORSHIP_DIMENSION
      && finding.severity === 'soft',
  );
  if (softPlayerAuthorship) {
    return {
      status: 'unverified',
      reason: 'soft_nar_player_authorship_insufficient_to_clear_obligation',
      finding: softPlayerAuthorship,
    };
  }
  if (!hasHard && !hasSoft && !hasPlayerAuthorshipFinding(findings)) {
    return { status: 'cleared', reason: 'no_nar_player_authorship_findings' };
  }
  return {
    status: 'unverified',
    reason: 'residual_semantic_concerns_without_player_authorship_repair_proof',
    hasHard,
    hasSoft,
  };
}

export function buildNarratorEvaluatorPrompt({
  schema = SEMANTIC_QA_RESULT_SCHEMA,
  evaluationTargetRole = 'narrator',
  evaluationPassId,
  playerAuthorshipRepairObligation = null,
}) {
  const lines = [
    'You are a bounded semantic QA evaluator for a Narrator presentation candidate.',
    `Return ONLY one JSON object (no markdown) with schema ${schema}.`,
    `Set evaluation_target_role to "${evaluationTargetRole}" and evaluation_pass_id to "${evaluationPassId}".`,
    'Use overall_result pass|reject_soft|reject_hard only (never fail, reject, or other values).',
    'Apply the rubric dimensions and authority references supplied in the manifest contributions.',
    'For unsupported Player sensation/embodiment or material Player-behavior amplification,',
    'use dimension nar_player_authorship (not nar_action_intention_distortion alone).',
    'Hard findings require authoritative_citation.ref_id with authority_class authoritative',
    'from the authority references block.',
    '- orch:* and derived refs cannot support hard rejection.',
    '- Do not duplicate F1/F2 speech verbatim/order checks.',
    '- Do not emit replacement Narrator prose.',
    `If no issues, return {"schema":"${schema}","evaluation_target_role":"${evaluationTargetRole}",`,
    `"evaluation_pass_id":"${evaluationPassId}","overall_result":"pass","findings":[]}.`,
  ];
  if (playerAuthorshipRepairObligation) {
    lines.push(
      'REPAIR VERIFICATION: a prior attempt produced a hard nar_player_authorship violation.',
      `Prior evaluation_pass_id: ${playerAuthorshipRepairObligation.source_evaluation_pass_id}.`,
      `Offending assertion: ${playerAuthorshipRepairObligation.offending_assertion ?? 'see manifest'}.`,
      `Authority failure: ${playerAuthorshipRepairObligation.rationale ?? 'unsupported Player authorship'}.`,
      'Verify the candidate removed or permissibly rephrased that unsupported Player attribution.',
      'If the violation persists, emit hard nar_player_authorship with authoritative citation.',
      'Soft-only or pass without nar_player_authorship clearance is insufficient when the violation remains.',
      'Do not invent compensatory Player facts.',
    );
  }
  return lines.join(' ');
}

export function buildCorrectionContextFromNarratorQa(
  qaResult,
  { evaluationPassId, playerAuthorshipRepairObligation = null },
) {
  const findings = (qaResult?.findings ?? []).map((finding) => ({
    dimension: finding.dimension,
    severity: finding.severity,
    finding: finding.finding,
    rationale: finding.rationale,
    ref_ids: finding.authoritative_citation?.ref_id
      ? [finding.authoritative_citation.ref_id]
      : [],
  }));
  const repairInstruction = playerAuthorshipRepairObligation
    ? ' Remove unsupported Player sensation, embodiment, or material behavioral amplification. '
      + 'Rephrase into environmental or otherwise non-Player-attributed narration. '
      + 'Do not invent compensatory Player facts.'
    : '';
  return {
    source: 'semantic_qa',
    evaluation_pass_id: evaluationPassId,
    schema: SEMANTIC_QA_RESULT_SCHEMA,
    overall_result: qaResult?.overall_result ?? null,
    findings,
    evaluator_summary: qaResult?.evaluator_summary ?? null,
    player_authorship_repair_obligation: playerAuthorshipRepairObligation ?? null,
    instruction:
      'Revise your Narrator presentation for fidelity against the semantic QA findings. '
      + 'Do not invent replacement authoritative prose bindings. Output replacement narration only.'
      + repairInstruction,
  };
}

function playerAuthorshipRepairBlockedPolicy(evalOutcome, {
  findings,
  repairVerification,
  repairFailureReason,
}) {
  return {
    action: 'player_authorship_fail_closed',
    result: evalOutcome.result,
    findings,
    repairVerification,
    repairFailureReason,
  };
}

export function applyNarratorSemanticPolicy(evalOutcome, {
  attemptIndex,
  maxAttempts = 2,
  pendingPlayerAuthorshipRepair = null,
}) {
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

  let repairVerification = null;
  if (pendingPlayerAuthorshipRepair) {
    repairVerification = assessPlayerAuthorshipRepairVerification(
      pendingPlayerAuthorshipRepair,
      evalOutcome,
    );
    if (repairVerification.status === 'persists' || repairVerification.status === 'unverified') {
      if (attemptIndex < maxAttempts - 1) {
        return {
          action: 'hard_regen',
          result: evalOutcome.result,
          findings,
          repairVerification,
          playerAuthorshipRepairObligation: pendingPlayerAuthorshipRepair,
        };
      }
      return playerAuthorshipRepairBlockedPolicy(evalOutcome, {
        findings,
        repairVerification,
        repairFailureReason: repairVerification.reason
          ?? (repairVerification.status === 'persists'
            ? 'player_authorship_violation_persists'
            : 'player_authorship_repair_unverified'),
      });
    }
  }

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
      repairVerification,
      playerAuthorshipRepairCleared: Boolean(pendingPlayerAuthorshipRepair),
    };
  }

  if (hasHard) {
    const playerAuthorshipHard = findings.some(
      (finding, index) => finding?.dimension === PLAYER_AUTHORSHIP_DIMENSION
        && findingHasAuthoritativeHardSupport(finding, index, evalOutcome.citationValidations),
    );
    if (attemptIndex < maxAttempts - 1) {
      return {
        action: 'hard_regen',
        result: evalOutcome.result,
        findings,
      };
    }
    if (playerAuthorshipHard) {
      return {
        action: 'player_authorship_fail_closed',
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

  if (pendingPlayerAuthorshipRepair) {
    return playerAuthorshipRepairBlockedPolicy(evalOutcome, {
      findings,
      repairVerification: repairVerification ?? assessPlayerAuthorshipRepairVerification(
        pendingPlayerAuthorshipRepair,
        evalOutcome,
      ),
      repairFailureReason: 'player_authorship_repair_unverified',
    });
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
  playerAuthorshipRepairObligation = null,
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
    buildEvaluatorPrompt: (args) => buildNarratorEvaluatorPrompt({
      ...args,
      playerAuthorshipRepairObligation,
    }),
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

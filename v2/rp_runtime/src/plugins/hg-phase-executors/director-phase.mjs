import {
  canContinueSelection,
  clearRetention,
  createDirectorSelectionBudget,
  recordDirectorAttempt,
  recordResidualSoftConcerns,
  recordSoftRegeneration,
  setRetentionEligible,
  setTerminalDisposition,
} from './director-candidate-budget.mjs';
import {
  applyDirectorSemanticPolicy,
  buildCorrectionContextFromDirectorQa,
  runDirectorSemanticEvaluation,
} from './director-semantic-qa.mjs';
import { directorDecisionPatch } from '../../lib/execution-evidence/phase-decision.mjs';
import { patchConsumerNiPackaging } from '../../lib/execution-evidence/ni-evidence.mjs';
import { parseJsonObject } from '../../lib/inference-utils.mjs';
import { LIVE_INFERENCE_TRANSPORT_PROMPT } from '../../lib/live-inference-prompts.mjs';
import { SEMANTIC_EVAL_INFRA_RETRIES } from '../../lib/phase-execution-policy.mjs';

function buildCandidateSnapshot({
  proposed,
  parseError,
  validation,
  evidenceId,
  attemptIndex,
  manifestId,
}) {
  return {
    decision: validation.normalized_decision ?? proposed,
    evidenceId,
    attemptIndex,
    manifestId,
    validation,
    proposed,
    parseError,
  };
}

function acceptDirectorCandidate({
  candidate,
  budget,
  recorder,
  hgSessionId,
  trace,
  sceneAgent,
  scope,
  directorInferenceId,
  directorInferenceSessionId,
  directorInferenceTrace,
  eligibilitySnapshot,
  participationContext,
  actorsUsedThisRound,
  terminalDisposition = 'accepted',
  retention = null,
}) {
  const directorDecision = candidate.decision;
  const endRound = Boolean(directorDecision.end_round);
  const selectedCharacterId = endRound
    ? null
    : String(candidate.validation?.selected_character_id ?? directorDecision.next_actor ?? '');

  recorder?.patchDecision(
    candidate.evidenceId,
    hgSessionId,
    directorDecisionPatch({
      proposed: candidate.proposed,
      parseError: candidate.parseError,
      validation: candidate.validation,
      outcome: terminalDisposition === 'semantic_soft_exhaustion_retained'
        ? 'semantic_soft_exhaustion_retained'
        : 'accepted',
      eligibilitySnapshot,
      participationContext,
      actorsUsedThisRound,
      residualSoftConcerns: budget.residualSoftConcerns,
      terminalDisposition,
      retention,
    }),
  );

  trace.emit(sceneAgent.session, 'hg/director-accepted', scope, {
    inference_id: directorInferenceId,
    director_inference_session_id: directorInferenceSessionId,
    role: 'director',
    attempt_index: candidate.attemptIndex,
    manifest_id: candidate.manifestId,
    selected_character_id: selectedCharacterId,
    normalized_decision: directorDecision,
    end_round: endRound,
    actors_used_this_round: actorsUsedThisRound,
    eligibility_snapshot: eligibilitySnapshot,
    terminal_disposition: terminalDisposition,
    retention,
    residual_soft_concerns: budget.residualSoftConcerns,
  });

  return {
    accepted: true,
    endRound,
    directorDecision,
    selectedCharacterId,
    directorManifestId: candidate.manifestId,
    directorInferenceSessionId,
    directorInferenceTrace,
    directorAttempt: candidate.attemptIndex,
    terminalDisposition,
    residualSoftConcerns: budget.residualSoftConcerns,
  };
}

export async function runDirectorPhase({
  runEphemeralInference,
  recorder,
  trace,
  api,
  sceneAgent,
  sceneSessionId,
  hgSessionId,
  hgSceneId,
  hgRoundId,
  directorInferenceId,
  directorAttemptSeed,
  mockDirectorResponses,
  mockDirectorSemanticQaResponses = [],
  directorResponseIndex,
  actorsUsedThisRound,
  turnIndex,
  eligibilitySnapshot,
  participationContext,
  modelProfile,
  semanticEvaluatorProfile,
  liveMaxAttempts,
  prompt,
  directorSemanticQaEnabled = true,
  storytellerAssessmentEvidenceId = null,
}) {
  const budget = createDirectorSelectionBudget(liveMaxAttempts);
  let directorAccepted = false;
  let directorDecision = null;
  let directorManifestId = '';
  let selectedCharacterId = null;
  let directorInferenceSessionId = null;
  let directorInferenceTrace = null;
  let endRound = false;
  let terminalDisposition = null;
  let responseIndex = directorResponseIndex;
  let priorEvidenceId = null;
  let correctionContext = null;
  let semanticEvalPassIndex = 0;
  let lastDirectorAttempt = directorAttemptSeed;
  let directorEvidenceId = null;
  const orchestrationEvidenceIds = [];
  const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };
  const evaluatorProfile = semanticEvaluatorProfile ?? modelProfile;
  const useMockDirectorResponses = mockDirectorResponses.length > 0;
  const attemptLimit = useMockDirectorResponses
    ? mockDirectorResponses.length
    : budget.limit;

  while (!directorAccepted && canContinueSelection(budget) && budget.attemptsUsed < attemptLimit) {
    const attemptIndex = directorAttemptSeed + budget.attemptsUsed;
    const manifest = await api.prepareDirectorContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: directorInferenceId,
      turn_index: turnIndex,
      attempt_index: attemptIndex,
      actors_used_this_round: actorsUsedThisRound,
      correction_context: correctionContext ?? undefined,
    });
    directorManifestId = String(manifest.manifest_id);

    const directorRun = await runEphemeralInference({
      inferenceId: `${directorInferenceId}-${attemptIndex}`,
      prompt: prompt ?? LIVE_INFERENCE_TRANSPORT_PROMPT,
      manifest,
      mockResponses: useMockDirectorResponses
        ? [mockDirectorResponses[responseIndex]]
        : [],
      modelProfile,
      evidenceContext: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        role: 'director',
        inferenceId: directorInferenceId,
        parentInferenceId: directorInferenceId,
        inferenceKind: 'director_decision',
        niForensics: true,
        attemptIndex,
        priorAttemptId: priorEvidenceId,
      },
    });
    directorInferenceSessionId = directorRun.inferenceSessionId;
    directorInferenceTrace = directorRun.trace;
    lastDirectorAttempt = attemptIndex;
    if (directorRun.evidenceId) {
      directorEvidenceId = directorRun.evidenceId;
      orchestrationEvidenceIds.push(directorRun.evidenceId);
    }

    if (!directorRun.failed) {
      patchConsumerNiPackaging(recorder, {
        hgSessionId,
        evidenceId: directorRun.evidenceId,
        manifest,
        storytellerAssessmentEvidenceId,
      });
    }

    if (directorRun.failed) {
      recorder?.patchDecision(
        directorRun.evidenceId,
        hgSessionId,
        directorDecisionPatch({
          proposed: null,
          outcome: 'inference_failed',
          eligibilitySnapshot,
          participationContext,
          actorsUsedThisRound,
        }),
      );
      priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
      trace.emit(sceneAgent.session, 'hg/inference-failed', scope, {
        inference_id: directorInferenceId,
        director_inference_session_id: directorInferenceSessionId,
        role: 'director',
        attempt_index: attemptIndex,
        manifest_id: directorManifestId,
        failure: directorRun.failure,
        inference_trace: directorInferenceTrace,
      });
      recordDirectorAttempt(budget);
      responseIndex += 1;
      continue;
    }

    let proposed;
    let parseError = null;
    try {
      proposed = parseJsonObject(directorRun.raw);
    } catch (error) {
      parseError = String(error);
      proposed = { parse_error: parseError };
    }

    trace.emit(sceneAgent.session, 'hg/director-proposed', scope, {
      inference_id: directorInferenceId,
      director_inference_session_id: directorInferenceSessionId,
      role: 'director',
      attempt_index: attemptIndex,
      manifest_id: directorManifestId,
      proposed_decision: proposed,
      raw_model_output: directorRun.raw,
      actors_used_this_round: actorsUsedThisRound,
      eligibility_snapshot: eligibilitySnapshot,
      inference_trace: directorInferenceTrace,
    });

    const validation = await api.validateDirectorDecision({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: directorInferenceId,
      turn_index: turnIndex,
      attempt_index: attemptIndex,
      proposed_decision: proposed,
      raw_model_output: directorRun.raw,
      eligibility_snapshot_id: participationContext?.eligibilitySnapshotId
        ?? eligibilitySnapshot?.eligibility_snapshot_id,
      director_constraint_actor: participationContext?.directorConstraintActor ?? null,
      continuation_c2_skip: Boolean(participationContext?.continuationC2Skip),
    });

    if (!validation.accepted) {
      recorder?.patchDecision(
        directorRun.evidenceId,
        hgSessionId,
        directorDecisionPatch({
          proposed,
          parseError,
          validation,
          outcome: 'rejected',
          eligibilitySnapshot,
          participationContext,
          actorsUsedThisRound,
        }),
      );
      priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
      trace.emit(sceneAgent.session, 'hg/director-rejected', scope, {
        inference_id: directorInferenceId,
        director_inference_session_id: directorInferenceSessionId,
        role: 'director',
        attempt_index: attemptIndex,
        validation_class: String(validation.validation_class ?? 'unknown'),
        reason: String(validation.reason ?? ''),
        retryable: Boolean(validation.retryable),
        proposed_decision: proposed,
        eligibility_snapshot: eligibilitySnapshot,
      });
      correctionContext = {
        source: 'deterministic_validation',
        validation_class: validation.validation_class,
        reason: validation.reason,
      };
      recordDirectorAttempt(budget);
      responseIndex += 1;
      continue;
    }

    const normalizedDecision = validation.normalized_decision ?? proposed;
    const candidateSnapshot = buildCandidateSnapshot({
      proposed,
      parseError,
      validation,
      evidenceId: directorRun.evidenceId,
      attemptIndex,
      manifestId: directorManifestId,
    });

    if (directorSemanticQaEnabled) {
      const evaluationPassId = `${directorInferenceId}-qa-${semanticEvalPassIndex}`;
      semanticEvalPassIndex += 1;
      let evalOutcome = null;
      for (let evalInfra = 0; evalInfra <= SEMANTIC_EVAL_INFRA_RETRIES; evalInfra += 1) {
        evalOutcome = await runDirectorSemanticEvaluation({
          api,
          runEphemeralInference,
          directorInferenceId,
          hgSceneId,
          hgRoundId,
          hgSessionId,
          turnIndex,
          evaluationPassId,
          candidateDecision: normalizedDecision,
          rawModelOutput: directorRun.raw,
          actorsUsedThisRound,
          semanticEvaluatorProfile: evaluatorProfile,
          mockSemanticResponse: mockDirectorSemanticQaResponses[responseIndex]
            ?? mockDirectorSemanticQaResponses[budget.attemptsUsed]
            ?? mockDirectorSemanticQaResponses[semanticEvalPassIndex - 1]
            ?? null,
          parentDirectorEvidenceId: directorRun.evidenceId,
          infrastructureAttempt: evalInfra,
        });
        if (!evalOutcome.infrastructureFailure) break;
      }

      if (evalOutcome?.evidenceId) {
        orchestrationEvidenceIds.push(evalOutcome.evidenceId);
      }

      if (!evalOutcome || evalOutcome.infrastructureFailure) {
        recorder?.patchDecision(
          directorRun.evidenceId,
          hgSessionId,
          directorDecisionPatch({
            proposed,
            parseError,
            validation,
            outcome: 'semantic_evaluator_failed',
            eligibilitySnapshot,
            participationContext,
            actorsUsedThisRound,
            semanticQa: {
              evaluationPassId,
              evaluationTargetRole: 'director',
              evaluatorEvidenceId: evalOutcome?.evidenceId ?? null,
              policyAction: 'infra_fail',
              infrastructureFailure: true,
              rawEvaluatorOutput: evalOutcome?.raw ?? null,
            },
            terminalDisposition: 'semantic_evaluator_failed',
          }),
        );
        setTerminalDisposition(budget, 'semantic_evaluator_failed');
        recordDirectorAttempt(budget);
        break;
      }

      const policy = applyDirectorSemanticPolicy(evalOutcome, budget);
      const semanticOutcome = policy.action === 'pass'
        ? 'semantic_passed'
        : policy.action === 'accept_with_residuals'
          ? 'semantic_accepted_with_residuals'
          : policy.action === 'soft_regen'
            ? 'semantic_rejected_soft'
            : policy.action === 'hard_regen'
              ? 'semantic_rejected_hard'
              : policy.action === 'retain'
                ? 'semantic_soft_exhaustion_retained'
                : 'semantic_evaluator_failed';

      recorder?.patchDecision(
        directorRun.evidenceId,
        hgSessionId,
        directorDecisionPatch({
          proposed,
          parseError,
          validation,
          outcome: semanticOutcome,
          eligibilitySnapshot,
          participationContext,
          actorsUsedThisRound,
          semanticQa: {
            evaluationPassId,
            evaluationTargetRole: 'director',
            evaluatorEvidenceId: evalOutcome.evidenceId,
            policyAction: policy.action,
            result: evalOutcome.result,
            rawEvaluatorOutput: evalOutcome.raw,
            citationValidations: evalOutcome.citationValidations,
            parseWarnings: evalOutcome.parseWarnings,
          },
          residualSoftConcerns: policy.residualSoftConcerns ?? null,
        }),
      );

      trace.emit(sceneAgent.session, 'hg/director-semantic-qa', scope, {
        inference_id: directorInferenceId,
        evaluation_pass_id: evaluationPassId,
        attempt_index: attemptIndex,
        policy_action: policy.action,
        overall_result: evalOutcome.result?.overall_result,
        findings: evalOutcome.result?.findings,
      });

      if (policy.action === 'infra_fail') {
        setTerminalDisposition(budget, 'semantic_evaluator_failed');
        recordDirectorAttempt(budget);
        break;
      }

      if (policy.action === 'pass') {
        if (policy.residualSoftConcerns?.length) {
          recordResidualSoftConcerns(budget, policy.residualSoftConcerns);
        }
        const accepted = acceptDirectorCandidate({
          candidate: candidateSnapshot,
          budget,
          recorder,
          hgSessionId,
          trace,
          sceneAgent,
          scope,
          directorInferenceId,
          directorInferenceSessionId,
          directorInferenceTrace,
          eligibilitySnapshot,
          participationContext,
          actorsUsedThisRound,
        });
        directorAccepted = accepted.accepted;
        directorDecision = accepted.directorDecision;
        selectedCharacterId = accepted.selectedCharacterId;
        endRound = accepted.endRound;
        terminalDisposition = accepted.terminalDisposition;
        priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
        responseIndex += 1;
        break;
      }

      if (policy.action === 'accept_with_residuals') {
        recordResidualSoftConcerns(budget, policy.residualSoftConcerns ?? []);
        const accepted = acceptDirectorCandidate({
          candidate: candidateSnapshot,
          budget,
          recorder,
          hgSessionId,
          trace,
          sceneAgent,
          scope,
          directorInferenceId,
          directorInferenceSessionId,
          directorInferenceTrace,
          eligibilitySnapshot,
          participationContext,
          actorsUsedThisRound,
          terminalDisposition: 'accepted_with_residual_soft_concerns',
        });
        directorAccepted = accepted.accepted;
        directorDecision = accepted.directorDecision;
        selectedCharacterId = accepted.selectedCharacterId;
        endRound = accepted.endRound;
        terminalDisposition = accepted.terminalDisposition;
        priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
        responseIndex += 1;
        break;
      }

      if (policy.action === 'retain') {
        const retained = policy.candidate ?? budget.retentionEligibleCandidate;
        const accepted = acceptDirectorCandidate({
          candidate: retained,
          budget,
          recorder,
          hgSessionId,
          trace,
          sceneAgent,
          scope,
          directorInferenceId,
          directorInferenceSessionId: retained.evidenceId ? directorInferenceSessionId : null,
          directorInferenceTrace,
          eligibilitySnapshot,
          participationContext,
          actorsUsedThisRound,
          terminalDisposition: 'semantic_soft_exhaustion_retained',
          retention: {
            retained_evidence_id: retained.evidenceId,
            retained_attempt_index: retained.attemptIndex,
            rejecting_attempt_index: attemptIndex,
          },
        });
        directorAccepted = accepted.accepted;
        directorDecision = accepted.directorDecision;
        selectedCharacterId = accepted.selectedCharacterId;
        endRound = accepted.endRound;
        terminalDisposition = accepted.terminalDisposition;
        setTerminalDisposition(budget, 'semantic_soft_exhaustion_retained');
        break;
      }

      if (policy.action === 'soft_regen') {
        setRetentionEligible(budget, candidateSnapshot);
        recordSoftRegeneration(budget);
        correctionContext = buildCorrectionContextFromDirectorQa(evalOutcome.result, {
          evaluationPassId,
        });
        priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
        recordDirectorAttempt(budget);
        responseIndex += 1;
        continue;
      }

      if (policy.action === 'hard_regen') {
        clearRetention(budget, { evidenceId: directorRun.evidenceId });
        if (policy.exhausted) {
          setTerminalDisposition(budget, 'hard_exhausted');
          recordDirectorAttempt(budget);
          break;
        }
        correctionContext = buildCorrectionContextFromDirectorQa(evalOutcome.result, {
          evaluationPassId,
        });
        priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
        recordDirectorAttempt(budget);
        responseIndex += 1;
        continue;
      }
    } else {
      const accepted = acceptDirectorCandidate({
        candidate: candidateSnapshot,
        budget,
        recorder,
        hgSessionId,
        trace,
        sceneAgent,
        scope,
        directorInferenceId,
        directorInferenceSessionId,
        directorInferenceTrace,
        eligibilitySnapshot,
        participationContext,
        actorsUsedThisRound,
      });
      directorAccepted = accepted.accepted;
      directorDecision = accepted.directorDecision;
      selectedCharacterId = accepted.selectedCharacterId;
      endRound = accepted.endRound;
      terminalDisposition = accepted.terminalDisposition;
      priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
      responseIndex += 1;
      break;
    }
  }

  if (!directorAccepted && !budget.terminalDisposition) {
    if (budget.retentionEligibleCandidate) {
      const retained = budget.retentionEligibleCandidate;
      const accepted = acceptDirectorCandidate({
        candidate: retained,
        budget,
        recorder,
        hgSessionId,
        trace,
        sceneAgent,
        scope,
        directorInferenceId,
        directorInferenceSessionId,
        directorInferenceTrace,
        eligibilitySnapshot,
        participationContext,
        actorsUsedThisRound,
        terminalDisposition: 'semantic_soft_exhaustion_retained',
        retention: {
          retained_evidence_id: retained.evidenceId,
          retained_attempt_index: retained.attemptIndex,
        },
      });
      directorAccepted = accepted.accepted;
      directorDecision = accepted.directorDecision;
      selectedCharacterId = accepted.selectedCharacterId;
      endRound = accepted.endRound;
      terminalDisposition = accepted.terminalDisposition;
      directorManifestId = retained.manifestId;
      setTerminalDisposition(budget, 'semantic_soft_exhaustion_retained');
    } else {
      setTerminalDisposition(budget, 'selection_budget_exhausted');
    }
  }

  return {
    accepted: directorAccepted,
    endRound,
    directorDecision,
    selectedCharacterId,
    directorManifestId,
    directorInferenceSessionId,
    directorInferenceTrace,
    directorAttempt: lastDirectorAttempt,
    directorResponseIndex: responseIndex,
    terminalDisposition: terminalDisposition ?? budget.terminalDisposition,
    residualSoftConcerns: budget.residualSoftConcerns,
    directorEvidenceId,
    orchestrationEvidenceIds: [...new Set(orchestrationEvidenceIds.filter(Boolean))],
  };
}

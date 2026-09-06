import { parsePerceptualVisibilityEnvelope } from '../../lib/perceptual-visibility-parse.mjs';
import {
  classifyNarratorFailureOutcome,
  inferenceOutcomeFromNormalizedKind,
  normalizeFinishKind,
} from '../../lib/narrator-inference-outcome.mjs';
import {
  isPermanentProviderFailure,
  narratorRetryDecision,
} from '../../lib/completion-finish-kind.mjs';
import { narratorDecisionPatch } from '../../lib/execution-evidence/phase-decision.mjs';
import {
  applyNarratorSemanticPolicy,
  buildCorrectionContextFromNarratorQa,
  runNarratorSemanticEvaluation,
} from './narrator-semantic-qa.mjs';
import { runNarratorEnvironmentCognition } from '../../lib/narrator-environment-cognition-substrate.mjs';
import {
  buildCorrectionContextFromPresentationValidation,
  extractStructuredMoveFromManifest,
  isEligibleFidelityValidationFailure,
  requiredSpeechDialoguesFromStructuredMove,
} from '../../lib/narrator-fidelity-correction.mjs';
import {
  buildForensicAttribution,
  classifyFailureBoundary,
  extractEnvironmentCognitionFailure,
  FORENSIC_BOUNDARIES,
  NARRATOR_FAILURE_CLASSES,
} from '../../lib/narrator-forensic-attribution.mjs';
import { SEMANTIC_EVAL_INFRA_RETRIES } from '../../lib/phase-execution-policy.mjs';

const MAX_NARRATOR_ATTEMPTS = 2;

function attemptInferenceId(baseId, attemptIndex) {
  return attemptIndex === 0 ? baseId : `${baseId}-retry-${attemptIndex}`;
}

function recordAttemptEvidence({
  recorder,
  evidenceId,
  hgSessionId,
  patch,
  environmentCognition = undefined,
  forensicContext = null,
}) {
  const merged = environmentCognition
    ? {
        ...patch,
        decision: {
          ...patch.decision,
          environment_cognition: environmentCognition,
        },
      }
    : patch;
  if (evidenceId && hgSessionId) {
    recorder?.patchDecision(evidenceId, hgSessionId, merged);
    return evidenceId;
  }
  if (recorder?.isEnabled?.() && hgSessionId && forensicContext) {
    return recorder.recordNarratorPhaseFailure({
      hgSessionId,
      patch: merged,
      ...forensicContext,
    });
  }
  return null;
}

function acceptNarratorPresentation({
  presentationText,
  perceptualVisibility = null,
  attemptIndex,
  finishKindRaw,
  finishKindNormalized,
  validation,
  narratorRun,
  domainCommitId,
  continuityTurnIndex,
  recorder,
  hgSessionId,
  trace,
  sceneAgent,
  scope,
  inferenceId,
  characterId,
  characterTurnIndex,
  manifestId,
  semanticQa = null,
  residualSoftConcerns = null,
  terminalDisposition = 'narrator_presented',
  environmentCognition = null,
}) {
  trace.emit(sceneAgent.session, 'hg/narrator-completed', scope, {
    inference_id: inferenceId,
    narrator_inference_session_id: narratorRun.inferenceSessionId,
    role: 'narrator',
    character_id: characterId,
    character_turn_index: characterTurnIndex,
    manifest_id: manifestId,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
    presentation_text: presentationText,
    attempt_index: attemptIndex,
    inference_trace: narratorRun.trace,
    terminal_disposition: terminalDisposition,
  });

  const inferenceOutcome = inferenceOutcomeFromNormalizedKind('complete', false);
  recordAttemptEvidence({
    recorder,
    evidenceId: narratorRun.evidenceId,
    hgSessionId,
    patch: narratorDecisionPatch({
      inferenceOutcome,
      presentationText,
      presentationFailed: false,
      domainCommitId,
      continuityTurnIndex,
      attemptIndex,
      finishKindRaw,
      finishKindNormalized,
      validationAccepted: true,
      validationClass: validation.validation_class ?? 'accepted',
      validationReason: validation.reason ?? '',
      retryable: false,
      retryDecision: 'accept',
      candidatePresentationText: presentationText,
      terminalDisposition,
      semanticQa,
      residualSoftConcerns,
      environmentCognition,
    }),
    environmentCognition,
  });

  return {
    presentation_rendered: true,
    presentation_text: presentationText,
    perceptual_visibility: perceptualVisibility,
    presentation_failed: false,
    inference_outcome: inferenceOutcome,
    narrator_inference_session_id: narratorRun.inferenceSessionId,
    narrator_manifest_id: manifestId,
    narrator_inference_trace: narratorRun.trace,
    narrator_evidence_id: narratorRun.evidenceId ?? null,
    terminal_disposition: terminalDisposition,
  };
}

export async function runNarratorPhase({
  runEphemeralInference,
  recorder,
  trace,
  api,
  sceneAgent,
  sceneSessionId,
  hgSessionId,
  hgSceneId,
  hgRoundId,
  characterId,
  domainCommitId,
  continuityTurnIndex,
  narratorInferenceId,
  mockNarratorResponses,
  mockNarratorSemanticQaResponses = [],
  mockNarratorEnvironmentCognitionResponse = null,
  characterTurnIndex,
  modelProfile,
  semanticEvaluatorProfile,
  narratorSemanticQaEnabled = true,
  prompt,
}) {
  const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };
  let lastFailureReason = 'narrator presentation failed';
  let lastInferenceOutcome = 'inference_error';
  let lastEvidenceId = null;
  let lastInferenceTrace = null;
  let lastInferenceSessionId = null;
  let correctionContext = null;
  let semanticEvalPassIndex = 0;
  let responseIndex = 0;

  trace.emit(sceneAgent.session, 'hg/narrator-started', scope, {
    inference_id: narratorInferenceId,
    role: 'narrator',
    character_id: characterId,
    character_turn_index: characterTurnIndex,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
  });

  let environmentCognitionAudit = null;
  let environmentCognitionEvidence = null;
  try {
    const envCognition = await runNarratorEnvironmentCognition({
      api,
      runEphemeralInference,
      hgSessionId,
      hgSceneId,
      hgRoundId,
      inferenceId: narratorInferenceId,
      characterId,
      domainCommitId,
      continuityTurnIndex,
      modelProfile,
      mockCognitionResponse: mockNarratorEnvironmentCognitionResponse,
      allowDeterministicFallback: true,
    });
    if (!envCognition.ok) {
      environmentCognitionAudit = {
        cognition_failed: true,
        failure_stage: envCognition.stage ?? 'cognition_failed',
        failure_boundary: envCognition.boundary ?? null,
        failure_reason: envCognition.failureReason ?? 'environment_cognition_unavailable',
        cognition_id: envCognition.audit?.cognition_id ?? null,
        domain_commit_id: domainCommitId,
      };
      environmentCognitionEvidence = environmentCognitionAudit;
    } else {
      environmentCognitionAudit = envCognition.audit;
      environmentCognitionEvidence = {
        cognition_failed: false,
        cognition_id: envCognition.audit?.cognition_id ?? null,
        domain_commit_id: domainCommitId,
      };
    }
  } catch (error) {
    const attribution = extractEnvironmentCognitionFailure(error);
    environmentCognitionAudit = {
      cognition_failed: true,
      failure_stage: attribution.stage,
      failure_boundary: attribution.boundary,
      failure_reason: attribution.reason,
      cognition_id: null,
      domain_commit_id: domainCommitId,
    };
    environmentCognitionEvidence = environmentCognitionAudit;
    trace.emit(sceneAgent.session, 'hg/narrator-environment-cognition-failed', scope, {
      inference_id: narratorInferenceId,
      reason: attribution.reason,
      failure_stage: attribution.stage,
      failure_boundary: attribution.boundary,
    });
  }

  for (let attemptIndex = 0; attemptIndex < MAX_NARRATOR_ATTEMPTS; attemptIndex += 1) {
    const inferenceId = attemptInferenceId(narratorInferenceId, attemptIndex);
    let manifestId = null;
    let manifest;
    try {
      manifest = await api.prepareNarratorContext({
        hg_scene_id: hgSceneId,
        hg_round_id: hgRoundId,
        inference_id: narratorInferenceId,
        character_id: characterId,
        domain_commit_id: domainCommitId,
        continuity_turn_index: continuityTurnIndex,
        attempt_index: attemptIndex,
        correction_context: correctionContext ?? undefined,
        ...(environmentCognitionAudit?.cognition_failed
          ? { cognition_failure: environmentCognitionAudit }
          : {
              environmental_response_obligations_text:
                environmentCognitionAudit?.environmental_response_obligations_text ?? undefined,
              environmental_response_obligations:
                environmentCognitionAudit?.environmental_response_obligations ?? undefined,
            }),
      });
      manifestId = String(manifest.manifest_id);
    } catch (error) {
      lastFailureReason = String(error?.message ?? error);
      lastInferenceOutcome = classifyNarratorFailureOutcome(lastFailureReason);
      trace.emit(sceneAgent.session, 'hg/narrator-failed', scope, {
        inference_id: narratorInferenceId,
        role: 'narrator',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        manifest_id: manifestId,
        domain_commit_id: domainCommitId,
        continuity_turn_index: continuityTurnIndex,
        reason: lastFailureReason,
        presentation_failure_class: 'runtime_render',
        canon_preserved: true,
      });
      recordAttemptEvidence({
        recorder,
        evidenceId: null,
        hgSessionId,
        patch: narratorDecisionPatch({
          inferenceOutcome: lastInferenceOutcome,
          presentationText: null,
          presentationFailed: true,
          failureReason: lastFailureReason,
          domainCommitId,
          continuityTurnIndex,
          attemptIndex,
          retryable: false,
          retryDecision: 'terminal_fallback',
          terminalDisposition: 'committed_fallback',
          forensicAttribution: buildForensicAttribution({
            failureClass: NARRATOR_FAILURE_CLASSES.CONTEXT_PREPARE,
            boundary: classifyFailureBoundary(error, FORENSIC_BOUNDARIES.DOMAIN_API),
            stage: 'prepare_narrator_context',
            failureReason: lastFailureReason,
          }),
        }),
        forensicContext: {
          hgSceneId,
          hgRoundId,
          characterId,
          inferenceId: narratorInferenceId,
          attemptIndex,
          domainCommitId,
          continuityTurnIndex,
          manifestId,
          failureClass: NARRATOR_FAILURE_CLASSES.CONTEXT_PREPARE,
          boundary: classifyFailureBoundary(error, FORENSIC_BOUNDARIES.DOMAIN_API),
          stage: 'prepare_narrator_context',
        },
      });
      return {
        presentation_rendered: false,
        presentation_text: null,
        presentation_failed: true,
        inference_outcome: lastInferenceOutcome,
        presentation_failure_reason: lastFailureReason,
        narrator_manifest_id: manifestId,
        narrator_evidence_id: null,
        terminal_disposition: 'committed_fallback',
      };
    }

    let narratorRun = null;
    let finishKindRaw = null;
    let finishKindNormalized = 'unknown';
    let rejectedPresentationText = null;

    try {
      const narratorMockFallback = modelProfile?.kind === 'mock'
        ? ['She nodded thoughtfully, taking in the workshop around her.']
        : [];
      narratorRun = await runEphemeralInference({
        inferenceId,
        prompt: prompt ?? 'Render the committed character move as scene narration only.',
        manifest,
        mockResponses: mockNarratorResponses?.length
          ? mockNarratorResponses
          : narratorMockFallback,
        modelProfile,
        evidenceContext: {
          hgSessionId,
          hgSceneId,
          hgRoundId,
          role: 'narrator',
          characterId,
          inferenceId,
          inferenceKind: 'narrator_presentation',
          attemptIndex,
          priorAttemptId: lastEvidenceId,
          domainCommitId,
          continuityTurnIndex,
        },
      });
      lastEvidenceId = narratorRun.evidenceId ?? lastEvidenceId;
      if (narratorRun.trace) {
        lastInferenceTrace = narratorRun.trace;
      }
      if (narratorRun.inferenceSessionId) {
        lastInferenceSessionId = narratorRun.inferenceSessionId;
      }

      if (narratorRun.failed) {
        finishKindRaw = narratorRun.trace?.finish?.kind ?? null;
        finishKindNormalized = normalizeFinishKind(finishKindRaw, { failed: true });
        const failureMessage = narratorRun.failure?.message ?? 'narrator provider inference failed';
        const permanent = isPermanentProviderFailure(failureMessage, narratorRun.trace);
        const retry = narratorRetryDecision({
          attemptIndex,
          maxAttempts: MAX_NARRATOR_ATTEMPTS,
          normalizedKind: finishKindNormalized,
          permanentProviderFailure: permanent,
          failureMessage,
        });
        lastFailureReason = failureMessage;
        lastInferenceOutcome = inferenceOutcomeFromNormalizedKind(finishKindNormalized, false);
        recordAttemptEvidence({
          recorder,
          evidenceId: narratorRun.evidenceId,
          hgSessionId,
          patch: narratorDecisionPatch({
            inferenceOutcome: lastInferenceOutcome,
            presentationText: null,
            presentationFailed: true,
            failureReason: failureMessage,
            domainCommitId,
            continuityTurnIndex,
            attemptIndex,
            finishKindRaw,
            finishKindNormalized,
            retryable: retry.retryable,
            retryDecision: retry.retryDecision,
            terminalDisposition:
              retry.retryDecision === 'terminal_fallback' ? 'committed_fallback' : null,
            forensicAttribution: buildForensicAttribution({
              failureClass: NARRATOR_FAILURE_CLASSES.INFERENCE_RETURNED_FAILURE,
              boundary: FORENSIC_BOUNDARIES.INFERENCE_PROVIDER,
              stage: 'run_ephemeral_inference',
              failureReason: failureMessage,
            }),
          }),
        });
        if (retry.retryDecision === 'retry') {
          responseIndex += 1;
          continue;
        }
        break;
      }

      finishKindRaw = narratorRun.trace?.finish?.kind ?? null;
      finishKindNormalized = normalizeFinishKind(finishKindRaw, { failed: false });
      const parsedEnvelope = parsePerceptualVisibilityEnvelope(narratorRun.raw ?? '');
      let presentationText = String(parsedEnvelope.presentationText ?? '').trim();
      let perceptualVisibility = parsedEnvelope.perceptualVisibility;
      if (perceptualVisibility?.units?.length) {
        const nvrValidation = await api.validatePerceptualVisibility({
          hg_session_id: hgSessionId,
          domain_commit_id: domainCommitId,
          character_id: characterId,
          perceptual_visibility: perceptualVisibility,
        });
        if (nvrValidation.accepted && nvrValidation.record) {
          perceptualVisibility = nvrValidation.record;
        } else {
          perceptualVisibility = null;
        }
      }
      const emptyOutput = !presentationText;
      rejectedPresentationText = emptyOutput ? null : presentationText;

      if (finishKindNormalized !== 'complete' || emptyOutput) {
        const retry = narratorRetryDecision({
          attemptIndex,
          maxAttempts: MAX_NARRATOR_ATTEMPTS,
          normalizedKind: finishKindNormalized,
          emptyOutput,
          failureMessage: emptyOutput ? 'narrator produced empty presentation output' : null,
        });
        lastFailureReason = emptyOutput
          ? 'narrator produced empty presentation output'
          : `narrator completion classified as ${finishKindNormalized}`;
        lastInferenceOutcome = inferenceOutcomeFromNormalizedKind(
          finishKindNormalized,
          emptyOutput,
        );
        recordAttemptEvidence({
          recorder,
          evidenceId: narratorRun.evidenceId,
          hgSessionId,
          patch: narratorDecisionPatch({
            inferenceOutcome: lastInferenceOutcome,
            presentationText: null,
            presentationFailed: true,
            failureReason: lastFailureReason,
            domainCommitId,
            continuityTurnIndex,
            attemptIndex,
            finishKindRaw,
            finishKindNormalized,
            retryable: retry.retryable,
            retryDecision: retry.retryDecision,
            rejectedPresentationText,
            terminalDisposition:
              retry.retryDecision === 'terminal_fallback' ? 'committed_fallback' : null,
          }),
        });
        if (retry.retryDecision === 'retry') {
          responseIndex += 1;
          continue;
        }
        break;
      }

      const validation = await api.validateNarratorPresentation({
        hg_scene_id: hgSceneId,
        domain_commit_id: domainCommitId,
        presentation_text: presentationText,
      });

      if (!validation.accepted) {
        const retry = narratorRetryDecision({
          attemptIndex,
          maxAttempts: MAX_NARRATOR_ATTEMPTS,
          normalizedKind: 'complete',
          validationRetryable: Boolean(validation.retryable),
        });
        lastFailureReason = validation.reason || 'narrator presentation failed fidelity validation';
        lastInferenceOutcome = 'inference_error';
        const structuredMove = extractStructuredMoveFromManifest(manifest);
        const requiredSpeechDialogues = requiredSpeechDialoguesFromStructuredMove(structuredMove);
        const fidelityCorrection = retry.retryDecision === 'retry'
          && isEligibleFidelityValidationFailure(validation.validation_class, validation.retryable)
          ? buildCorrectionContextFromPresentationValidation(validation, {
            attemptIndex,
            narratorInferenceId,
            domainCommitId,
            requiredSpeechDialogues,
          })
          : null;
        recordAttemptEvidence({
          recorder,
          evidenceId: narratorRun.evidenceId,
          hgSessionId,
          patch: narratorDecisionPatch({
            inferenceOutcome: lastInferenceOutcome,
            presentationText: null,
            presentationFailed: true,
            failureReason: lastFailureReason,
            domainCommitId,
            continuityTurnIndex,
            attemptIndex,
            finishKindRaw,
            finishKindNormalized,
            validationAccepted: false,
            validationClass: validation.validation_class ?? null,
            validationReason: validation.reason ?? '',
            retryable: retry.retryable,
            retryDecision: retry.retryDecision,
            rejectedPresentationText: presentationText,
            candidatePresentationText: presentationText,
            fidelityCorrection,
            terminalDisposition:
              retry.retryDecision === 'terminal_fallback' ? 'committed_fallback' : null,
          }),
        });
        if (retry.retryDecision === 'retry') {
          correctionContext = fidelityCorrection;
          responseIndex += 1;
          continue;
        }
        break;
      }

      if (!narratorSemanticQaEnabled) {
        return acceptNarratorPresentation({
          presentationText,
          perceptualVisibility,
          attemptIndex,
          finishKindRaw,
          finishKindNormalized,
          validation,
          narratorRun,
          domainCommitId,
          continuityTurnIndex,
          recorder,
          hgSessionId,
          trace,
          sceneAgent,
          scope,
          inferenceId,
          characterId,
          characterTurnIndex,
          manifestId,
          environmentCognition: environmentCognitionEvidence,
        });
      }

      const evaluationPassId = `${narratorInferenceId}-qa-${semanticEvalPassIndex}`;
      semanticEvalPassIndex += 1;
      let evalOutcome = null;
      for (let evalInfra = 0; evalInfra <= SEMANTIC_EVAL_INFRA_RETRIES; evalInfra += 1) {
        evalOutcome = await runNarratorSemanticEvaluation({
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
          candidatePresentation: presentationText,
          rawModelOutput: narratorRun.raw,
          semanticEvaluatorProfile: semanticEvaluatorProfile ?? modelProfile,
          mockSemanticResponse: mockNarratorSemanticQaResponses[responseIndex]
            ?? mockNarratorSemanticQaResponses[attemptIndex]
            ?? mockNarratorSemanticQaResponses[semanticEvalPassIndex - 1]
            ?? null,
          parentNarratorEvidenceId: narratorRun.evidenceId,
          infrastructureAttempt: evalInfra,
        });
        if (!evalOutcome.infrastructureFailure) break;
      }

      if (!evalOutcome || evalOutcome.infrastructureFailure) {
        recordAttemptEvidence({
          recorder,
          evidenceId: narratorRun.evidenceId,
          hgSessionId,
          patch: narratorDecisionPatch({
            inferenceOutcome: 'inference_error',
            presentationText: null,
            presentationFailed: true,
            failureReason: evalOutcome?.evaluatorError ?? 'semantic evaluator failed',
            domainCommitId,
            continuityTurnIndex,
            attemptIndex,
            finishKindRaw,
            finishKindNormalized,
            validationAccepted: true,
            validationClass: validation.validation_class ?? 'accepted',
            validationReason: validation.reason ?? '',
            retryable: false,
            retryDecision: 'terminal_fallback',
            rejectedPresentationText: presentationText,
            terminalDisposition: 'semantic_evaluator_failed',
            semanticQa: {
              evaluationPassId,
              evaluationTargetRole: 'narrator',
              evaluatorEvidenceId: evalOutcome?.evidenceId ?? null,
              policyAction: 'infra_fail',
              infrastructureFailure: true,
              rawEvaluatorOutput: evalOutcome?.raw ?? null,
            },
          }),
        });
        lastFailureReason = evalOutcome?.evaluatorError ?? 'semantic evaluator failed';
        lastInferenceOutcome = 'inference_error';
        break;
      }

      const policy = applyNarratorSemanticPolicy(evalOutcome, {
        attemptIndex,
        maxAttempts: MAX_NARRATOR_ATTEMPTS,
      });

      const semanticOutcome = policy.action === 'pass'
        ? 'semantic_passed'
        : policy.action === 'accept_with_residuals'
          ? 'semantic_accepted_with_residuals'
          : policy.action === 'soft_regen'
            ? 'semantic_rejected_soft'
            : policy.action === 'hard_regen'
              ? 'semantic_rejected_hard'
              : policy.action === 'exhausted_fallback'
                ? 'semantic_hard_exhausted'
                : 'semantic_evaluator_failed';

      recordAttemptEvidence({
        recorder,
        evidenceId: narratorRun.evidenceId,
        hgSessionId,
        patch: narratorDecisionPatch({
          inferenceOutcome: inferenceOutcomeFromNormalizedKind('complete', false),
          presentationText: policy.action === 'accept_with_residuals'
            || policy.action === 'pass'
            ? presentationText
            : null,
          presentationFailed: policy.action !== 'pass'
            && policy.action !== 'accept_with_residuals',
          failureReason: policy.action === 'pass' || policy.action === 'accept_with_residuals'
            ? null
            : lastFailureReason,
          domainCommitId,
          continuityTurnIndex,
          attemptIndex,
          finishKindRaw,
          finishKindNormalized,
          validationAccepted: true,
          validationClass: validation.validation_class ?? 'accepted',
          validationReason: validation.reason ?? '',
          retryable: policy.action === 'soft_regen' || policy.action === 'hard_regen',
          retryDecision: policy.action === 'soft_regen' || policy.action === 'hard_regen'
            ? 'retry'
            : policy.action === 'exhausted_fallback' || policy.action === 'infra_fail'
              ? 'terminal_fallback'
              : 'accept',
          rejectedPresentationText: policy.action === 'pass'
            || policy.action === 'accept_with_residuals'
            ? null
            : presentationText,
          terminalDisposition: policy.action === 'accept_with_residuals'
            ? 'accepted_with_residual_soft_concerns'
            : policy.action === 'exhausted_fallback' || policy.action === 'infra_fail'
              ? 'committed_fallback'
              : policy.action === 'pass'
                ? 'narrator_presented'
                : null,
          semanticQa: {
            evaluationPassId,
            evaluationTargetRole: 'narrator',
            evaluatorEvidenceId: evalOutcome.evidenceId,
            result: evalOutcome.result,
            rawEvaluatorOutput: evalOutcome.raw,
            citationValidations: evalOutcome.citationValidations,
            parseWarnings: evalOutcome.parseWarnings,
            policyAction: policy.action,
          },
          residualSoftConcerns: policy.residualSoftConcerns ?? null,
        }),
      });

      trace.emit(sceneAgent.session, 'hg/narrator-semantic-qa', scope, {
        inference_id: inferenceId,
        evaluation_pass_id: evaluationPassId,
        attempt_index: attemptIndex,
        policy_action: policy.action,
        overall_result: evalOutcome.result?.overall_result,
        findings: evalOutcome.result?.findings,
      });

      if (policy.action === 'infra_fail') {
        lastFailureReason = policy.evaluatorError ?? 'semantic evaluator failed';
        lastInferenceOutcome = 'inference_error';
        break;
      }

      if (policy.action === 'pass') {
        return acceptNarratorPresentation({
          presentationText,
          perceptualVisibility,
          attemptIndex,
          finishKindRaw,
          finishKindNormalized,
          validation,
          narratorRun,
          domainCommitId,
          continuityTurnIndex,
          recorder,
          hgSessionId,
          trace,
          sceneAgent,
          scope,
          inferenceId,
          characterId,
          characterTurnIndex,
          manifestId,
          semanticQa: {
            evaluationPassId,
            evaluationTargetRole: 'narrator',
            evaluatorEvidenceId: evalOutcome.evidenceId,
            result: evalOutcome.result,
            policyAction: policy.action,
          },
          residualSoftConcerns: policy.residualSoftConcerns ?? null,
          environmentCognition: environmentCognitionEvidence,
        });
      }

      if (policy.action === 'accept_with_residuals') {
        return acceptNarratorPresentation({
          presentationText,
          perceptualVisibility,
          attemptIndex,
          finishKindRaw,
          finishKindNormalized,
          validation,
          narratorRun,
          domainCommitId,
          continuityTurnIndex,
          recorder,
          hgSessionId,
          trace,
          sceneAgent,
          scope,
          inferenceId,
          characterId,
          characterTurnIndex,
          manifestId,
          semanticQa: {
            evaluationPassId,
            evaluationTargetRole: 'narrator',
            evaluatorEvidenceId: evalOutcome.evidenceId,
            result: evalOutcome.result,
            policyAction: policy.action,
          },
          residualSoftConcerns: policy.residualSoftConcerns ?? [],
          terminalDisposition: 'accepted_with_residual_soft_concerns',
          environmentCognition: environmentCognitionEvidence,
        });
      }

      if (policy.action === 'soft_regen' || policy.action === 'hard_regen') {
        correctionContext = buildCorrectionContextFromNarratorQa(evalOutcome.result, {
          evaluationPassId,
        });
        responseIndex += 1;
        continue;
      }

      if (policy.action === 'exhausted_fallback') {
        lastFailureReason = 'narrator semantic hard rejection exhausted generation budget';
        lastInferenceOutcome = 'inference_error';
        break;
      }
    } catch (error) {
      const failureMessage = String(error?.message ?? error);
      const permanent = isPermanentProviderFailure(failureMessage, narratorRun?.trace);
      const retry = narratorRetryDecision({
        attemptIndex,
        maxAttempts: MAX_NARRATOR_ATTEMPTS,
        normalizedKind: finishKindNormalized,
        permanentProviderFailure: permanent,
        failureMessage,
      });
      lastFailureReason = failureMessage;
      lastInferenceOutcome = classifyNarratorFailureOutcome(failureMessage);
      const inferenceBoundary = classifyFailureBoundary(
        error,
        FORENSIC_BOUNDARIES.INFERENCE_PROVIDER,
      );
      const boundaryThrowBeforeInference = !narratorRun;
      const recordedEvidenceId = recordAttemptEvidence({
        recorder,
        evidenceId: narratorRun?.evidenceId ?? null,
        hgSessionId,
        patch: narratorDecisionPatch({
          inferenceOutcome: lastInferenceOutcome,
          presentationText: null,
          presentationFailed: true,
          failureReason: failureMessage,
          domainCommitId,
          continuityTurnIndex,
          attemptIndex,
          finishKindRaw,
          finishKindNormalized,
          retryable: retry.retryable,
          retryDecision: retry.retryDecision,
          rejectedPresentationText,
          terminalDisposition:
            retry.retryDecision === 'terminal_fallback' ? 'committed_fallback' : null,
          forensicAttribution: buildForensicAttribution({
            failureClass: NARRATOR_FAILURE_CLASSES.INFERENCE_BOUNDARY_THROW,
            boundary: inferenceBoundary,
            stage: 'run_ephemeral_inference',
            failureReason: failureMessage,
          }),
        }),
        forensicContext: narratorRun?.evidenceId
          ? null
          : {
            hgSceneId,
            hgRoundId,
            characterId,
            inferenceId: narratorInferenceId,
            attemptIndex,
            domainCommitId,
            continuityTurnIndex,
            manifestId,
            failureClass: NARRATOR_FAILURE_CLASSES.INFERENCE_BOUNDARY_THROW,
            boundary: inferenceBoundary,
            stage: 'run_ephemeral_inference',
          },
      });
      if (boundaryThrowBeforeInference) {
        lastInferenceTrace = null;
        lastInferenceSessionId = null;
        lastEvidenceId = recordedEvidenceId ?? null;
      } else if (recordedEvidenceId) {
        lastEvidenceId = recordedEvidenceId;
      }
      if (retry.retryDecision === 'retry') {
        responseIndex += 1;
        continue;
      }
      break;
    }
  }

  trace.emit(sceneAgent.session, 'hg/narrator-failed', scope, {
    inference_id: narratorInferenceId,
    role: 'narrator',
    character_id: characterId,
    character_turn_index: characterTurnIndex,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
    reason: lastFailureReason,
    presentation_failure_class: 'runtime_render',
    canon_preserved: true,
  });

  return {
    presentation_rendered: false,
    presentation_text: null,
    presentation_failed: true,
    inference_outcome: lastInferenceOutcome,
    presentation_failure_reason: lastFailureReason,
    narrator_inference_trace: lastInferenceTrace,
    narrator_inference_session_id: lastInferenceSessionId,
    narrator_evidence_id: lastEvidenceId,
    terminal_disposition: 'committed_fallback',
  };
}

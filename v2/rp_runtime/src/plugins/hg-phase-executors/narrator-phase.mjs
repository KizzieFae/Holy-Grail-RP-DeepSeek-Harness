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

const MAX_NARRATOR_ATTEMPTS = 2;

function attemptInferenceId(baseId, attemptIndex) {
  return attemptIndex === 0 ? baseId : `${baseId}-retry-${attemptIndex}`;
}

function recordAttemptEvidence({
  recorder,
  evidenceId,
  hgSessionId,
  patch,
}) {
  recorder?.patchDecision(evidenceId ?? null, hgSessionId, patch);
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
  characterTurnIndex,
  modelProfile,
  prompt,
}) {
  const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };
  let manifestId = null;
  let lastFailureReason = 'narrator presentation failed';
  let lastInferenceOutcome = 'inference_error';
  let lastEvidenceId = null;

  let manifest;
  try {
    manifest = await api.prepareNarratorContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: narratorInferenceId,
      character_id: characterId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
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
        attemptIndex: 0,
        retryable: false,
        retryDecision: 'terminal_fallback',
        terminalDisposition: 'committed_fallback',
      }),
    });
    return {
      presentation_rendered: false,
      presentation_text: null,
      presentation_failed: true,
      inference_outcome: lastInferenceOutcome,
      presentation_failure_reason: lastFailureReason,
      narrator_manifest_id: manifestId,
    };
  }

  trace.emit(sceneAgent.session, 'hg/narrator-started', scope, {
    inference_id: narratorInferenceId,
    role: 'narrator',
    character_id: characterId,
    character_turn_index: characterTurnIndex,
    manifest_id: manifestId,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
  });

  for (let attemptIndex = 0; attemptIndex < MAX_NARRATOR_ATTEMPTS; attemptIndex += 1) {
    const inferenceId = attemptInferenceId(narratorInferenceId, attemptIndex);
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
          attemptIndex,
          priorAttemptId: lastEvidenceId,
          domainCommitId,
          continuityTurnIndex,
        },
      });
      lastEvidenceId = narratorRun.evidenceId ?? lastEvidenceId;

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
          }),
        });
        if (retry.retryDecision === 'retry') {
          continue;
        }
        break;
      }

      finishKindRaw = narratorRun.trace?.finish?.kind ?? null;
      finishKindNormalized = normalizeFinishKind(finishKindRaw, { failed: false });
      const presentationText = String(narratorRun.raw ?? '').trim();
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
            terminalDisposition:
              retry.retryDecision === 'terminal_fallback' ? 'committed_fallback' : null,
          }),
        });
        if (retry.retryDecision === 'retry') {
          continue;
        }
        break;
      }

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
          terminalDisposition: 'narrator_presented',
        }),
      });

      return {
        presentation_rendered: true,
        presentation_text: presentationText,
        presentation_failed: false,
        inference_outcome: inferenceOutcome,
        narrator_inference_session_id: narratorRun.inferenceSessionId,
        narrator_manifest_id: manifestId,
        narrator_inference_trace: narratorRun.trace,
      };
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
      recordAttemptEvidence({
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
        }),
      });
      if (retry.retryDecision === 'retry') {
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
    manifest_id: manifestId,
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
    narrator_manifest_id: manifestId,
  };
}

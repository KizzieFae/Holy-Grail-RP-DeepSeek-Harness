import { parsePlayerUniformEligibilityVerificationEnvelope } from '../../lib/perceptual-visibility-parse.mjs';

export const PLAYER_UNIFORM_ELIGIBILITY_VERIFICATION_TASK_PROMPT =
  'Adversarially challenge whether the player-authored turn in the user message contains semantic content explicitly stated in the text that disqualifies uniform projection to all present Characters without semantic decomposition. Disqualify only actual stated nonuniform content; do not invent unstated internal state, hidden motivation, or hypothetical perceptibility differences.';

export function buildPlayerUniformEligibilityVerificationUserPrompt(playerContent) {
  return `${PLAYER_UNIFORM_ELIGIBILITY_VERIFICATION_TASK_PROMPT}\n\nPLAYER SOURCE:\n${playerContent}`;
}

export function isUniformEligibilityVerificationClear(parsed) {
  return parsed?.disposition === 'clear' && !parsed?.parseError;
}

export async function runPlayerUniformEligibilityVerification({
  runEphemeralInference,
  trace,
  api,
  sceneAgent,
  hgSessionId,
  hgSceneId,
  hgRoundId,
  triageInferenceId,
  playerContent,
  mockResponses,
  modelProfile,
}) {
  const verificationInferenceId = `${triageInferenceId}-uniform-eligibility-verification`;
  const scope = {
    hgSessionId,
    hgSceneId,
    hgRoundId,
    role: 'player_uniform_eligibility_verification',
  };

  trace?.emit?.(sceneAgent?.session, 'hg/player-uniform-eligibility-verification-started', scope, {
    inference_id: verificationInferenceId,
    triage_inference_id: triageInferenceId,
  });

  let manifest;
  try {
    manifest = await api.preparePlayerUniformEligibilityVerificationContext({
      hg_session_id: hgSessionId,
      inference_id: verificationInferenceId,
      hg_round_id: hgRoundId,
    });
  } catch (err) {
    trace?.emit?.(sceneAgent?.session, 'hg/player-uniform-eligibility-verification-failed', scope, {
      inference_id: verificationInferenceId,
      failure_class: 'context_prepare',
      reason: err instanceof Error ? err.message : String(err),
    });
    return {
      passed: false,
      disposition: 'context_prepare_failed',
      reason: 'uniform_eligibility_verification_context_prepare_failed',
      verificationInferenceId,
      evidenceId: null,
    };
  }

  try {
    const inferRun = await runEphemeralInference({
      inferenceId: verificationInferenceId,
      prompt: buildPlayerUniformEligibilityVerificationUserPrompt(playerContent),
      manifest,
      mockResponses: mockResponses ?? [],
      modelProfile,
      evidenceContext: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        role: 'player_uniform_eligibility_verification',
        inferenceId: verificationInferenceId,
        inferenceKind: 'player_uniform_eligibility_verification',
        attemptIndex: 0,
      },
    });

    if (inferRun.failed) {
      trace?.emit?.(sceneAgent?.session, 'hg/player-uniform-eligibility-verification-failed', scope, {
        inference_id: verificationInferenceId,
        failure_class: 'inference_unavailable',
        reason: inferRun.failure?.message ?? 'verification inference failed',
      });
      return {
        passed: false,
        disposition: 'inference_failed',
        reason: 'uniform_eligibility_verification_inference_unavailable',
        verificationInferenceId,
        evidenceId: inferRun.evidenceId,
      };
    }

    const parsed = parsePlayerUniformEligibilityVerificationEnvelope(inferRun.raw ?? '');
    if (parsed.parseError) {
      trace?.emit?.(sceneAgent?.session, 'hg/player-uniform-eligibility-verification-failed', scope, {
        inference_id: verificationInferenceId,
        failure_class: 'malformed_output',
        reason: parsed.parseError,
      });
      return {
        passed: false,
        disposition: 'malformed',
        reason: 'uniform_eligibility_verification_malformed_output',
        parseError: parsed.parseError,
        verificationInferenceId,
        evidenceId: inferRun.evidenceId,
      };
    }

    if (isUniformEligibilityVerificationClear(parsed)) {
      trace?.emit?.(sceneAgent?.session, 'hg/player-uniform-eligibility-verification-completed', scope, {
        inference_id: verificationInferenceId,
        disposition: 'clear',
        reason: parsed.reason,
      });
      return {
        passed: true,
        disposition: 'clear',
        reason: parsed.reason ?? 'no_disqualifier_found',
        auditNote: parsed.auditNote,
        verificationInferenceId,
        evidenceId: inferRun.evidenceId,
      };
    }

    trace?.emit?.(sceneAgent?.session, 'hg/player-uniform-eligibility-verification-completed', scope, {
      inference_id: verificationInferenceId,
      disposition: parsed.disposition,
      reason: parsed.reason,
    });
    return {
      passed: false,
      disposition: parsed.disposition ?? 'uncertain',
      reason: parsed.reason ?? 'uniform_eligibility_disqualified_or_uncertain',
      auditNote: parsed.auditNote,
      verificationInferenceId,
      evidenceId: inferRun.evidenceId,
    };
  } catch (err) {
    trace?.emit?.(sceneAgent?.session, 'hg/player-uniform-eligibility-verification-failed', scope, {
      inference_id: verificationInferenceId,
      failure_class: 'inference_unavailable',
      reason: err instanceof Error ? err.message : String(err),
    });
    return {
      passed: false,
      disposition: 'inference_failed',
      reason: 'uniform_eligibility_verification_exception',
      verificationInferenceId,
      evidenceId: null,
    };
  }
}

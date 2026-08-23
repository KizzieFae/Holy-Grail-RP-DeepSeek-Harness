import { inferenceAttemptLimit } from '../../lib/inference-profile.mjs';
import { directorDecisionPatch } from '../../lib/execution-evidence/phase-decision.mjs';
import { parseJsonObject } from '../../lib/inference-utils.mjs';

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
  directorResponseIndex,
  actorsUsedThisRound,
  turnIndex,
  eligibilitySnapshot,
  participationContext,
  modelProfile,
  liveMaxAttempts,
  prompt,
}) {
  let directorAttempt = directorAttemptSeed;
  let directorAccepted = false;
  let directorDecision = null;
  let directorManifestId = '';
  let selectedCharacterId = null;
  let directorInferenceSessionId = null;
  let directorInferenceTrace = null;
  let endRound = false;
  const attemptLimit = inferenceAttemptLimit(mockDirectorResponses, liveMaxAttempts);
  let attemptsUsed = 0;
  let responseIndex = directorResponseIndex;
  let priorEvidenceId = null;
  const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };

  while (!directorAccepted && attemptsUsed < attemptLimit) {
    const manifest = await api.prepareDirectorContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: directorInferenceId,
      turn_index: turnIndex,
      attempt_index: directorAttempt,
      actors_used_this_round: actorsUsedThisRound,
    });
    directorManifestId = String(manifest.manifest_id);

    const directorRun = await runEphemeralInference({
      inferenceId: `${directorInferenceId}-${directorAttempt}`,
      prompt: prompt ?? 'Produce your director decision as JSON only.',
      manifest,
      mockResponses: mockDirectorResponses.length
        ? [mockDirectorResponses[responseIndex]]
        : [],
      modelProfile,
      evidenceContext: {
        hgSessionId,
        hgSceneId,
        hgRoundId,
        role: 'director',
        inferenceId: directorInferenceId,
        attemptIndex: directorAttempt,
        priorAttemptId: priorEvidenceId,
      },
    });
    directorInferenceSessionId = directorRun.inferenceSessionId;
    directorInferenceTrace = directorRun.trace;

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
        attempt_index: directorAttempt,
        manifest_id: directorManifestId,
        failure: directorRun.failure,
        inference_trace: directorInferenceTrace,
      });
      directorAttempt += 1;
      responseIndex += 1;
      attemptsUsed += 1;
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
      attempt_index: directorAttempt,
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
      attempt_index: directorAttempt,
      proposed_decision: proposed,
      raw_model_output: directorRun.raw,
      eligibility_snapshot_id: participationContext?.eligibilitySnapshotId ?? eligibilitySnapshot?.eligibility_snapshot_id,
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
        attempt_index: directorAttempt,
        validation_class: String(validation.validation_class ?? 'unknown'),
        reason: String(validation.reason ?? ''),
        retryable: Boolean(validation.retryable),
        proposed_decision: proposed,
        eligibility_snapshot: eligibilitySnapshot,
      });
      directorAttempt += 1;
      responseIndex += 1;
      attemptsUsed += 1;
      continue;
    }

    directorAccepted = true;
    directorDecision = validation.normalized_decision ?? proposed;
    endRound = Boolean(directorDecision.end_round);
    selectedCharacterId = endRound
      ? null
      : String(validation.selected_character_id ?? directorDecision.next_actor ?? '');
    recorder?.patchDecision(
      directorRun.evidenceId,
      hgSessionId,
      directorDecisionPatch({
        proposed,
        parseError,
        validation,
        outcome: 'accepted',
        eligibilitySnapshot,
        participationContext,
        actorsUsedThisRound,
      }),
    );
    priorEvidenceId = directorRun.evidenceId ?? priorEvidenceId;
    trace.emit(sceneAgent.session, 'hg/director-accepted', scope, {
      inference_id: directorInferenceId,
      director_inference_session_id: directorInferenceSessionId,
      role: 'director',
      attempt_index: directorAttempt,
      manifest_id: directorManifestId,
      selected_character_id: selectedCharacterId,
      normalized_decision: directorDecision,
      end_round: endRound,
      actors_used_this_round: actorsUsedThisRound,
      eligibility_snapshot: eligibilitySnapshot,
    });
    responseIndex += 1;
  }

  return {
    accepted: directorAccepted,
    endRound,
    directorDecision,
    selectedCharacterId,
    directorManifestId,
    directorInferenceSessionId,
    directorInferenceTrace,
    directorAttempt,
    directorResponseIndex: responseIndex,
  };
}

import { inferenceAttemptLimit } from '../../lib/inference-profile.mjs';
import { parseJsonObject } from '../../lib/inference-utils.mjs';
import { appendHgEvent } from '../hg-rp-runtime/events.mjs';
import { roleForCharacter } from './role-utils.mjs';

export async function runCharacterPhase({
  runEphemeralInference,
  correlation,
  api,
  sceneAgent,
  sceneSessionId,
  hgSceneId,
  hgRoundId,
  characterId,
  directorDecision,
  characterInferenceId,
  mockResponses,
  characterTurnIndex,
  characterRole,
  modelProfile,
  liveMaxAttempts,
  prompt,
}) {
  const role = characterRole ?? roleForCharacter(characterId);
  let attemptIndex = 0;
  let committed = false;
  let continuityTurnIndex = null;
  let domainCommitId = null;
  let characterManifestId = '';
  let characterInferenceSessionId = null;
  let characterInferenceTrace = null;
  const attemptLimit = inferenceAttemptLimit(mockResponses, liveMaxAttempts);

  while (!committed && attemptIndex < attemptLimit) {
    const state = await api.getSceneState(hgSceneId);
    const expectedTurnIndex = Number(state.turn_counter ?? 0);
    const manifest = await api.prepareCharacterContext({
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      inference_id: characterInferenceId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: attemptIndex,
    });
    characterManifestId = String(manifest.manifest_id);

    const characterRun = await runEphemeralInference({
      inferenceId: `${characterInferenceId}-${attemptIndex}`,
      prompt: prompt ?? 'Produce your character move as JSON only.',
      manifest,
      mockResponses: mockResponses.length ? [mockResponses[attemptIndex]] : [],
      modelProfile,
    });
    characterInferenceSessionId = characterRun.inferenceSessionId;
    characterInferenceTrace = characterRun.trace;

    if (characterRun.failed) {
      appendHgEvent(sceneAgent.session, 'hg/inference-failed', {
        ...correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        attempt_index: attemptIndex,
        manifest_id: characterManifestId,
        failure: characterRun.failure,
        inference_trace: characterInferenceTrace,
      });
      attemptIndex += 1;
      continue;
    }

    let proposed;
    try {
      proposed = parseJsonObject(characterRun.raw);
    } catch (error) {
      proposed = { parse_error: String(error) };
    }

    appendHgEvent(sceneAgent.session, 'hg/move-proposed', {
      ...correlation({ hgSceneId, hgRoundId, sceneSessionId }),
      inference_id: characterInferenceId,
      character_inference_session_id: characterInferenceSessionId,
      role: 'character',
      character_id: characterId,
      character_turn_index: characterTurnIndex,
      attempt_index: attemptIndex,
      manifest_id: characterManifestId,
      proposed_move: proposed,
      raw_model_output: characterRun.raw,
      inference_trace: characterInferenceTrace,
    });

    const validation = await api.validateMove({
      inference_id: characterInferenceId,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      character_id: characterId,
      role,
      turn_index: expectedTurnIndex,
      attempt_index: attemptIndex,
      proposed_move: proposed,
      raw_model_output: characterRun.raw,
    });

    if (!validation.accepted) {
      appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
        ...correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        attempt_index: attemptIndex,
        validation_class: String(validation.validation_class ?? 'unknown'),
        reason: String(validation.reason ?? ''),
        retryable: Boolean(validation.retryable),
      });
      attemptIndex += 1;
      continue;
    }

    const commit = await api.commitMove({
      inference_id: characterInferenceId,
      hg_scene_id: hgSceneId,
      hg_round_id: hgRoundId,
      character_id: characterId,
      validated_move: validation.normalized_move ?? proposed,
      director_decision: directorDecision,
      expected_turn_index: expectedTurnIndex,
    });

    if (!commit.committed) {
      appendHgEvent(sceneAgent.session, 'hg/move-rejected', {
        ...correlation({ hgSceneId, hgRoundId, sceneSessionId }),
        inference_id: characterInferenceId,
        character_inference_session_id: characterInferenceSessionId,
        role: 'character',
        character_id: characterId,
        character_turn_index: characterTurnIndex,
        attempt_index: attemptIndex,
        validation_class: 'continuity_anchor',
        reason: String(commit.reason ?? 'commit rejected'),
        retryable: false,
      });
      attemptIndex += 1;
      continue;
    }

    committed = true;
    continuityTurnIndex = Number(commit.continuity_turn_index);
    domainCommitId = String(commit.domain_commit_id ?? '');
    appendHgEvent(sceneAgent.session, 'hg/move-committed', {
      ...correlation({ hgSceneId, hgRoundId, sceneSessionId }),
      inference_id: characterInferenceId,
      character_inference_session_id: characterInferenceSessionId,
      role: 'character',
      character_id: characterId,
      character_turn_index: characterTurnIndex,
      attempt_index: attemptIndex,
      manifest_id: characterManifestId,
      continuity_turn_index: continuityTurnIndex,
      domain_commit_id: domainCommitId,
    });
  }

  return {
    committed,
    characterId,
    continuityTurnIndex,
    domainCommitId,
    characterManifestId,
    characterInferenceSessionId,
    characterInferenceTrace,
  };
}

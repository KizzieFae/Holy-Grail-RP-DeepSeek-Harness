import {
  classifyNarratorFailureOutcome,
  classifyNarratorInferenceOutcome,
} from '../../lib/narrator-inference-outcome.mjs';

export async function runNarratorPhase({
  runEphemeralInference,
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
  const manifest = await api.prepareNarratorContext({
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    inference_id: narratorInferenceId,
    character_id: characterId,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
  });
  const manifestId = String(manifest.manifest_id);
  const scope = { hgSessionId, hgSceneId, hgRoundId, sceneSessionId };

  trace.emit(sceneAgent.session, 'hg/narrator-started', scope, {
    inference_id: narratorInferenceId,
    role: 'narrator',
    character_id: characterId,
    character_turn_index: characterTurnIndex,
    manifest_id: manifestId,
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
  });

  try {
    const narratorMockFallback = modelProfile?.kind === 'mock'
      ? ['She nodded thoughtfully, taking in the workshop around her.']
      : [];
    const narratorRun = await runEphemeralInference({
      inferenceId: narratorInferenceId,
      prompt: prompt ?? 'Render the committed character move as scene narration only.',
      manifest,
      mockResponses: mockNarratorResponses?.length
        ? mockNarratorResponses
        : narratorMockFallback,
      modelProfile,
    });

    if (narratorRun.failed) {
      throw new Error(narratorRun.failure?.message ?? 'narrator provider inference failed');
    }

    const presentationText = narratorRun.raw.trim();
    if (!presentationText) {
      throw new Error('narrator produced empty presentation output');
    }

    trace.emit(sceneAgent.session, 'hg/narrator-completed', scope, {
      inference_id: narratorInferenceId,
      narrator_inference_session_id: narratorRun.inferenceSessionId,
      role: 'narrator',
      character_id: characterId,
      character_turn_index: characterTurnIndex,
      manifest_id: manifestId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
      presentation_text: presentationText,
      inference_trace: narratorRun.trace,
    });

    const inferenceOutcome = classifyNarratorInferenceOutcome(
      narratorRun.trace,
      presentationText,
    );

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
    trace.emit(sceneAgent.session, 'hg/narrator-failed', scope, {
      inference_id: narratorInferenceId,
      role: 'narrator',
      character_id: characterId,
      character_turn_index: characterTurnIndex,
      manifest_id: manifestId,
      domain_commit_id: domainCommitId,
      continuity_turn_index: continuityTurnIndex,
      reason: String(error?.message ?? error),
      presentation_failure_class: 'runtime_render',
      canon_preserved: true,
    });
    const inferenceOutcome = classifyNarratorFailureOutcome(error?.message);
    return {
      presentation_rendered: false,
      presentation_text: null,
      presentation_failed: true,
      inference_outcome: inferenceOutcome,
      presentation_failure_reason: String(error?.message ?? error),
      narrator_manifest_id: manifestId,
    };
  }
}

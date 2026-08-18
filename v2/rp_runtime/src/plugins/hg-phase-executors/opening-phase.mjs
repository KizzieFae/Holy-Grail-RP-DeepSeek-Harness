const OPENING_PROMPT =
  'Write the scene opening prose following the authoritative context and instructions.';

export async function runOpeningPhase({
  runEphemeralInference,
  trace,
  api,
  sceneAgent,
  sceneSessionId,
  hgSessionId,
  hgSceneId,
  openingInferenceId,
  mockOpeningResponses,
  modelProfile,
  maxAttempts = 2,
}) {
  const scope = {
    hgSessionId,
    hgSceneId,
    hgRoundId: 'opening-bootstrap',
    sceneSessionId,
  };

  trace.emit(sceneAgent.session, 'hg/opening-started', scope, {
    inference_id: openingInferenceId,
    role: 'opening',
  });

  let lastError = null;
  let manifestId = null;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const inferenceId =
      attempt === 0 ? openingInferenceId : `${openingInferenceId}-retry-${attempt}`;
    try {
      const manifest = await api.prepareOpeningContext({
        hg_session_id: hgSessionId,
        inference_id: inferenceId,
      });
      manifestId = String(manifest.manifest_id);
      const mockFallback =
        modelProfile?.kind === 'mock'
          ? ['Rain drums against the windows as the scene begins.']
          : [];
      const openingRun = await runEphemeralInference({
        inferenceId,
        prompt: OPENING_PROMPT,
        manifest,
        mockResponses: mockOpeningResponses?.length
          ? mockOpeningResponses
          : mockFallback,
        modelProfile,
      });

      if (openingRun.failed) {
        throw new Error(openingRun.failure?.message ?? 'opening provider inference failed');
      }

      const presentationText = openingRun.raw.trim();
      if (!presentationText) {
        throw new Error('opening produced empty presentation output');
      }

      trace.emit(sceneAgent.session, 'hg/opening-completed', scope, {
        inference_id: inferenceId,
        opening_inference_session_id: openingRun.inferenceSessionId,
        role: 'opening',
        manifest_id: manifestId,
        presentation_text: presentationText,
        attempt_index: attempt,
        inference_trace: openingRun.trace,
      });

      return {
        presentation_rendered: true,
        presentation_text: presentationText,
        presentation_failed: false,
        opening_inference_session_id: openingRun.inferenceSessionId,
        opening_manifest_id: manifestId,
        opening_inference_trace: openingRun.trace,
        inference_id: inferenceId,
      };
    } catch (error) {
      lastError = error;
    }
  }

  trace.emit(sceneAgent.session, 'hg/opening-failed', scope, {
    inference_id: openingInferenceId,
    role: 'opening',
    manifest_id: manifestId,
    reason: String(lastError?.message ?? lastError),
    presentation_failure_class: 'runtime_render',
    canon_preserved: true,
  });

  return {
    presentation_rendered: false,
    presentation_text: null,
    presentation_failed: true,
    presentation_failure_reason: String(lastError?.message ?? lastError),
    opening_manifest_id: manifestId,
  };
}

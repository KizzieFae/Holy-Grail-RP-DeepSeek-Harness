import {
  PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
  buildPlotCognitionUpdatePrompt,
  manifestFromPlotCognitionUpdatePrepare,
  parsePlotCognitionUpdateInference,
} from './plot-cognition-update-envelope.mjs';

/**
 * DSH-side Plot Cognition update/replan semantic substrate (#63).
 */
export async function runPlotCognitionUpdateGeneration({
  domainApi,
  hgSceneId,
  inferenceId,
  runEphemeralInference,
  mockResponse = null,
  modelProfile = null,
  evidenceContextBase = null,
  manifestId = null,
}) {
  const prepareResponse = await domainApi.preparePlotCognitionUpdate({
    hg_scene_id: hgSceneId,
    manifest_id: manifestId ?? `manifest-plot-update-${inferenceId}`,
  });
  if (!prepareResponse?.accepted) {
    return {
      ok: false,
      stage: 'prepare',
      prepareResponse,
      inferRun: null,
      parsed: null,
      finalizeResponse: null,
    };
  }

  const resolvedMock = typeof mockResponse === 'function'
    ? mockResponse(prepareResponse)
    : mockResponse;

  const updateInferenceId = `${inferenceId}-plot-update`;
  const inferRun = await runEphemeralInference({
    inferenceId: updateInferenceId,
    prompt: buildPlotCognitionUpdatePrompt(),
    manifest: manifestFromPlotCognitionUpdatePrepare(prepareResponse),
    mockResponses: resolvedMock ? [resolvedMock] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
      inferenceId: updateInferenceId,
      inferenceKind: 'plot_cognition_update',
      schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
    },
  });

  if (inferRun.failed) {
    return {
      ok: false,
      stage: 'inference',
      inferenceError: inferRun.failure ?? 'inference_failed',
      prepareResponse,
      inferRun,
      parsed: null,
      finalizeResponse: null,
    };
  }

  const parsed = parsePlotCognitionUpdateInference(inferRun.raw, prepareResponse);
  if (!parsed.ok || !parsed.result) {
    return {
      ok: false,
      stage: 'parsed',
      inferenceError: parsed.error ?? 'malformed_update_inference',
      prepareResponse,
      inferRun,
      parsed,
      finalizeResponse: null,
    };
  }

  const finalizeResponse = await domainApi.finalizePlotCognitionUpdate({
    hg_scene_id: hgSceneId,
    proposal: parsed.result.update_proposal,
    evaluation: parsed.result.update_evaluation,
    replan_proposal: parsed.result.replan_proposal,
    replan_evaluation: parsed.result.replan_evaluation,
  });

  return {
    ok: finalizeResponse?.accepted === true,
    stage: 'finalized',
    prepareResponse,
    inferRun,
    parsed,
    finalizeResponse,
    inferenceEvidenceId: inferRun.evidenceId ?? null,
  };
}

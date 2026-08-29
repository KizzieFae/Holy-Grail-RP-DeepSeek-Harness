import {
  PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
  buildPlotCognitionUpdateCorrectionPrompt,
  buildPlotCognitionUpdatePrompt,
  manifestFromPlotCognitionUpdatePrepare,
  parsePlotCognitionUpdateInference,
} from './plot-cognition-update-envelope.mjs';
import { runInferenceWithContractCorrection } from './contract-correction-substrate.mjs';

/**
 * DSH-side Plot Cognition update/replan semantic substrate (#63).
 * Bounded contract correction (#65): max 1 correction per update inference.
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
      inferRuns: [],
      parsed: null,
      finalizeResponse: null,
      contractLineage: null,
    };
  }

  const resolvedMock = typeof mockResponse === 'function'
    ? mockResponse(prepareResponse)
    : mockResponse;
  const mockList = resolvedMock
    ? (Array.isArray(resolvedMock) ? resolvedMock : [resolvedMock])
    : [];

  const updateInferenceId = `${inferenceId}-plot-update`;
  const manifest = manifestFromPlotCognitionUpdatePrepare(prepareResponse);

  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference,
    primaryInferenceId: updateInferenceId,
    primaryInferenceKind: 'plot_cognition_update',
    correctionInferenceKind: 'plot_cognition_update_contract_correction',
    buildPrimaryPrompt: () => buildPlotCognitionUpdatePrompt(prepareResponse),
    buildCorrectionPrompt: buildPlotCognitionUpdateCorrectionPrompt,
    parseFn: parsePlotCognitionUpdateInference,
    parseContext: prepareResponse,
    manifest,
    mockResponses: mockList,
    modelProfile,
    evidenceContextBase: {
      ...evidenceContextBase,
      schema: PLOT_COGNITION_UPDATE_INFERENCE_SCHEMA,
    },
    maxCorrections: 1,
  });

  const inferRun = inference.inferRun;
  const inferRuns = inference.inferRuns ?? (inferRun ? [inferRun] : []);

  if (!inference.ok) {
    return {
      ok: false,
      stage: inference.stage ?? 'parsed',
      inferenceError: inference.structuralError ?? inference.parsed?.error ?? 'malformed_update_inference',
      prepareResponse,
      inferRun,
      inferRuns,
      parsed: inference.parsed,
      finalizeResponse: null,
      contractLineage: inference.lineage ?? null,
      correctionUsed: inference.correctionUsed === true,
    };
  }

  const finalizeResponse = await domainApi.finalizePlotCognitionUpdate({
    hg_scene_id: hgSceneId,
    proposal: inference.parsed.result.update_proposal,
    evaluation: inference.parsed.result.update_evaluation,
    replan_proposal: inference.parsed.result.replan_proposal,
    replan_evaluation: inference.parsed.result.replan_evaluation,
  });

  return {
    ok: finalizeResponse?.accepted === true,
    stage: 'finalized',
    prepareResponse,
    inferRun,
    inferRuns,
    parsed: inference.parsed,
    finalizeResponse,
    inferenceEvidenceId: inferRun?.evidenceId ?? null,
    contractLineage: inference.lineage ?? null,
    correctionUsed: inference.correctionUsed === true,
  };
}

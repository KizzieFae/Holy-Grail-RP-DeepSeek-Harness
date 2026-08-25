import {
  LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  buildLibrarianMediationPrompt,
  manifestFromLibrarianPrepareResponse,
  parseLibrarianMediationResult,
} from './librarian-mediation-envelope.mjs';

/**
 * DSH-side Librarian contextual mediation substrate (#34 S2a remediation).
 * Host prepares catalog/manifest; DSH performs inference; Host validates/finalizes.
 */
export async function runLibrarianMediation({
  domainApi,
  hgSceneId,
  inferenceId,
  knowledgeAccessRequest,
  runEphemeralInference,
  mockResponse = null,
  modelProfile = null,
  allowDeterministicFallback = true,
  evidenceContextBase = null,
}) {
  const prepareResponse = await domainApi.prepareLibrarianMediationContext({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    knowledge_access_request: knowledgeAccessRequest,
  });
  const catalogIds = new Set(
    (prepareResponse.mediation_catalog ?? []).map((item) => String(item.source_id)),
  );
  const manifest = manifestFromLibrarianPrepareResponse(prepareResponse);
  const mediationInferenceId = `${inferenceId}-librarian-mediation`;

  const inferRun = await runEphemeralInference({
    inferenceId: mediationInferenceId,
    prompt: buildLibrarianMediationPrompt({ schema: LIBRARIAN_MEDIATION_RESULT_SCHEMA }),
    manifest,
    mockResponses: mockResponse ? [mockResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
      role: 'librarian',
      requestId: prepareResponse.request_id,
      mediationPhase: 'contextual_semantic',
    },
  });

  if (inferRun.failed) {
    const bundle = await domainApi.finalizeLibrarianMediation({
      hg_scene_id: hgSceneId,
      inference_id: inferenceId,
      knowledge_access_request: knowledgeAccessRequest,
      mediation_result: null,
      allow_deterministic_fallback: allowDeterministicFallback,
    });
    return {
      ok: false,
      stage: 'inference',
      inferenceError: inferRun.failure ?? 'inference_failed',
      prepareResponse,
      inferRun,
      parsed: null,
      bundle,
    };
  }

  const parsed = parseLibrarianMediationResult(inferRun.raw, catalogIds);
  const bundle = await domainApi.finalizeLibrarianMediation({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    knowledge_access_request: knowledgeAccessRequest,
    mediation_result: parsed.ok ? parsed.result : null,
    allow_deterministic_fallback: allowDeterministicFallback,
  });

  return {
    ok: parsed.ok,
    stage: parsed.ok ? 'finalized' : 'parse_or_host_validation',
    inferenceError: parsed.ok ? null : parsed.error,
    prepareResponse,
    inferRun,
    parsed: parsed.ok ? parsed.result : null,
    bundle,
  };
}

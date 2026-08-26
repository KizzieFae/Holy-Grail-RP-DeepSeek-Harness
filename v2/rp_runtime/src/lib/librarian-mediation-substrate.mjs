import {
  LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  buildLibrarianMediationPrompt,
  manifestFromLibrarianPrepareResponse,
  parseLibrarianMediationResult,
} from './librarian-mediation-envelope.mjs';
import { buildLibrarianMediationDecisionPatch } from './execution-evidence/ni-evidence.mjs';

function patchMediationEvidence({
  recorder,
  hgSessionId,
  evidenceId,
  prepareResponse,
  parsedResult,
  bundle,
  upstreamEvidenceId = null,
  upstreamAssociationKey = 'orientation_evidence_id',
}) {
  if (!recorder?.isEnabled?.() || !hgSessionId || !evidenceId) return;
  const hostValidation = bundle?.audit?.host_validation ?? {};
  const patch = buildLibrarianMediationDecisionPatch({
    prepareResponse,
    parsedResult: parsedResult?.ok ? parsedResult.result : null,
    bundle,
    hostAccepted: Boolean(hostValidation.accepted ?? parsedResult?.ok),
    hostReason: hostValidation.reason ?? null,
    hostRejectionCodes: hostValidation.rejection_codes ?? [],
    mediationMode: bundle?.mediation_mode ?? null,
  });
  recorder.patchDecision(evidenceId, hgSessionId, patch);
  if (upstreamEvidenceId) {
    recorder.linkNiAssociation(hgSessionId, upstreamEvidenceId, evidenceId, {
      leftKey: 'mediation_evidence_id',
      rightKey: upstreamAssociationKey,
    });
  }
}

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
  recorder = null,
  hgSessionId = null,
  upstreamEvidenceId = null,
  upstreamAssociationKey = 'orientation_evidence_id',
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
      inferenceId: mediationInferenceId,
      parentInferenceId: evidenceContextBase?.parentInferenceId ?? inferenceId,
      inferenceKind: 'librarian_mediation',
      niForensics: true,
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
    patchMediationEvidence({
      recorder,
      hgSessionId,
      evidenceId: inferRun.evidenceId,
      prepareResponse,
      parsedResult: null,
      bundle,
      upstreamEvidenceId,
      upstreamAssociationKey,
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

  patchMediationEvidence({
    recorder,
    hgSessionId,
    evidenceId: inferRun.evidenceId,
    prepareResponse,
    parsedResult: parsed,
    bundle,
    upstreamEvidenceId,
    upstreamAssociationKey,
  });

  return {
    ok: parsed.ok,
    stage: parsed.ok ? 'finalized' : 'parse_or_host_validation',
    inferenceError: parsed.ok ? null : parsed.error,
    prepareResponse,
    inferRun,
    parsed: parsed.ok ? parsed.result : null,
    bundle,
    mediationEvidenceId: inferRun.evidenceId ?? null,
  };
}

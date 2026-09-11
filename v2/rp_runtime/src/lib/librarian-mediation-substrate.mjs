import { runInferenceWithContractCorrection } from './contract-correction-substrate.mjs';
import {
  LIBRARIAN_MEDIATION_CORRECTION_KIND,
  LIBRARIAN_MEDIATION_RESULT_SCHEMA,
  buildLibrarianMediationCorrectionPrompt,
  buildLibrarianMediationPrompt,
  manifestFromLibrarianPrepareResponse,
  parseLibrarianMediationResult,
} from './librarian-mediation-envelope.mjs';
import { buildLibrarianMediationDecisionPatch } from './execution-evidence/ni-evidence.mjs';

function summarizeContractLineage(lineage) {
  if (!lineage) return null;
  return {
    correction_used: lineage.correction_used === true,
    primary_inference_id: lineage.primary?.inference_id ?? null,
    primary_evidence_id: lineage.primary?.evidence_id ?? null,
    primary_parse_error: lineage.primary?.parse_error ?? null,
    correction_inference_id: lineage.correction?.inference_id ?? null,
    correction_evidence_id: lineage.correction?.evidence_id ?? null,
    correction_parse_error: lineage.correction?.parse_error ?? null,
  };
}

function countLooseSelectedItems(raw) {
  if (!raw) return null;
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.selected_items)) return null;
    return parsed.selected_items.length;
  } catch {
    return null;
  }
}

function patchMediationEvidence({
  recorder,
  hgSessionId,
  evidenceId,
  prepareResponse,
  parsedResult,
  bundle,
  hostAccepted,
  hostReason = null,
  hostRejectionCodes = [],
  mediationMode = null,
  contractLineage = null,
  structuralParseError = null,
  mediationGenerationStage = null,
  primaryRawSelectedCount = null,
  upstreamEvidenceId = null,
  upstreamAssociationKey = 'orientation_evidence_id',
}) {
  if (!recorder?.isEnabled?.() || !hgSessionId || !evidenceId) return;
  const hostValidation = bundle?.audit?.host_validation ?? {};
  const patch = buildLibrarianMediationDecisionPatch({
    prepareResponse,
    parsedResult: parsedResult?.ok ? parsedResult.result : null,
    bundle,
    hostAccepted: hostAccepted ?? Boolean(hostValidation.accepted ?? parsedResult?.ok),
    hostReason: hostReason ?? hostValidation.reason ?? null,
    hostRejectionCodes: hostRejectionCodes.length
      ? hostRejectionCodes
      : (hostValidation.rejection_codes ?? []),
    mediationMode: mediationMode ?? bundle?.mediation_mode ?? null,
    contractLineage,
    structuralParseError,
    mediationGenerationStage,
    primaryRawSelectedCount,
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
 * DSH-side Librarian contextual mediation substrate (#34 S2a remediation, #169 contract correction).
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
  const sampleSourceId = [...catalogIds][0] ?? 'lmi:cand:example-source';
  const parseContext = { catalogIds, sampleSourceId };
  const manifest = manifestFromLibrarianPrepareResponse(prepareResponse);
  const mediationInferenceId = `${inferenceId}-librarian-mediation`;
  const mockList = mockResponse
    ? (Array.isArray(mockResponse) ? mockResponse : [mockResponse])
    : [];

  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference,
    primaryInferenceId: mediationInferenceId,
    primaryInferenceKind: 'librarian_mediation',
    correctionInferenceKind: LIBRARIAN_MEDIATION_CORRECTION_KIND,
    buildPrimaryPrompt: () => buildLibrarianMediationPrompt({ sampleSourceId }),
    buildCorrectionPrompt: buildLibrarianMediationCorrectionPrompt,
    parseFn: (raw, ctx) => parseLibrarianMediationResult(raw, ctx.catalogIds),
    parseContext,
    manifest,
    mockResponses: mockList,
    modelProfile,
    evidenceContextBase: {
      ...evidenceContextBase,
      role: 'librarian',
      parentInferenceId: evidenceContextBase?.parentInferenceId ?? inferenceId,
      niForensics: true,
      requestId: prepareResponse.request_id,
      mediationPhase: 'contextual_semantic',
    },
    maxCorrections: 1,
  });

  const inferRuns = inference.inferRuns ?? (inference.inferRun ? [inference.inferRun] : []);
  const primaryRun = inferRuns[0] ?? null;
  const finalRun = inference.inferRun ?? primaryRun;
  const contractLineage = summarizeContractLineage(inference.lineage);
  const structuralError = inference.structuralError
    ?? inference.lineage?.primary?.parse_error
    ?? inference.parsed?.error
    ?? null;
  const primaryRawSelectedCount = countLooseSelectedItems(primaryRun?.raw);

  if (inference.stage === 'inference' || primaryRun?.failed) {
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
      evidenceId: primaryRun?.evidenceId ?? finalRun?.evidenceId,
      prepareResponse,
      parsedResult: null,
      bundle,
      contractLineage,
      structuralParseError: primaryRun?.failure ?? 'inference_failed',
      mediationGenerationStage: 'primary',
      primaryRawSelectedCount,
      upstreamEvidenceId,
      upstreamAssociationKey,
    });
    return {
      ok: false,
      stage: 'inference',
      inferenceError: primaryRun?.failure ?? 'inference_failed',
      prepareResponse,
      inferRun: finalRun,
      inferRuns,
      parsed: null,
      bundle,
      contractLineage,
      mediationEvidenceId: primaryRun?.evidenceId ?? null,
    };
  }

  const parsed = inference.parsed?.ok ? inference.parsed : inference.parsed;
  const bundle = await domainApi.finalizeLibrarianMediation({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    knowledge_access_request: knowledgeAccessRequest,
    mediation_result: parsed?.ok ? parsed.result : null,
    allow_deterministic_fallback: allowDeterministicFallback,
  });

  const hostValidation = bundle?.audit?.host_validation ?? {};

  if (contractLineage?.correction_used) {
    patchMediationEvidence({
      recorder,
      hgSessionId,
      evidenceId: finalRun?.evidenceId,
      prepareResponse,
      parsedResult: parsed,
      bundle,
      hostAccepted: Boolean(hostValidation.accepted),
      hostReason: hostValidation.reason ?? null,
      hostRejectionCodes: hostValidation.rejection_codes ?? [],
      contractLineage,
      mediationGenerationStage: 'contract_correction',
      primaryRawSelectedCount,
      upstreamEvidenceId,
      upstreamAssociationKey,
    });
    if (primaryRun?.evidenceId) {
      patchMediationEvidence({
        recorder,
        hgSessionId,
        evidenceId: primaryRun.evidenceId,
        prepareResponse,
        parsedResult: null,
        bundle,
        hostAccepted: false,
        contractLineage,
        structuralParseError: structuralError,
        mediationGenerationStage: 'primary',
        primaryRawSelectedCount,
        upstreamEvidenceId,
        upstreamAssociationKey,
      });
    }
  } else {
    patchMediationEvidence({
      recorder,
      hgSessionId,
      evidenceId: primaryRun?.evidenceId ?? finalRun?.evidenceId,
      prepareResponse,
      parsedResult: parsed,
      bundle,
      hostAccepted: Boolean(hostValidation.accepted),
      hostReason: hostValidation.reason ?? null,
      hostRejectionCodes: hostValidation.rejection_codes ?? [],
      contractLineage,
      structuralParseError: parsed?.ok ? null : structuralError,
      mediationGenerationStage: 'primary',
      primaryRawSelectedCount,
      upstreamEvidenceId,
      upstreamAssociationKey,
    });
  }

  const structurallyValid = Boolean(parsed?.ok);
  return {
    ok: structurallyValid,
    stage: structurallyValid ? 'finalized' : 'parse_or_host_validation',
    inferenceError: structurallyValid ? null : (structuralError ?? parsed?.error ?? 'structural_parse_failed'),
    prepareResponse,
    inferRun: finalRun,
    inferRuns,
    parsed: parsed?.ok ? parsed.result : null,
    bundle,
    contractLineage,
    mediationEvidenceId: finalRun?.evidenceId ?? primaryRun?.evidenceId ?? null,
    structuralParseSucceeded: structurallyValid,
    hostAccepted: Boolean(hostValidation.accepted),
  };
}

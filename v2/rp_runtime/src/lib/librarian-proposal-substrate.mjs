import {
  LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
  buildLibrarianProposalPrompt,
  manifestFromLibrarianProposalPrepareResponse,
  parseLibrarianProposalResult,
} from './librarian-proposal-envelope.mjs';

/**
 * DSH-side Librarian post-commit proposal substrate (#34 S4a).
 * Host prepares evidence catalog/manifest; DSH performs inference; Host validates/finalizes.
 */
export async function runLibrarianProposalGeneration({
  domainApi,
  hgSceneId,
  inferenceId,
  proposalContextRequest,
  runEphemeralInference,
  mockResponse = null,
  modelProfile = null,
  evidenceContextBase = null,
}) {
  const prepareResponse = await domainApi.prepareLibrarianProposalContext({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    proposal_context_request: proposalContextRequest,
  });
  const catalogIds = new Set(
    (prepareResponse.evidence_catalog ?? []).map((item) => String(item.anchor_id)),
  );
  const manifest = manifestFromLibrarianProposalPrepareResponse(prepareResponse);
  const proposalInferenceId = `${inferenceId}-librarian-proposal`;

  const inferRun = await runEphemeralInference({
    inferenceId: proposalInferenceId,
    prompt: buildLibrarianProposalPrompt({ schema: LIBRARIAN_PROPOSAL_RESULT_SCHEMA }),
    manifest,
    mockResponses: mockResponse ? [mockResponse] : [],
    modelProfile,
    evidenceContext: {
      ...evidenceContextBase,
      role: 'librarian',
      requestId: prepareResponse.request_id,
      proposalPhase: 'post_commit_semantic',
    },
  });

  if (inferRun.failed) {
    const batch = await domainApi.finalizeLibrarianProposals({
      hg_scene_id: hgSceneId,
      inference_id: inferenceId,
      proposal_context_request: proposalContextRequest,
      proposal_result: null,
      evidence_catalog: prepareResponse.evidence_catalog,
    });
    return {
      ok: false,
      stage: 'inference',
      inferenceError: inferRun.failure ?? 'inference_failed',
      prepareResponse,
      inferRun,
      parsed: null,
      batch,
    };
  }

  const parsed = parseLibrarianProposalResult(inferRun.raw, catalogIds);
  const batch = await domainApi.finalizeLibrarianProposals({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    proposal_context_request: proposalContextRequest,
    proposal_result: parsed.ok ? parsed.result : null,
    evidence_catalog: prepareResponse.evidence_catalog,
  });

  return {
    ok: parsed.ok,
    stage: parsed.ok ? 'finalized' : 'parse_or_host_validation',
    inferenceError: parsed.ok ? null : parsed.error,
    prepareResponse,
    inferRun,
    parsed: parsed.ok ? parsed.result : null,
    batch,
  };
}

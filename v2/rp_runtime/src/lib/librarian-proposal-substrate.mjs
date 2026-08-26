import crypto from 'node:crypto';

import {
  LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
  buildLibrarianProposalPrompt,
  manifestFromLibrarianProposalPrepareResponse,
  parseLibrarianProposalResult,
} from './librarian-proposal-envelope.mjs';
import { buildLibrarianProposalDecisionPatch } from './execution-evidence/ni-evidence.mjs';

function proposalContentHash(raw) {
  if (!raw) return null;
  return crypto.createHash('sha256').update(String(raw)).digest('hex');
}

/**
 * DSH-side Librarian post-commit proposal substrate (#34 S4a).
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
  recorder = null,
  hgSessionId = evidenceContextBase?.hgSessionId ?? null,
  characterMoveEvidenceId = null,
}) {
  const prepareResponse = await domainApi.prepareLibrarianProposalContext({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    proposal_context_request: proposalContextRequest,
  });

  if (prepareResponse.skipped === true) {
    return {
      ok: true,
      skipped: true,
      stage: 'already_terminal',
      inferenceError: null,
      prepareResponse,
      inferRun: null,
      parsed: null,
      batch: {
        skipped: true,
        orchestration_status: prepareResponse.orchestration_status ?? 'already_terminal',
        domain_commit_id: prepareResponse.domain_commit_id ?? proposalContextRequest.domain_commit_id,
        existing_audit: prepareResponse.existing_audit ?? null,
        persisted: true,
      },
    };
  }

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
      inferenceId: proposalInferenceId,
      parentInferenceId: inferenceId,
      inferenceKind: 'librarian_proposal',
      niForensics: true,
      requestId: prepareResponse.request_id,
      proposalPhase: 'post_commit_semantic',
      domainCommitId: proposalContextRequest.domain_commit_id,
    },
  });

  const patchProposalEvidence = (batch) => {
    if (!recorder?.isEnabled?.() || !inferRun?.evidenceId || !hgSessionId) return;
    recorder.patchDecision(
      inferRun.evidenceId,
      hgSessionId,
      buildLibrarianProposalDecisionPatch({
        batch,
        proposalContentHash: proposalContentHash(inferRun.raw),
        characterMoveEvidenceId,
      }),
    );
    if (characterMoveEvidenceId) {
      recorder.linkNiAssociation(hgSessionId, characterMoveEvidenceId, inferRun.evidenceId, {
        leftKey: 'proposal_evidence_id',
        rightKey: 'character_move_evidence_id',
      });
    }
  };

  if (inferRun.failed) {
    const batch = await domainApi.finalizeLibrarianProposals({
      hg_scene_id: hgSceneId,
      inference_id: inferenceId,
      proposal_context_request: proposalContextRequest,
      proposal_result: null,
      evidence_catalog: prepareResponse.evidence_catalog,
    });
    patchProposalEvidence(batch);
    return {
      ok: false,
      stage: 'inference',
      inferenceError: inferRun.failure ?? 'inference_failed',
      prepareResponse,
      inferRun,
      parsed: null,
      batch,
      proposalEvidenceId: inferRun.evidenceId ?? null,
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
  patchProposalEvidence(batch);

  return {
    ok: parsed.ok,
    stage: parsed.ok ? 'finalized' : 'parse_or_host_validation',
    inferenceError: parsed.ok ? null : parsed.error,
    prepareResponse,
    inferRun,
    parsed: parsed.ok ? parsed.result : null,
    batch,
    proposalEvidenceId: inferRun.evidenceId ?? null,
    proposalContentHash: proposalContentHash(inferRun.raw),
  };
}

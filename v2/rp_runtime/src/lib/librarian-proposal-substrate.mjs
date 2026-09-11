import crypto from 'node:crypto';

import { modelProfileForInferenceKind } from '../application/application-settings.mjs';
import { runInferenceWithContractCorrection } from './contract-correction-substrate.mjs';
import {
  LIBRARIAN_PROPOSAL_RESULT_SCHEMA,
  buildLibrarianProposalCorrectionPrompt,
  buildLibrarianProposalPrompt,
  manifestFromLibrarianProposalPrepareResponse,
  parseLibrarianProposalResult,
} from './librarian-proposal-envelope.mjs';
import { buildPostCommitSemanticDecisionPatch } from './execution-evidence/ni-evidence.mjs';

function proposalContentHash(raw) {
  if (!raw) return null;
  return crypto.createHash('sha256').update(String(raw)).digest('hex');
}

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

function resolveProposalGenerationFailure({ inferenceFailed, structuralParseFailed }) {
  if (inferenceFailed) return 'provider_inference_failed';
  if (structuralParseFailed) return 'structural_parse_failed';
  return null;
}

/**
 * DSH-side Librarian post-commit proposal substrate (#34 S4a, #72 contract correction).
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
      inferRuns: [],
      parsed: null,
      contractLineage: null,
      batch: {
        skipped: true,
        orchestration_status: prepareResponse.orchestration_status ?? 'already_terminal',
        domain_commit_id: prepareResponse.domain_commit_id ?? proposalContextRequest.domain_commit_id,
        existing_audit: prepareResponse.existing_audit ?? null,
        persisted: true,
      },
    };
  }

  if (prepareResponse.inference_required === false) {
    const skipReason = prepareResponse.eligibility_outcome ?? 'no_eligible_active_issues';
    const batch = await domainApi.finalizeLibrarianProposals({
      hg_scene_id: hgSceneId,
      inference_id: inferenceId,
      proposal_context_request: proposalContextRequest,
      proposal_result: null,
      evidence_catalog: prepareResponse.evidence_catalog,
      proposal_generation_skip_reason: skipReason,
    });
    const dispositionEvidenceId = recorder?.recordPostCommitSemanticDisposition?.({
      hgSessionId,
      hgSceneId,
      hgRoundId: evidenceContextBase?.hgRoundId ?? proposalContextRequest.hg_round_id,
      domainCommitId: proposalContextRequest.domain_commit_id,
      continuityTurnIndex: evidenceContextBase?.continuityTurnIndex ?? proposalContextRequest.turn_index,
      postCommitSemanticInferenceId: inferenceId,
      batch,
      eligibilityOutcome: skipReason,
      degradationMode: batch?.degradation_mode ?? 'eligibility_skipped',
      orchestrationStatus: batch?.orchestration_status ?? 'finalized',
      effectiveConfigurationEpochId: evidenceContextBase?.effectiveConfigurationEpochId ?? null,
    }) ?? null;
    if (dispositionEvidenceId && characterMoveEvidenceId) {
      recorder?.linkNiAssociation?.(hgSessionId, characterMoveEvidenceId, dispositionEvidenceId, {
        leftKey: 'semantic_disposition_evidence_id',
        rightKey: 'character_move_evidence_id',
      });
    }
    return {
      ok: true,
      skipped: false,
      stage: 'eligibility_skipped',
      inferenceError: null,
      prepareResponse,
      inferRun: null,
      inferRuns: [],
      parsed: null,
      contractLineage: null,
      batch,
      proposalEvidenceId: null,
      dispositionEvidenceId,
      eligibilitySkipped: true,
    };
  }

  const inferenceKind = prepareResponse.inference_kind ?? 'storyteller_post_commit_issue_pressure';
  const correctionKind = `${inferenceKind}_contract_correction`;

  const catalogIds = new Set(
    (prepareResponse.evidence_catalog ?? []).map((item) => String(item.anchor_id)),
  );
  const sampleAnchorId = [...catalogIds][0] ?? `committed_move:${proposalContextRequest.domain_commit_id}`;
  const parseContext = {
    catalogIds,
    sampleAnchorId,
    domainCommitId: proposalContextRequest.domain_commit_id,
  };
  const manifest = manifestFromLibrarianProposalPrepareResponse(prepareResponse);
  const proposalInferenceId = `${inferenceId}-post-commit-semantic`;
  const mockList = mockResponse
    ? (Array.isArray(mockResponse) ? mockResponse : [mockResponse])
    : [];

  const resolvedModelProfile = modelProfileForInferenceKind(
    modelProfile,
    inferenceKind,
  );

  const inference = await runInferenceWithContractCorrection({
    runEphemeralInference,
    primaryInferenceId: proposalInferenceId,
    primaryInferenceKind: inferenceKind,
    correctionInferenceKind: correctionKind,
    buildPrimaryPrompt: () => buildLibrarianProposalPrompt(parseContext),
    buildCorrectionPrompt: buildLibrarianProposalCorrectionPrompt,
    parseFn: (raw, ctx) => parseLibrarianProposalResult(raw, ctx.catalogIds),
    parseContext,
    manifest,
    mockResponses: mockList,
    modelProfile: resolvedModelProfile,
    evidenceContextBase: {
      ...evidenceContextBase,
      role: 'storyteller',
      parentInferenceId: inferenceId,
      niForensics: true,
      requestId: prepareResponse.request_id,
      proposalPhase: 'post_commit_issue_pressure',
      domainCommitId: proposalContextRequest.domain_commit_id,
      semanticProducerRole: 'storyteller',
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

  const patchProposalEvidence = (batch, { stage = 'primary' } = {}) => {
    if (!recorder?.isEnabled?.() || !hgSessionId) return;
    const targetRun = stage === 'contract_correction'
      ? (inferRuns[1] ?? finalRun)
      : (primaryRun ?? finalRun);
    if (!targetRun?.evidenceId) return;
    recorder.patchDecision(
      targetRun.evidenceId,
      hgSessionId,
      buildPostCommitSemanticDecisionPatch({
        batch,
        proposalContentHash: proposalContentHash(targetRun.raw),
        characterMoveEvidenceId,
        contractLineage,
        structuralParseError: stage === 'primary' ? structuralError : null,
        proposalGenerationStage: stage,
        proposalGenerationFailure: batch?.proposal_generation_failure ?? null,
      }),
    );
    if (characterMoveEvidenceId && stage === 'primary') {
      recorder.linkNiAssociation(hgSessionId, characterMoveEvidenceId, targetRun.evidenceId, {
        leftKey: 'proposal_evidence_id',
        rightKey: 'character_move_evidence_id',
      });
    }
  };

  if (inference.stage === 'inference' || primaryRun?.failed) {
    const batch = await domainApi.finalizeLibrarianProposals({
      hg_scene_id: hgSceneId,
      inference_id: inferenceId,
      proposal_context_request: proposalContextRequest,
      proposal_result: null,
      evidence_catalog: prepareResponse.evidence_catalog,
      proposal_generation_failure: 'provider_inference_failed',
    });
    patchProposalEvidence(batch, { stage: 'primary' });
    return {
      ok: false,
      stage: 'inference',
      inferenceError: primaryRun?.failure ?? 'inference_failed',
      prepareResponse,
      inferRun: finalRun,
      inferRuns,
      parsed: null,
      contractLineage,
      batch,
      proposalEvidenceId: primaryRun?.evidenceId ?? null,
      proposalGenerationFailure: 'provider_inference_failed',
    };
  }

  const parsed = inference.parsed?.ok ? inference.parsed.result : null;
  const structuralParseFailed = !parsed;
  const batch = await domainApi.finalizeLibrarianProposals({
    hg_scene_id: hgSceneId,
    inference_id: inferenceId,
    proposal_context_request: proposalContextRequest,
    proposal_result: parsed,
    evidence_catalog: prepareResponse.evidence_catalog,
    proposal_generation_failure: resolveProposalGenerationFailure({
      inferenceFailed: false,
      structuralParseFailed,
    }),
  });

  if (contractLineage?.correction_used) {
    patchProposalEvidence(batch, { stage: 'contract_correction' });
    if (primaryRun?.evidenceId) {
      recorder?.patchDecision?.(
        primaryRun.evidenceId,
        hgSessionId,
        buildPostCommitSemanticDecisionPatch({
          proposalContentHash: proposalContentHash(primaryRun.raw),
          characterMoveEvidenceId,
          contractLineage,
          structuralParseError: structuralError,
          proposalGenerationStage: 'primary',
          proposalGenerationFailure: structuralParseFailed ? 'structural_parse_failed' : null,
        }),
      );
    }
  } else {
    patchProposalEvidence(batch, { stage: 'primary' });
  }

  return {
    ok: Boolean(parsed),
    stage: parsed ? 'finalized' : 'structural_parse_failed',
    inferenceError: parsed ? null : (structuralError ?? 'structural_parse_failed'),
    prepareResponse,
    inferRun: finalRun,
    inferRuns,
    parsed,
    contractLineage,
    batch,
    proposalEvidenceId: finalRun?.evidenceId ?? null,
    proposalContentHash: proposalContentHash(finalRun?.raw),
    proposalGenerationFailure: batch?.proposal_generation_failure ?? null,
    correctionUsed: contractLineage?.correction_used === true,
  };
}

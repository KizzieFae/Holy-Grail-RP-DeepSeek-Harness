import crypto from 'node:crypto';

import { runLibrarianProposalGeneration } from './librarian-proposal-substrate.mjs';

/**
 * Build Host proposal_context_request payload for post-commit S4 (#39).
 */
export function buildPostCommitProposalContextRequest({
  hgSceneId,
  hgRoundId,
  turnIndex,
  domainCommitId,
  librarianInferenceId,
}) {
  return {
    request_id: `lpr-${crypto.randomUUID()}`,
    hg_scene_id: hgSceneId,
    hg_round_id: hgRoundId,
    turn_index: turnIndex,
    domain_commit_id: domainCommitId,
    librarian_inference_id: librarianInferenceId,
    semantic_producer_role: 'storyteller',
    visibility_envelope: {
      viewer_role: 'host_internal',
      authority_ceiling_enforced: 'derived',
    },
  };
}

function batchRequiresPersistence(batch) {
  if (!batch || batch.skipped === true) {
    return false;
  }
  return batch.orchestration_status === 'finalized' || batch.orchestration_status === 'already_terminal';
}

function hasBlockingPersistenceFailure(batch) {
  if (!batchRequiresPersistence(batch)) {
    return false;
  }
  return batch.persisted !== true;
}

/**
 * Post-commit Librarian S4 lifecycle for one successful Character commit (#39).
 * Runs prepare → inference → finalize with trace correlation; does not await Narrator.
 */
export async function runPostCommitLibrarianLifecycle({
  domainApi,
  trace,
  sceneAgent,
  scope,
  hgSceneId,
  hgRoundId,
  characterTurnIndex,
  domainCommitId,
  continuityTurnIndex,
  librarianInferenceId,
  runEphemeralInference,
  mockResponse = null,
  modelProfile = null,
  evidenceContextBase = null,
  delayMs = 0,
  recorder = null,
  characterMoveEvidenceId = null,
}) {
  const correlation = {
    domain_commit_id: domainCommitId,
    continuity_turn_index: continuityTurnIndex,
    character_turn_index: characterTurnIndex,
    librarian_inference_id: librarianInferenceId,
    hg_round_id: hgRoundId,
  };

  trace.emit(sceneAgent.session, 'hg/librarian-proposal-started', scope, correlation);

  if (delayMs > 0) {
    await new Promise((resolve) => {
      setTimeout(resolve, delayMs);
    });
  }

  const proposalContextRequest = buildPostCommitProposalContextRequest({
    hgSceneId,
    hgRoundId,
    turnIndex: continuityTurnIndex,
    domainCommitId,
    librarianInferenceId,
  });

  let generationResult;
  try {
    generationResult = await runLibrarianProposalGeneration({
      domainApi,
      hgSceneId,
      inferenceId: librarianInferenceId,
      proposalContextRequest,
      runEphemeralInference,
      mockResponse,
      modelProfile,
      evidenceContextBase: {
        ...evidenceContextBase,
        domainCommitId,
        continuityTurnIndex,
        characterTurnIndex,
      },
      recorder,
      hgSessionId: evidenceContextBase?.hgSessionId ?? null,
      characterMoveEvidenceId,
    });
  } catch (error) {
    trace.emit(sceneAgent.session, 'hg/librarian-proposal-failed', scope, {
      ...correlation,
      stage: 'orchestration_error',
      error: String(error?.message ?? error ?? 'librarian_orchestration_error'),
    });
    return {
      ok: false,
      terminal: false,
      blockingPersistenceFailure: true,
      stage: 'orchestration_error',
      error: String(error?.message ?? error ?? 'librarian_orchestration_error'),
      generationResult: null,
      batch: null,
    };
  }

  const batch = generationResult.batch ?? {};
  const blockingPersistenceFailure = hasBlockingPersistenceFailure(batch);
  const terminal = generationResult.skipped === true
    || generationResult.stage === 'eligibility_skipped'
    || batch.skipped === true
    || batch.orchestration_status === 'already_terminal'
    || batch.orchestration_status === 'finalized'
    || batch.degradation_mode === 'eligibility_skipped'
    || Boolean(batch.batch_id)
    || Boolean(batch.existing_audit);

  trace.emit(sceneAgent.session, 'hg/librarian-proposal-completed', scope, {
    ...correlation,
    stage: generationResult.stage ?? null,
    ok: generationResult.ok === true,
    skipped: generationResult.skipped === true || batch.skipped === true,
    orchestration_status: batch.orchestration_status ?? generationResult.stage ?? null,
    degradation_mode: batch.degradation_mode ?? batch.audit?.degradation_mode ?? null,
    batch_id: batch.batch_id ?? batch.existing_audit?.librarian_proposal_batch_id ?? null,
    request_id: batch.request_id ?? batch.existing_audit?.request_id ?? null,
    persisted: batch.persisted === true,
    blocking_persistence_failure: blockingPersistenceFailure,
    inference_error: generationResult.inferenceError ?? null,
  });

  return {
    ok: generationResult.ok === true || generationResult.skipped === true || terminal,
    terminal,
    blockingPersistenceFailure,
    stage: generationResult.stage ?? null,
    degradationMode: batch.degradation_mode ?? null,
    generationResult,
    batch,
  };
}

/**
 * Issue #201 LH-0 — live transport seam helpers (projection build, fault injection).
 */
import crypto from 'node:crypto';

import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import {
  buildLh0FinalizedProjection,
  obligationsForConsumer,
  readLh0Store,
  classifyLh0ObligationStates,
  writeLh0Store,
} from './issue201-lh0-persistent-store.mjs';
import {
  projectionSemanticAdequate,
  validateLh0FinalizedProjectionPackage,
} from './issue201-lh0-consumer-evidence.mjs';

export function prepareLh0RoundTransport({
  sessionsDir,
  hgSessionId,
  hgRoundId,
  turnIndex,
  characterId,
  arm,
  faultInjection = null,
  storeOverride = null,
}) {
  const store = storeOverride ?? readLh0Store(sessionsDir, hgSessionId);
  classifyLh0ObligationStates(store, turnIndex);
  if (!storeOverride) {
    writeLh0Store(sessionsDir, hgSessionId, store);
  }

  const directorDue = obligationsForConsumer(store, { turn: turnIndex, consumer: 'director_turn' });
  const characterDue = obligationsForConsumer(store, { turn: turnIndex, consumer: 'character_move' });

  const directorBatchId = `lh0-dir-${hgRoundId}`;
  const characterBatchId = `lh0-char-${hgRoundId}`;

  let directorProjection = buildLh0FinalizedProjection(directorDue, {
    batchId: directorBatchId,
    consumer: 'director_turn',
    hgRoundId,
    turnIndex,
    characterId,
  });
  let characterProjection = buildLh0FinalizedProjection(characterDue, {
    batchId: characterBatchId,
    consumer: 'character_move',
    hgRoundId,
    turnIndex,
    characterId,
  });

  if (faultInjection === 'omit_projection') {
    characterProjection = null;
    directorProjection = null;
  }

  let directorManifestValid = { skipped: true };
  let characterManifestValid = { skipped: true };
  if (directorProjection) {
    directorManifestValid = validateLh0FinalizedProjectionPackage(directorProjection, { consumer: 'director_turn' });
  }
  if (characterProjection) {
    characterManifestValid = validateLh0FinalizedProjectionPackage(characterProjection, { consumer: 'character_move' });
  }

  const omitReceipt = faultInjection === 'omit_receipt';
  const characterPrecomputed = omitReceipt ? null : characterProjection;

  const usePlotProjectionLifecycle = arm === LH0_ARMS.LH_B && !characterPrecomputed;

  return {
    store,
    directorDue,
    characterDue,
    directorProjection,
    characterProjection,
    characterPrecomputed,
    usePlotProjectionLifecycle,
    directorManifestValid,
    characterManifestValid,
    director_receipt_applicable: directorDue.length > 0,
    director_deterministic_fixture: true,
    candidate_only: Boolean(characterProjection || directorProjection),
    projected_finalized: Boolean(characterPrecomputed),
    fault_injection: faultInjection ?? null,
  };
}

export function recordLh0TransportAuditStep(transport, { omitCharacterReceipt = false } = {}) {
  return {
    step: 'lh0_projection_transport',
    director_due_count: transport.directorDue.length,
    character_due_count: transport.characterDue.length,
    director_projection_built: Boolean(transport.directorProjection),
    character_projection_built: Boolean(transport.characterProjection),
    director_manifest_valid: transport.directorManifestValid?.valid === true
      || transport.directorManifestValid?.skipped === true,
    character_manifest_valid: transport.characterManifestValid?.valid === true
      || transport.characterManifestValid?.skipped === true,
    director_receipt_applicable: transport.director_receipt_applicable === true,
    director_deterministic_fixture: transport.director_deterministic_fixture === true,
    director_consumer_receipt: false,
    character_consumer_receipt: false,
    character_precomputed_supplied: Boolean(transport.characterPrecomputed) && !omitCharacterReceipt,
    candidate_only: transport.candidate_only === true,
    projected_finalized: transport.projected_finalized === true && !omitCharacterReceipt,
    semantic_projection_adequate: projectionSemanticAdequate(transport.characterProjection),
    fault_injection: transport.fault_injection,
  };
}

export function buildLh0ConsequenceMarker(obligationIds, { turnIndex, hgRoundId }) {
  return {
    schema: 'issue201_lh0_consequence_marker_v1',
    marker_id: `lh0-cons-${crypto.randomUUID()}`,
    turn_index: turnIndex,
    hg_round_id: hgRoundId,
    obligation_ids: obligationIds,
    recorded_at: new Date().toISOString(),
  };
}

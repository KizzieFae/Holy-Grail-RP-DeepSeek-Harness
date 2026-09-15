/**
 * Issue #201 LH-0 — consumer receipt / use / influence evidence (harness-only).
 */
import { validateBridgeManifest } from '../../src/lib/manifest-validation.mjs';
import {
  evaluateTurnCausalEvidence,
  isBookkeepingOnlySemanticContent,
} from './issue201-lh0-semantic-content.mjs';

export const LH0_OBLIGATION_KNOWLEDGE_PREFIX = 'lh0-obligation:';

export function extractLh0ObligationIdsFromManifest(manifest) {
  const ids = new Set();
  for (const c of manifest?.contributions ?? []) {
    const provId = c?.provenance?.lh0_obligation_id;
    if (provId) ids.add(String(provId));
    for (const kid of c?.knowledge_ids ?? []) {
      const text = String(kid);
      if (text.startsWith(LH0_OBLIGATION_KNOWLEDGE_PREFIX)) {
        ids.add(text.slice(LH0_OBLIGATION_KNOWLEDGE_PREFIX.length));
      }
    }
  }
  return [...ids];
}

export function extractLh0ObligationIdsFromProjection(projection) {
  if (!projection) return [];
  const ids = new Set();
  for (const c of projection.contributions ?? []) {
    const provId = c?.provenance?.lh0_obligation_id;
    if (provId) ids.add(String(provId));
    for (const kid of c?.knowledge_ids ?? []) {
      const text = String(kid);
      if (text.startsWith(LH0_OBLIGATION_KNOWLEDGE_PREFIX)) {
        ids.add(text.slice(LH0_OBLIGATION_KNOWLEDGE_PREFIX.length));
      }
    }
  }
  return [...ids];
}

export function validateLh0FinalizedProjectionPackage(projection, { consumer }) {
  if (!projection) return { valid: true, skipped: true, reason: 'empty_projection' };
  const inferenceKind = consumer === 'director_turn' ? 'director_turn' : 'character_turn';
  const manifest = {
    manifest_id: `lh0-projection-validate-${projection.batch_id}`,
    inference_kind: inferenceKind,
    contributions: projection.contributions ?? [],
  };
  validateBridgeManifest({ manifest, inferenceKind });
  return { valid: true, inference_kind: inferenceKind };
}

export function buildCharacterConsumerEvidence({
  manifest,
  finalizedProjection,
  projectionSupplied,
  obligationIdsExpected = [],
}) {
  const receivedIds = extractLh0ObligationIdsFromManifest(manifest);
  const projectedIds = extractLh0ObligationIdsFromProjection(finalizedProjection);
  const expected = obligationIdsExpected.filter(Boolean);
  const receivedExpected = expected.filter((id) => receivedIds.includes(id));
  const semanticPayloadSamples = (manifest?.contributions ?? [])
    .filter((c) => c?.provenance?.lh0_obligation_id)
    .map((c) => String(c.content ?? ''));
  const semanticReceiptAdequate = semanticPayloadSamples.length > 0
    && semanticPayloadSamples.every((content) => !isBookkeepingOnlySemanticContent(content));
  return {
    projection_supplied: projectionSupplied === true,
    projected_obligation_ids: projectedIds,
    received_obligation_ids: receivedIds,
    expected_obligation_ids: expected,
    received_expected_obligation_ids: receivedExpected,
    consumer_received: expected.length === 0
      ? receivedIds.length > 0
      : receivedExpected.length > 0,
    semantic_payload_samples: semanticPayloadSamples,
    semantic_receipt_adequate: semanticReceiptAdequate,
    contribution_source_kinds: (manifest?.contributions ?? []).map((c) => c.source_kind).filter(Boolean),
  };
}

export function detectObligationUseInText(text, obligationIds, { turnIndex = null, fixture = null } = {}) {
  const causal = evaluateTurnCausalEvidence({
    turnIndex,
    moveText: text,
    presentationText: text,
    receivedObligationIds: obligationIds,
    fixture,
  });
  return causal.influenced_obligation_ids;
}

export function buildTurnConsumerForensics({
  turn,
  arm,
  fixtureObligations = [],
  presentationText = '',
}) {
  const transport = turn.lh0_transport ?? {};
  const charEvidence = transport.character ?? {};
  const directorEvidence = transport.director ?? {};
  const expectedChar = fixtureObligations
    .filter((o) => o.authorized_consumer === 'character_move' && !o.negative_control)
    .map((o) => o.obligation_id);
  const receivedChar = charEvidence.received_obligation_ids ?? [];
  const usedChar = [
    ...detectObligationUseInText(turn.presentation_text, receivedChar),
    ...(charEvidence.referenced_obligation_ids ?? []),
  ];
  const influenced = (charEvidence.decision_influenced_obligation_ids ?? []).length > 0;
  const consequenceIds = (turn.lh0_consequences?.obligation_ids ?? []);
  return {
    arm,
    turn_index: turn.turn_index,
    character: {
      ...charEvidence,
      consumer_used: usedChar.length > 0,
      referenced_obligation_ids: [...new Set(usedChar)],
      decision_influenced: influenced,
    },
    director: directorEvidence,
    projected_finalized: transport.projected_finalized === true,
    candidate_only: transport.candidate_only === true,
    expected_character_obligations: expectedChar,
    consequential_obligation_ids: consequenceIds,
  };
}

export function projectionSemanticAdequate(projection) {
  const samples = (projection?.contributions ?? [])
    .filter((c) => c?.provenance?.lh0_obligation_id)
    .map((c) => String(c.content ?? ''));
  return samples.length > 0 && samples.every((content) => !isBookkeepingOnlySemanticContent(content));
}

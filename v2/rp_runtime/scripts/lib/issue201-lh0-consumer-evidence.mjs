/**
 * Issue #201 LH-0 — consumer receipt / use / influence evidence (harness-only).
 */
import { LIFECYCLE_STATES } from './issue201-lifecycle-states.mjs';
import { validateBridgeManifest } from '../../src/lib/manifest-validation.mjs';

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
    const content = String(c?.content ?? '');
    const match = content.match(/LH0-OBL-[A-Z0-9_-]+/g);
    for (const m of match ?? []) ids.add(m);
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
  return {
    projection_supplied: projectionSupplied === true,
    projected_obligation_ids: projectedIds,
    received_obligation_ids: receivedIds,
    expected_obligation_ids: expected,
    received_expected_obligation_ids: receivedExpected,
    consumer_received: expected.length === 0
      ? receivedIds.length > 0
      : receivedExpected.length > 0,
    contribution_source_kinds: (manifest?.contributions ?? []).map((c) => c.source_kind).filter(Boolean),
  };
}

const OBLIGATION_SEMANTIC_MARKERS = {
  'LH0-OBL-IMMEDIATE': ['curfew', 'weeknight', 'ten', 'evening duty'],
  'LH0-OBL-DEFERRED': ['curfew', 'weeknight', 'ten', 'evening duty'],
  'LH0-OBL-LATER': ['guest', 'overnight', 'visitors'],
};

export function detectObligationUseInText(text, obligationIds) {
  const haystack = String(text ?? '').toLowerCase();
  const used = [];
  for (const id of obligationIds) {
    const token = String(id).toLowerCase();
    if (haystack.includes(token)) used.push(id);
    const markers = OBLIGATION_SEMANTIC_MARKERS[id] ?? [];
    if (markers.some((m) => haystack.includes(m))) used.push(id);
  }
  return [...new Set(used)];
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

export function obligationMetDeferredLaterChain(store, obligationId) {
  const ob = store.obligations.find((o) => o.obligation_id === obligationId);
  if (!ob) return false;
  const hadDeferred = store.events.some((e) => (
    e.obligation_id === obligationId
    && (e.event_type === 'deferred_valid' || e.lifecycle_state === LIFECYCLE_STATES.DEFERRED_VALID)
  )) || ob.intro_turn < (ob.activated_turn ?? 999);
  return hadDeferred
    && ob.activated_turn != null
    && ob.lifecycle_state === LIFECYCLE_STATES.ACTIVATED_CONSEQUENTIAL;
}

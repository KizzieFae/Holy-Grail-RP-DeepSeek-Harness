/**
 * Issue #201 — paired-arm eligibility and comparability (LH-A authoritative).
 */
import { AGING_STATES } from './issue201-aging-contract.mjs';
import { trackedItemById } from './issue201-aging-fixtures.mjs';
import { evaluatePairedSemanticEstablishment } from './issue201-aging-establishment.mjs';

export function lhAAuthoritativeRegistry(registryLhA) {
  return registryLhA.tracked_items;
}

export function syncLhBOpportunityEligibility(registryLhB, registryLhA) {
  const items = registryLhB.tracked_items.map((bItem) => {
    const aItem = registryLhA.tracked_items.find(
      (a) => a.tracked_item_id === bItem.tracked_item_id,
    );
    if (!aItem) return bItem;
    return {
      ...bItem,
      opportunity_eligible: aItem.opportunity_eligible,
      aging_state: aItem.opportunity_eligible
        ? (bItem.persistence_provenance_chain?.length
          ? AGING_STATES.PERSISTED_AVAILABLE
          : AGING_STATES.OPPORTUNITY_PENDING)
        : aItem.aging_state,
      confirmatory_aged_out_turn: aItem.confirmatory_aged_out_turn,
      first_aged_out_turn: aItem.first_aged_out_turn,
    };
  });
  return { ...registryLhB, tracked_items: items };
}

export function assertPairedComparability({
  fixture,
  turnIndex,
  establishmentRecordsA,
  establishmentRecordsB,
  trackedItemId,
}) {
  const a = establishmentRecordsA?.[trackedItemId];
  const b = establishmentRecordsB?.[trackedItemId];
  if (!a || !b) {
    return { pass: false, reason: 'missing_establishment_record', turn_index: turnIndex, tracked_item_id: trackedItemId };
  }
  const trackedItem = trackedItemById(fixture, trackedItemId);
  if (!trackedItem) {
    return { pass: false, reason: 'missing_tracked_item', tracked_item_id: trackedItemId };
  }
  const paired = evaluatePairedSemanticEstablishment({
    trackedItem,
    recordA: a,
    recordB: b,
    turnIndexA: a.turn_index ?? turnIndex,
    turnIndexB: b.turn_index ?? turnIndex,
  });
  if (paired.bilateral_omission) {
    return {
      pass: true,
      bilateral_omission: true,
      reason: 'bilateral_omission',
      turn_index: turnIndex,
      tracked_item_id: trackedItemId,
      paired,
    };
  }
  if (paired.stop_c || !paired.pass) {
    return {
      pass: false,
      reason: paired.reason ?? 'establishment_integrity_failure',
      turn_index: turnIndex,
      tracked_item_id: trackedItemId,
      paired,
    };
  }
  return { pass: true, paired, tracked_item_id: trackedItemId };
}

export function lhBCannotSelfTriggerOpportunity(registryLhB, registryLhA, trackedItemId) {
  const a = registryLhA.tracked_items.find((t) => t.tracked_item_id === trackedItemId);
  const b = registryLhB.tracked_items.find((t) => t.tracked_item_id === trackedItemId);
  if (!a || !b) return { pass: false, reason: 'missing_item' };
  if (b.opportunity_eligible && !a.opportunity_eligible) {
    return { pass: false, reason: 'b_eligible_without_a' };
  }
  return { pass: true };
}

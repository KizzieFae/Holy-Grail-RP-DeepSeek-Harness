/**
 * Issue #201 — per-turn registry advancement (establishment → aging).
 */
import { LH0_ARMS } from './issue201-lh0-arms.mjs';
import { AGING_STATES, ESTABLISHMENT_STATES } from './issue201-aging-contract.mjs';
import {
  applyArmEstablishmentEvidence,
  canRunAgingLifecycle,
  checkPersistencePreestablishmentContamination,
  evaluatePairedSemanticEstablishment,
  finalizePairedEstablishment,
} from './issue201-aging-establishment.mjs';
import {
  applyAgingObservation,
  applyPersistenceObservation,
  classifyTrackedItemAvailability,
} from './issue201-aging-monitor.mjs';
import { trackedItemById } from './issue201-aging-fixtures.mjs';

export function advanceRegistryItemForTurn({
  fixture,
  registryItem,
  turnRow,
  turnIndex,
  arm,
}) {
  let item = applyArmEstablishmentEvidence(registryItem, {
    arm,
    turnIndex,
    turnRow,
    policyEstablishmentTurn: registryItem.establishment_turn,
  });

  const obs = classifyTrackedItemAvailability({
    fixture,
    trackedItem: item,
    assembledRequest: turnRow.assembled_request_character,
    playerStimulus: turnRow.exact_player_stimulus ?? '',
    continuitySnapshot: turnRow.continuity_snapshot,
  });

  if (arm === LH0_ARMS.LH_B) {
    item = checkPersistencePreestablishmentContamination(item, {
      persistencePresent: obs.persistence_present,
      turnIndex,
      arm: 'lh_b',
    });
  }

  if (!canRunAgingLifecycle(item)) {
    return {
      ...item,
      aging_state: AGING_STATES.UNESTABLISHED,
      opportunity_eligible: false,
    };
  }

  const clockStart = arm === LH0_ARMS.LH_B
    ? (item.aging_clock_start_turn_b ?? item.establishment_turn)
    : (item.aging_clock_start_turn_a ?? item.establishment_turn);
  if (turnIndex < clockStart) {
    return item;
  }

  let next = applyAgingObservation({
    registryItem: item,
    observation: obs,
    turnIndex,
    hgRoundId: turnRow.hg_round_id,
    arm,
  });
  if (arm === LH0_ARMS.LH_B) {
    next = applyPersistenceObservation(next, obs, turnIndex);
  }
  return next;
}

export function advanceRegistryForTurn({
  fixture,
  registry,
  turnRow,
  turnIndex,
  arm,
}) {
  const items = registry.tracked_items.map((item) => advanceRegistryItemForTurn({
    fixture,
    registryItem: item,
    turnRow,
    turnIndex,
    arm,
  }));
  return { ...registry, tracked_items: items };
}

export function replayLhAAgingObservations({ fixture, registry, turnsA }) {
  let reg = registry;
  for (const turnRow of turnsA ?? []) {
    const turnIndex = turnRow.turn_index;
    reg = {
      ...reg,
      tracked_items: reg.tracked_items.map((item) => {
        if (!canRunAgingLifecycle(item)) {
          return { ...item, aging_state: AGING_STATES.UNESTABLISHED, opportunity_eligible: false };
        }
        const clockStart = item.aging_clock_start_turn_a ?? item.establishment_turn;
        if (turnIndex < clockStart) return item;
        const obs = classifyTrackedItemAvailability({
          fixture,
          trackedItem: item,
          assembledRequest: turnRow.assembled_request_character,
          playerStimulus: turnRow.exact_player_stimulus ?? '',
          continuitySnapshot: turnRow.continuity_snapshot,
        });
        return applyAgingObservation({
          registryItem: item,
          observation: obs,
          turnIndex,
          hgRoundId: turnRow.hg_round_id,
          arm: LH0_ARMS.LH_A,
        });
      }),
    };
  }
  return reg;
}

export function evaluateEstablishmentIntegrityStop(registry, fixture, establishmentRecordsA, establishmentRecordsB) {
  for (const fxItem of fixture.tracked_items ?? []) {
    const cmp = evaluatePairedSemanticEstablishment({
      trackedItem: fxItem,
      recordA: establishmentRecordsA[fxItem.tracked_item_id],
      recordB: establishmentRecordsB[fxItem.tracked_item_id],
      turnIndexA: establishmentRecordsA[fxItem.tracked_item_id]?.turn_index ?? fxItem.establishment_turn,
      turnIndexB: establishmentRecordsB[fxItem.tracked_item_id]?.turn_index ?? fxItem.establishment_turn,
    });
    if (cmp.stop_c && cmp.reason === 'unilateral_establishment') {
      return {
        stop: true,
        reason: 'unilateral_establishment',
        tracked_item_id: fxItem.tracked_item_id,
        paired: cmp,
      };
    }
    const regItem = registry.tracked_items.find((t) => t.tracked_item_id === fxItem.tracked_item_id);
    if (regItem?.establishment_state === ESTABLISHMENT_STATES.PERSISTENCE_PREESTABLISHMENT_CONTAMINATION) {
      return {
        stop: true,
        reason: 'persistence_preestablishment_contamination',
        tracked_item_id: fxItem.tracked_item_id,
      };
    }
  }
  return { stop: false };
}

export function markRegistryPairedEstablishment(registry, fixture, establishmentRecordsA, establishmentRecordsB) {
  const items = registry.tracked_items.map((item) => {
    const fxItem = trackedItemById(fixture, item.tracked_item_id) ?? item;
    const paired = evaluatePairedSemanticEstablishment({
      trackedItem: fxItem,
      recordA: establishmentRecordsA[item.tracked_item_id],
      recordB: establishmentRecordsB[item.tracked_item_id],
      turnIndexA: establishmentRecordsA[item.tracked_item_id]?.turn_index ?? item.establishment_turn_arm_a,
      turnIndexB: establishmentRecordsB[item.tracked_item_id]?.turn_index ?? item.establishment_turn_arm_b,
    });
    return finalizePairedEstablishment(item, paired);
  });
  return { ...registry, tracked_items: items };
}

/**
 * Issue #201 — dynamic opportunity scheduler (LH-A authoritative).
 */
import { AGING_STATES } from './issue201-aging-contract.mjs';
import { trackedItemById } from './issue201-aging-fixtures.mjs';
import { shouldBlockOpportunity } from './issue201-aging-establishment.mjs';

export function isOpportunityEligible(registryItem) {
  if (shouldBlockOpportunity(registryItem)) return false;
  const agedReady = registryItem.confirmatory_aged_out_turn != null;
  return agedReady && (
    registryItem.opportunity_eligible === true
    || registryItem.aging_state === AGING_STATES.OPPORTUNITY_PENDING
  );
}

export function resolvePlayerStimulusForTurn({
  policy,
  turnIndex,
  registry,
  lhARegistryItems = null,
}) {
  const turn = policy.turns.find((t) => t.turn_index === turnIndex);
  if (!turn) throw new Error(`no policy turn ${turnIndex}`);

  if (turn.branch_mode !== 'gated_opportunity') {
    return {
      stimulus: turn.realization,
      gated: false,
      opportunity_id: null,
      withheld_reason: null,
    };
  }

  const trackedId = turn.tracked_item_id;
  const item = trackedItemById(
    { tracked_items: lhARegistryItems ?? registry.tracked_items },
    trackedId,
  );
  const lhAItem = (lhARegistryItems ?? registry.tracked_items).find(
    (t) => t.tracked_item_id === trackedId,
  );

  if (!lhAItem || !isOpportunityEligible(lhAItem)) {
    const state = lhAItem?.aging_state ?? 'unknown';
    return {
      stimulus: turn.fallback_realization ?? turn.realization,
      gated: true,
      opportunity_id: turn.gated_opportunity_id,
      tracked_item_id: trackedId,
      fired: false,
      withheld_reason: `lh_a_state_${state}`,
    };
  }

  return {
    stimulus: turn.realization,
    gated: true,
    opportunity_id: turn.gated_opportunity_id,
    tracked_item_id: trackedId,
    fired: true,
    withheld_reason: null,
  };
}

export function stimulusLeakageCheckForOpportunity(trackedItem, stimulus) {
  const lower = String(stimulus ?? '').toLowerCase();
  const forbidden = [
    'do you remember',
    'as i said',
    'as we discussed',
    'pantry alcove',
    'staff pantry',
    'trial staff meals',
  ];
  const hits = forbidden.filter((f) => lower.includes(f));
  const markerHits = (trackedItem.behavior_markers ?? []).filter(
    (m) => lower.includes(String(m).toLowerCase()),
  );
  return {
    pass: hits.length === 0 && markerHits.length === 0,
    forbidden_hits: hits,
    marker_hits: markerHits,
  };
}

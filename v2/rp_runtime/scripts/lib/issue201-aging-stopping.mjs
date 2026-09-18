/**
 * Issue #201 — campaign stopping state machine.
 */
import { AGING_DEFAULT_MAX_TURNS, AGING_STOP_REASONS } from './issue201-aging-contract.mjs';
import { AGING_STATES } from './issue201-aging-contract.mjs';

export function evaluateCampaignStop({
  turnIndex,
  maxTurns = AGING_DEFAULT_MAX_TURNS,
  registryLhA,
  testedItems = [],
  failClosed = null,
}) {
  if (failClosed) {
    return {
      stop: true,
      reason: AGING_STOP_REASONS.STOP_C_FAIL_CLOSED,
      detail: failClosed,
    };
  }

  const cleanTested = testedItems.filter((t) => t.clean_aging_evidence && t.interpretable);
  if (cleanTested.length >= 1) {
    return {
      stop: true,
      reason: AGING_STOP_REASONS.STOP_A_CLEAN_RESULT,
      detail: { tested_item_id: cleanTested[0].tracked_item_id },
    };
  }

  if (turnIndex >= maxTurns) {
    const anyAgedOut = registryLhA.tracked_items.some(
      (t) => t.confirmatory_aged_out_turn != null,
    );
    if (!anyAgedOut) {
      return {
        stop: true,
        reason: AGING_STOP_REASONS.STOP_B_MAX_BOUNDARY,
        detail: { turn_index: turnIndex, max_turns: maxTurns },
      };
    }
  }

  return { stop: false, reason: null };
}

export function markItemTested(registryItem, turnIndex) {
  return {
    ...registryItem,
    aging_state: AGING_STATES.TESTED,
    tested_turn: turnIndex,
    opportunity_eligible: false,
  };
}

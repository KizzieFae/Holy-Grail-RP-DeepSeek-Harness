/**
 * Issue #201 — semantic establishment & paired equivalence (aging apparatus).
 */
import { ESTABLISHMENT_STATES } from './issue201-aging-contract.mjs';
import { semanticFingerprint } from './issue201-aging-fixtures.mjs';

function normalize(text) {
  return String(text ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function markerHits(haystack, markers = []) {
  return markers.filter((m) => haystack.includes(String(m).toLowerCase()));
}

function semanticFragmentPresent(haystack, semantic) {
  const text = String(semantic ?? '').toLowerCase().trim();
  if (!text) return false;
  const slice = text.slice(0, Math.min(48, text.length));
  return slice.length >= 12 && haystack.includes(slice);
}

const CONTRADICTION_PATTERNS = Object.freeze({
  'TRK-AYA-MEAL-ALCOVE': [
    /eat wherever i (put|assign)/i,
    /meals are taken where i put you/i,
    /kitchen, at the end of the table/i,
  ],
  'TRK-AYA-PROMISE-GATE': [
    /may enter (the )?east wing without/i,
    /no restriction on the east wing/i,
  ],
  'TRK-AYA-DORMANT-RECORD': [
    /previous assistant (was )?(reliable|trustworthy|recommended)/i,
    /never (copied|took) (any )?ledger/i,
  ],
});

const REQUIRED_MARKER_GROUPS = Object.freeze({
  'TRK-AYA-MEAL-ALCOVE': [
    ['pantry alcove', 'staff pantry'],
    ['household dining table', 'not at the household dining table'],
  ],
  'TRK-AYA-DORMANT-RECORD': [
    ['previous assistant', 'previous live-in'],
    ['dismissed', 'copied ledger', 'ledger pages'],
  ],
  'TRK-AYA-PROMISE-GATE': [
    ['east wing', 'restricted area'],
    ['written authorization', 'without written authorization'],
  ],
});

export function committedStoryText({ move_text, presentation_text } = {}) {
  return [move_text, presentation_text].filter(Boolean).join('\n');
}

/**
 * Semantic establishment in committed story evidence (Character + Narrator presentation).
 */
export function evaluateSemanticEstablishment(trackedItem, committedText) {
  const haystack = normalize(committedText);
  const proposition = trackedItem.semantic_proposition ?? '';
  const markers = trackedItem.behavior_markers ?? [];
  const hits = markerHits(haystack, markers);
  const fragment = semanticFragmentPresent(haystack, proposition);
  const contradictions = (CONTRADICTION_PATTERNS[trackedItem.tracked_item_id] ?? [])
    .filter((re) => re.test(haystack));
  if (contradictions.length) {
    return {
      established: false,
      verdict: 'contradiction',
      marker_hits: hits,
      semantic_fragment: fragment,
      contradictions: contradictions.map((r) => String(r)),
      committed_source: 'character_and_presentation',
    };
  }

  const groups = REQUIRED_MARKER_GROUPS[trackedItem.tracked_item_id] ?? [];
  const groupsSatisfied = groups.length === 0
    || groups.every((group) => group.some((m) => haystack.includes(String(m).toLowerCase())));

  if (fragment && groupsSatisfied) {
    return {
      established: true,
      verdict: 'established',
      marker_hits: hits,
      semantic_fragment: true,
      committed_source: 'character_and_presentation',
      semantic_fingerprint: semanticFingerprint(proposition),
    };
  }

  if (fragment && !groupsSatisfied) {
    return {
      established: false,
      verdict: 'partial_proposition',
      marker_hits: hits,
      semantic_fragment: true,
      committed_source: 'character_and_presentation',
    };
  }

  if (hits.length >= 2 && groupsSatisfied) {
    return {
      established: true,
      verdict: 'established_marker_coverage',
      marker_hits: hits,
      semantic_fragment: false,
      committed_source: 'character_and_presentation',
      semantic_fingerprint: semanticFingerprint(proposition),
    };
  }

  if (hits.length > 0) {
    return {
      established: false,
      verdict: 'partial_proposition',
      marker_hits: hits,
      semantic_fragment: false,
      committed_source: 'character_and_presentation',
    };
  }

  return {
    established: false,
    verdict: 'omission',
    marker_hits: hits,
    semantic_fragment: false,
    committed_source: 'character_and_presentation',
  };
}

export const MAX_ESTABLISHMENT_TURN_SKEW = 2;

/**
 * Paired semantic establishment (not verbatim prose).
 */
export function evaluatePairedSemanticEstablishment({
  trackedItem,
  recordA,
  recordB,
  turnIndexA = null,
  turnIndexB = null,
  maxTurnSkew = MAX_ESTABLISHMENT_TURN_SKEW,
}) {
  const textA = committedStoryText({
    move_text: recordA?.move_text,
    presentation_text: recordA?.presentation_text,
  });
  const textB = committedStoryText({
    move_text: recordB?.move_text,
    presentation_text: recordB?.presentation_text,
  });
  const estA = evaluateSemanticEstablishment(trackedItem, textA);
  const estB = evaluateSemanticEstablishment(trackedItem, textB);
  const stimMatch = String(recordA?.player_stimulus ?? '').trim()
    === String(recordB?.player_stimulus ?? '').trim();

  if (!estA.established && !estB.established) {
    return {
      pass: true,
      stop_c: false,
      bilateral_omission: true,
      establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED,
      semantic_establishment_a: false,
      semantic_establishment_b: false,
      semantic_equivalence: null,
      stimulus_match: stimMatch,
      detail_a: estA,
      detail_b: estB,
      reason: 'bilateral_omission',
    };
  }

  if (estA.established !== estB.established) {
    return {
      pass: false,
      stop_c: true,
      bilateral_omission: false,
      establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED,
      semantic_establishment_a: estA.established,
      semantic_establishment_b: estB.established,
      semantic_equivalence: false,
      stimulus_match: stimMatch,
      detail_a: estA,
      detail_b: estB,
      reason: 'unilateral_establishment',
    };
  }

  if (turnIndexA != null && turnIndexB != null) {
    const skew = Math.abs(turnIndexA - turnIndexB);
    if (skew > maxTurnSkew) {
      return {
        pass: false,
        stop_c: true,
        bilateral_omission: false,
        establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED,
        semantic_establishment_a: true,
        semantic_establishment_b: true,
        semantic_equivalence: false,
        turn_skew: skew,
        reason: 'turn_skew_divergence',
        detail_a: estA,
        detail_b: estB,
      };
    }
  }

  const strengthMismatch = estA.verdict !== estB.verdict
    && (estA.verdict === 'partial_proposition' || estB.verdict === 'partial_proposition');
  if (strengthMismatch) {
    return {
      pass: false,
      stop_c: true,
      reason: 'semantic_strength_mismatch',
      detail_a: estA,
      detail_b: estB,
    };
  }

  return {
    pass: true,
    stop_c: false,
    bilateral_omission: false,
    establishment_state: ESTABLISHMENT_STATES.ESTABLISHED,
    semantic_establishment_a: true,
    semantic_establishment_b: true,
    semantic_equivalence: true,
    stimulus_match: stimMatch,
    detail_a: estA,
    detail_b: estB,
    reason: 'paired_semantic_establishment',
  };
}

export function applyArmEstablishmentEvidence(registryItem, {
  arm,
  turnIndex,
  turnRow,
  policyEstablishmentTurn,
}) {
  const isAttemptTurn = turnIndex >= policyEstablishmentTurn;
  if (!isAttemptTurn) return registryItem;

  const evalResult = evaluateSemanticEstablishment(
    registryItem,
    committedStoryText(turnRow),
  );
  const next = {
    ...registryItem,
    establishment_attempted: registryItem.establishment_attempted || turnIndex === policyEstablishmentTurn,
  };

  if (arm === 'lh_a') {
    next.establishment_evidence_arm_a = evalResult;
    next.semantic_establishment_arm_a = evalResult.established;
    if (evalResult.established && !next.establishment_turn_arm_a) {
      next.establishment_turn_arm_a = turnIndex;
    }
  } else {
    next.establishment_evidence_arm_b = evalResult;
    next.semantic_establishment_arm_b = evalResult.established;
    if (evalResult.established && !next.establishment_turn_arm_b) {
      next.establishment_turn_arm_b = turnIndex;
    }
  }
  return next;
}

export function finalizePairedEstablishment(registryItem, pairedEval) {
  if (pairedEval.bilateral_omission) {
    return {
      ...registryItem,
      establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED,
      paired_semantic_equivalence: null,
      aging_clock_started: false,
      aging_state: null,
    };
  }
  if (!pairedEval.pass || pairedEval.stop_c) {
    return {
      ...registryItem,
      establishment_state: pairedEval.reason === 'unilateral_establishment'
        ? ESTABLISHMENT_STATES.UNESTABLISHED
        : registryItem.establishment_state,
      paired_semantic_equivalence: false,
      aging_clock_started: false,
      establishment_integrity_failure: pairedEval.reason,
    };
  }
  return {
    ...registryItem,
    establishment_state: ESTABLISHMENT_STATES.ESTABLISHED,
    paired_semantic_equivalence: true,
    aging_clock_started: true,
    aging_clock_start_turn_a: registryItem.establishment_turn_arm_a ?? registryItem.establishment_turn,
    aging_clock_start_turn_b: registryItem.establishment_turn_arm_b ?? registryItem.establishment_turn,
    aging_state: registryItem.aging_state ?? null,
  };
}

export function checkPersistencePreestablishmentContamination(registryItem, {
  persistencePresent,
  turnIndex,
  arm,
}) {
  if (arm !== 'lh_b') return registryItem;
  if (!persistencePresent) return registryItem;
  if (registryItem.establishment_state === ESTABLISHMENT_STATES.ESTABLISHED) return registryItem;
  if (registryItem.semantic_establishment_arm_b) return registryItem;
  return {
    ...registryItem,
    establishment_state: ESTABLISHMENT_STATES.PERSISTENCE_PREESTABLISHMENT_CONTAMINATION,
    contamination: {
      type: 'PERSISTENCE_PREESTABLISHMENT_CONTAMINATION',
      turn_index: turnIndex,
      obligation_id: registryItem.obligation_id,
    },
    aging_clock_started: false,
    opportunity_eligible: false,
    causal_item_valid: false,
  };
}

export function canRunAgingLifecycle(registryItem) {
  return registryItem.establishment_state === ESTABLISHMENT_STATES.ESTABLISHED
    && registryItem.aging_clock_started === true
    && registryItem.establishment_state !== ESTABLISHMENT_STATES.PERSISTENCE_PREESTABLISHMENT_CONTAMINATION
    && registryItem.causal_item_valid !== false;
}

export function shouldBlockOpportunity(registryItem) {
  if (!canRunAgingLifecycle(registryItem)) return true;
  if (registryItem.contamination) return true;
  return false;
}

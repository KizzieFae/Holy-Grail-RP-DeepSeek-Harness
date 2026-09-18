/**
 * Issue #201 — information-aging monitor (lean substrate + lifecycle).
 */
import crypto from 'node:crypto';

import { AGING_SCHEMAS, AGING_STATES, ESTABLISHMENT_STATES } from './issue201-aging-contract.mjs';
import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import {
  contributionsFromAssembledRequest,
  partitionManifestContributions,
  presentationTranscriptFromContributions,
} from './issue201-r5-runner-analysis.mjs';
import {
  forkShapeForTrackedItem,
  obligationById,
  semanticFingerprint,
} from './issue201-aging-fixtures.mjs';

const ROLE_PRIVATE_KINDS = new Set([
  'character_private',
  'role_private_knowledge',
  'private_character_knowledge',
]);

function normalize(text) {
  return String(text ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function isPersistenceContribution(c) {
  if (!c) return false;
  if (c?.provenance?.lh0_obligation_id) return true;
  if (c?.provenance?.finalized_projection) return true;
  for (const kid of c?.knowledge_ids ?? []) {
    if (String(kid).startsWith('lh0-obligation:')) return true;
  }
  return false;
}

function persistenceCarriesItem(contributions, obligationId) {
  return (contributions ?? []).some(
    (c) => isPersistenceContribution(c) && c?.provenance?.lh0_obligation_id === obligationId,
  );
}

/**
 * Full channel classification for one tracked item at a checkpoint.
 */
export function classifyTrackedItemAvailability({
  fixture,
  trackedItem,
  assembledRequest,
  playerStimulus = '',
  continuitySnapshot = null,
}) {
  const contributions = contributionsFromAssembledRequest(assembledRequest);
  const parts = partitionManifestContributions(contributions);
  const fork = forkShapeForTrackedItem(trackedItem);
  const obligation = obligationById(fixture, trackedItem.obligation_id);
  const fixtureForClassifier = {
    obligations: fixture.obligations,
  };
  const classification = classifyActualSubstrateUniqueness({
    fixture: fixtureForClassifier,
    fork,
    manifestContributions: contributions.filter((c) => !isPersistenceContribution(c)),
    playerStimulus,
    presentationTranscript: presentationTranscriptFromContributions(contributions),
    continuitySnapshot,
    retrievalContributions: parts.retrieval,
  });

  const channels = {
    transcript: classification.flags.transcript_sufficient === true,
    continuity: classification.flags.continuity_sufficient === true,
    retrieval: classification.flags.retrieval_sufficient === true,
    memory_summary: classification.flags.memory_or_summary_sufficient === true,
    role_private: parts.rolePrivate.length > 0
      && (classification.marker_hits?.memory?.length > 0
        || classification.semantic_fragment_in_lean_substrate),
    stimulus: classification.flags.stimulus_sufficient === true,
    scene_context: parts.lean.some((c) => c.source_kind === 'scene_context')
      && classification.semantic_fragment_in_lean_substrate,
    director_context: parts.lean.some((c) => c.source_kind === 'director_context')
      && classification.semantic_fragment_in_lean_substrate,
    other_lean: classification.flags.other_substrate_sufficient === true,
  };

  let leanOtherChannels = [];
  if (channels.continuity) leanOtherChannels.push('continuity');
  if (channels.retrieval) leanOtherChannels.push('retrieval');
  if (channels.memory_summary) leanOtherChannels.push('memory_summary');
  if (channels.role_private) leanOtherChannels.push('role_private');
  if (channels.scene_context) leanOtherChannels.push('scene_context');
  if (channels.director_context) leanOtherChannels.push('director_context');
  if (channels.other_lean) leanOtherChannels.push('other_lean');
  if (channels.stimulus) leanOtherChannels.push('stimulus');

  let availabilityState = AGING_STATES.AGED_OUT;
  if (channels.transcript) {
    availabilityState = AGING_STATES.PRESENT_RAW;
  } else if (leanOtherChannels.length > 0) {
    availabilityState = AGING_STATES.PRESENT_LEAN_OTHER;
  }

  const semanticPresentLean = classification.semantic_fragment_in_lean_substrate
    || Object.values(classification.flags).some(Boolean);
  if (availabilityState === AGING_STATES.AGED_OUT && semanticPresentLean) {
    availabilityState = AGING_STATES.PRESENT_LEAN_OTHER;
    if (!leanOtherChannels.length) leanOtherChannels.push('semantic_fragment');
  }

  return {
    schema: AGING_SCHEMAS.AGING_TIMELINE,
    tracked_item_id: trackedItem.tracked_item_id,
    semantic_fingerprint: semanticFingerprint(trackedItem.semantic_proposition),
    availability_state: availabilityState,
    lean_other_channels: leanOtherChannels,
    channels,
    classification,
    obligation_semantic: obligation?.semantic_content ?? trackedItem.semantic_proposition,
    persistence_present: persistenceCarriesItem(contributions, trackedItem.obligation_id),
  };
}

function confirmatoryReanalysisSameRequest(first, second) {
  return first.availability_state === second.availability_state
    && first.availability_state === AGING_STATES.AGED_OUT;
}

/**
 * Update registry item state from checkpoint observation (LH-A authoritative for aging).
 */
export function applyAgingObservation({
  registryItem,
  observation,
  turnIndex,
  hgRoundId = null,
  arm = 'lh_a',
}) {
  if (registryItem.establishment_state !== ESTABLISHMENT_STATES.ESTABLISHED
    || registryItem.aging_clock_started !== true
    || registryItem.causal_item_valid === false
    || registryItem.contamination) {
    return {
      ...registryItem,
      aging_state: AGING_STATES.UNESTABLISHED,
      opportunity_eligible: false,
    };
  }
  const historyEntry = {
    turn_index: turnIndex,
    hg_round_id: hgRoundId,
    arm,
    availability_state: observation.availability_state,
    lean_other_channels: observation.lean_other_channels,
    channels: observation.channels,
    at: new Date().toISOString(),
  };

  const next = {
    ...registryItem,
    aging_history: [...(registryItem.aging_history ?? []), historyEntry],
  };

  if (observation.availability_state === AGING_STATES.PRESENT_RAW) {
    next.aging_state = AGING_STATES.PRESENT_RAW;
    next.last_raw_presence_turn = turnIndex;
    next.opportunity_eligible = false;
    return next;
  }

  if (observation.availability_state === AGING_STATES.PRESENT_LEAN_OTHER) {
    next.aging_state = AGING_STATES.PRESENT_LEAN_OTHER;
    if (!next.first_lean_other_turn) next.first_lean_other_turn = turnIndex;
    next.opportunity_eligible = false;
    return next;
  }

  if (observation.availability_state === AGING_STATES.AGED_OUT) {
    if (!next.first_aged_out_turn) {
      next.first_aged_out_turn = turnIndex;
      next.aging_state = AGING_STATES.AGED_OUT;
      next._pending_confirmatory = true;
      next.opportunity_eligible = false;
      return next;
    }
    if (next._pending_confirmatory && next.first_aged_out_turn < turnIndex) {
      next.confirmatory_aged_out_turn = turnIndex;
      next._pending_confirmatory = false;
      next.aging_state = AGING_STATES.OPPORTUNITY_PENDING;
      next.opportunity_eligible = true;
      return next;
    }
    if (next.confirmatory_aged_out_turn) {
      next.aging_state = AGING_STATES.OPPORTUNITY_PENDING;
      next.opportunity_eligible = true;
    }
    return next;
  }

  return next;
}

export function applyPersistenceObservation(registryItem, observation, turnIndex) {
  if (observation.persistence_present && registryItem.aging_state === AGING_STATES.OPPORTUNITY_PENDING
    || observation.persistence_present && registryItem.aging_state === AGING_STATES.AGED_OUT) {
    return {
      ...registryItem,
      aging_state: AGING_STATES.PERSISTED_AVAILABLE,
      persistence_provenance_chain: [
        ...(registryItem.persistence_provenance_chain ?? []),
        { turn_index: turnIndex, obligation_id: registryItem.obligation_id },
      ],
    };
  }
  return registryItem;
}

export function confirmAgingFromConsecutiveObservations(obsA, obsB) {
  return obsA.availability_state === AGING_STATES.AGED_OUT
    && obsB.availability_state === AGING_STATES.AGED_OUT;
}

export function confirmAgingFromDuplicateAnalysis(observation) {
  const second = classifyTrackedItemAvailability({
    fixture: observation._fixture,
    trackedItem: observation._trackedItem,
    assembledRequest: observation._assembledRequest,
    playerStimulus: observation._playerStimulus,
    continuitySnapshot: observation._continuitySnapshot,
  });
  return confirmatoryReanalysisSameRequest(observation, second);
}

export function transcriptCompositionHash(assembledRequest) {
  const contribs = contributionsFromAssembledRequest(assembledRequest);
  const transcript = contribs
    .filter((c) => String(c?.source_kind ?? '').includes('transcript'))
    .map((c) => normalize(c.content))
    .join('|');
  return crypto.createHash('sha256').update(transcript).digest('hex');
}

export function buildTranscriptObservationRecord(registry, turnIndex, observationsByItem) {
  return {
    turn_index: turnIndex,
    items_present_raw: Object.entries(observationsByItem)
      .filter(([, o]) => o.availability_state === AGING_STATES.PRESENT_RAW)
      .map(([id]) => id),
    items_present_lean_other: Object.entries(observationsByItem)
      .filter(([, o]) => o.availability_state === AGING_STATES.PRESENT_LEAN_OTHER)
      .map(([id, o]) => ({ id, channels: o.lean_other_channels })),
    items_aged_out: Object.entries(observationsByItem)
      .filter(([, o]) => o.availability_state === AGING_STATES.AGED_OUT)
      .map(([id]) => id),
    items_opportunity_pending: registry.tracked_items
      .filter((t) => t.opportunity_eligible)
      .map((t) => t.tracked_item_id),
  };
}

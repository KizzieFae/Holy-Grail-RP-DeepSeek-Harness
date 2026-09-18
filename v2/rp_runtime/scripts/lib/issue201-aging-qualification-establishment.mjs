/**
 * Issue #201 — establishment semantic qualification gates AG17–AG28 + run2 regression.
 */
import { AGING_STATES, ESTABLISHMENT_STATES } from './issue201-aging-contract.mjs';
import {
  evaluateSemanticEstablishment,
  evaluatePairedSemanticEstablishment,
  checkPersistencePreestablishmentContamination,
  canRunAgingLifecycle,
  shouldBlockOpportunity,
} from './issue201-aging-establishment.mjs';
import {
  applyAgingObservation,
  classifyTrackedItemAvailability,
} from './issue201-aging-monitor.mjs';
import { resolvePlayerStimulusForTurn } from './issue201-aging-scheduler.mjs';
import { assertPairedComparability } from './issue201-aging-paired.mjs';
import { loadAgingFixtureManifest, loadAgingPolicy, trackedItemById } from './issue201-aging-fixtures.mjs';
import { markRegistryPairedEstablishment, replayLhAAgingObservations } from './issue201-aging-registry.mjs';
import { buildTrackedItemRegistry } from './issue201-aging-fixtures.mjs';

function gate(name, pass, detail = null) {
  return { name, pass, detail };
}

const RUN2_T5_A_MOVE = 'Staff areas. Family-only. You\'ve asked me for a curfew, a figure, and now a map. I\'m beginning to think you\'re pricing the exits before you\'ve seen the rooms. There will be a floor plan, in writing, with the figure — once we\'re inside. What I\'ll tell you now is this: this house doesn\'t divide that way. It isn\'t kept by staff. It\'s kept by one person who lives in it, and everything else follows from that. So the better question isn\'t where you\'re allowed to go. It\'s whose house you\'d be living in.';
const RUN2_T5_B_MOVE = 'Four questions from a doorstep. Not one of them about the work. There are no staff areas yet. There is a house, and there is the question of which parts of it I decide a person belongs in. That is settled inside, in writing, after I have looked at you properly — not traded across a doorway like a floor plan. The study is at the end. Come and be answered.';
const RUN2_STIM = 'Kizzie asks, "Which parts of the house are staff areas versus family-only?"';

function withSyntheticPairedEstablishment(item, turnA = 6, turnB = 6) {
  return {
    ...item,
    establishment_state: ESTABLISHMENT_STATES.ESTABLISHED,
    aging_clock_started: true,
    aging_clock_start_turn_a: turnA,
    aging_clock_start_turn_b: turnB,
    paired_semantic_equivalence: true,
    semantic_establishment_arm_a: true,
    semantic_establishment_arm_b: true,
    causal_item_valid: true,
  };
}

export function runEstablishmentQualificationGates() {
  const fixture = loadAgingFixtureManifest();
  const meal = trackedItemById(fixture, 'TRK-AYA-MEAL-ALCOVE');
  const dormant = trackedItemById(fixture, 'TRK-AYA-DORMANT-RECORD');
  const gates = [];

  const paraphraseA = 'During your trial week you\'ll eat in the pantry alcove when guests are at the household dining table.';
  const paraphraseB = 'If I have dinner guests, trial staff take meals in the pantry alcove rather than at the household dining table.';
  const pairedParaphrase = evaluatePairedSemanticEstablishment({
    trackedItem: meal,
    recordA: { move_text: paraphraseA, player_stimulus: 'meal?' },
    recordB: { move_text: paraphraseB, player_stimulus: 'meal?' },
  });
  gates.push(gate('AG17_semantic_paraphrase_equivalence', pairedParaphrase.pass && pairedParaphrase.semantic_equivalence === true, pairedParaphrase));

  const weakB = 'Trial staff may eat wherever Ayame assigns them.';
  const pairedWeak = evaluatePairedSemanticEstablishment({
    trackedItem: meal,
    recordA: { move_text: meal.establishment.character_move_dialogue, player_stimulus: 'meal?' },
    recordB: { move_text: weakB, player_stimulus: 'meal?' },
  });
  gates.push(gate('AG18_material_semantic_difference', pairedWeak.stop_c === true && pairedWeak.reason === 'unilateral_establishment', pairedWeak));

  const run2Pair = evaluatePairedSemanticEstablishment({
    trackedItem: dormant,
    recordA: { move_text: RUN2_T5_A_MOVE, player_stimulus: RUN2_STIM },
    recordB: { move_text: RUN2_T5_B_MOVE, player_stimulus: RUN2_STIM },
  });
  gates.push(gate('AG19_bilateral_omission', run2Pair.bilateral_omission === true && run2Pair.stop_c === false, run2Pair));

  const unilateral = evaluatePairedSemanticEstablishment({
    trackedItem: dormant,
    recordA: { move_text: dormant.establishment.character_move_dialogue, player_stimulus: RUN2_STIM },
    recordB: { move_text: RUN2_T5_B_MOVE, player_stimulus: RUN2_STIM },
  });
  gates.push(gate('AG20_unilateral_establishment', unilateral.stop_c === true && unilateral.reason === 'unilateral_establishment', unilateral));

  const unestablished = { ...meal, aging_history: [], establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED, aging_clock_started: false };
  const obsAbsent = classifyTrackedItemAvailability({
    fixture,
    trackedItem: unestablished,
    assembledRequest: { contributions: [{ source_kind: 'recent_scene_transcript', content: 'tea and linens' }] },
  });
  const afterUnest = applyAgingObservation({
    registryItem: unestablished,
    observation: obsAbsent,
    turnIndex: 20,
  });
  gates.push(gate('AG21_no_aging_before_establishment', afterUnest.aging_state === AGING_STATES.UNESTABLISHED || !canRunAgingLifecycle(afterUnest), { obs: obsAbsent.availability_state, state: afterUnest.aging_state }));

  let contaminated = { ...dormant, establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED, semantic_establishment_arm_b: false };
  contaminated = checkPersistencePreestablishmentContamination(contaminated, {
    persistencePresent: true,
    turnIndex: 5,
    arm: 'lh_b',
  });
  gates.push(gate('AG22_persistence_preestablishment_contamination',
    contaminated.establishment_state === ESTABLISHMENT_STATES.PERSISTENCE_PREESTABLISHMENT_CONTAMINATION, contaminated));

  let reg = buildTrackedItemRegistry(fixture);
  const recordsA = {
    [meal.tracked_item_id]: {
      move_text: meal.establishment.character_move_dialogue,
      presentation_text: meal.establishment.shared_committed_presentation,
      player_stimulus: meal.establishment.player_stimulus,
      turn_index: 6,
    },
  };
  const recordsB = {
    [meal.tracked_item_id]: {
      move_text: 'If guests are expected at formal meal, trial staff meals stay in the pantry alcove, not at the household dining table.',
      player_stimulus: meal.establishment.player_stimulus,
      turn_index: 6,
    },
  };
  reg = markRegistryPairedEstablishment(reg, fixture, recordsA, recordsB);
  const mealItem = reg.tracked_items.find((t) => t.tracked_item_id === meal.tracked_item_id);
  gates.push(gate('AG23_aging_starts_after_paired_establishment', mealItem.aging_clock_started === true && mealItem.establishment_state === ESTABLISHMENT_STATES.ESTABLISHED, mealItem));

  const skewOk = evaluatePairedSemanticEstablishment({
    trackedItem: meal,
    recordA: { move_text: meal.establishment.character_move_dialogue, player_stimulus: 'x' },
    recordB: { move_text: 'Trial staff take meals in the pantry alcove, not at the household dining table when guests are expected.', player_stimulus: 'x' },
    turnIndexA: 6,
    turnIndexB: 7,
  });
  gates.push(gate('AG24_turn_skew_semantic_checkpoint', skewOk.pass === true, skewOk));

  const skewBad = evaluatePairedSemanticEstablishment({
    trackedItem: meal,
    recordA: { move_text: meal.establishment.character_move_dialogue, player_stimulus: 'x' },
    recordB: { move_text: meal.establishment.character_move_dialogue, player_stimulus: 'x' },
    turnIndexA: 6,
    turnIndexB: 12,
  });
  gates.push(gate('AG25_turn_skew_divergence', skewBad.stop_c === true && skewBad.reason === 'turn_skew_divergence', skewBad));

  const run2Unestablished = {
    ...meal,
    establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED,
    aging_clock_started: false,
    aging_history: [],
    opportunity_eligible: true,
    aging_state: AGING_STATES.OPPORTUNITY_PENDING,
    confirmatory_aged_out_turn: 31,
  };
  const schedPremature = resolvePlayerStimulusForTurn({
    policy: loadAgingPolicy().policy,
    turnIndex: 14,
    registry: { tracked_items: [run2Unestablished] },
    lhARegistryItems: [run2Unestablished],
  });
  gates.push(gate('AG26_premature_opportunity_blocked', schedPremature.fired === false, schedPremature));

  let agedItem = withSyntheticPairedEstablishment({ ...meal, aging_history: [] });
  const aged1 = classifyTrackedItemAvailability({ fixture, trackedItem: meal, assembledRequest: { contributions: [{ source_kind: 'recent_scene_transcript', content: 'neutral chatter' }] } });
  agedItem = applyAgingObservation({ registryItem: agedItem, observation: aged1, turnIndex: 30 });
  agedItem = applyAgingObservation({ registryItem: agedItem, observation: aged1, turnIndex: 31 });
  const schedReady = resolvePlayerStimulusForTurn({
    policy: loadAgingPolicy().policy,
    turnIndex: 14,
    registry: { tracked_items: [agedItem] },
    lhARegistryItems: [agedItem],
  });
  gates.push(gate('AG27_valid_opportunity_still_works', agedItem.opportunity_eligible === true && schedReady.fired === true, { agedItem, schedReady }));

  const cmpRun2 = assertPairedComparability({
    fixture,
    turnIndex: 5,
    establishmentRecordsA: { 'TRK-AYA-DORMANT-RECORD': { move_text: RUN2_T5_A_MOVE, player_stimulus: RUN2_STIM, turn_index: 5 } },
    establishmentRecordsB: { 'TRK-AYA-DORMANT-RECORD': { move_text: RUN2_T5_B_MOVE, player_stimulus: RUN2_STIM, turn_index: 5 } },
    trackedItemId: 'TRK-AYA-DORMANT-RECORD',
  });
  gates.push(gate('AG28_early_establishment_integrity', cmpRun2.pass === true && cmpRun2.bilateral_omission === true, cmpRun2));

  const run2Regression = {
    bilateral_omission: run2Pair.bilateral_omission,
    no_stop_c_prose_diff: cmpRun2.pass && !cmpRun2.paired?.stop_c,
    contamination: checkPersistencePreestablishmentContamination(
      { ...dormant, establishment_state: ESTABLISHMENT_STATES.UNESTABLISHED },
      { persistencePresent: true, turnIndex: 5, arm: 'lh_b' },
    ),
  };

  return { gates, run2Regression };
}

export function syntheticEstablishedRegistryItem(fixture, trackedItemId) {
  const item = trackedItemById(fixture, trackedItemId);
  return withSyntheticPairedEstablishment({ ...item, aging_history: [] });
}

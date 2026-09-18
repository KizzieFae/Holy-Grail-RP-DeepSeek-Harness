/**
 * Issue #201 — information-aging apparatus qualification (AG1–AG16).
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { buildLh0ArmConfig, LH0_ARMS } from './issue201-lh0-arms.mjs';
import { evaluateCharacterForkAtTurn } from './issue201-lh1b-causal-classifier.mjs';
import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import { runLh1bApparatusValidationSuite } from './issue201-lh1b-validation-lib.mjs';
import { runR5ApparatusQualification } from './issue201-r5-qualification-lib.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import { AGING_SCHEMAS, AGING_STATES, AGING_DEFAULT_MAX_TURNS, AGING_STOP_REASONS } from './issue201-aging-contract.mjs';
import {
  buildTrackedItemRegistry,
  loadAgingFixtureManifest,
  loadAgingPolicy,
  trackedItemById,
  forkShapeForTrackedItem,
} from './issue201-aging-fixtures.mjs';
import {
  applyAgingObservation,
  classifyTrackedItemAvailability,
  confirmAgingFromConsecutiveObservations,
} from './issue201-aging-monitor.mjs';
import {
  resolvePlayerStimulusForTurn,
  stimulusLeakageCheckForOpportunity,
} from './issue201-aging-scheduler.mjs';
import {
  lhBCannotSelfTriggerOpportunity,
  syncLhBOpportunityEligibility,
} from './issue201-aging-paired.mjs';
import { evaluateCampaignStop, markItemTested } from './issue201-aging-stopping.mjs';
import { executeR5MockSequence } from './issue201-r5-live-lib.mjs';
import { buildR5CampaignPlan } from './issue201-r5-orchestrator.mjs';
import { loadR5FixtureManifest } from './issue201-r5-fixtures.mjs';
import { evaluateSemanticEstablishment } from './issue201-aging-establishment.mjs';
import {
  runEstablishmentQualificationGates,
  syntheticEstablishedRegistryItem,
} from './issue201-aging-qualification-establishment.mjs';
import { ESTABLISHMENT_STATES } from './issue201-aging-contract.mjs';

function gate(name, pass, detail = null) {
  return { name, pass, detail };
}

function syntheticManifest({ transcript = '', retrieval = '', continuity = null, persistence = null }) {
  const contributions = [];
  if (transcript) {
    contributions.push({
      source_kind: 'recent_scene_transcript',
      content: transcript,
    });
  }
  if (retrieval) {
    contributions.push({
      source_kind: 'indexed_retrieval',
      content: retrieval,
    });
  }
  if (continuity) {
    contributions.push({
      source_kind: 'scene_context',
      content: continuity,
    });
  }
  if (persistence) {
    const obligationId = persistence.obligation_id;
    const text = persistence.text ?? String(persistence);
    contributions.push({
      source_kind: 'active_constraints',
      content: text,
      provenance: { lh0_obligation_id: obligationId, finalized_projection: true },
      knowledge_ids: [`lh0-obligation:${obligationId}`],
    });
  }
  return { contributions };
}

function buildR5PantryMockOverrides() {
  const r5 = loadR5FixtureManifest();
  const est = r5.establishment;
  const MOVE_BASE = {
    move_schema_version: 2,
    beats: [{ type: 'action', action: 'considers the question carefully' }],
    motivation: { goal: 'respond', tactic: 'measured', emotional_driver: 'neutral', risk_level: 'low' },
    semantic_evaluation: { decision: 'no_covered_change' },
  };
  const generic = {
    forceMockInferenceProfiles: true,
    beatOptions: {
      mockCharacterResponses: [JSON.stringify(MOVE_BASE)],
      mockNarratorResponses: ['Ayame regarded the applicant with measured attention.'],
    },
  };
  const byTurn = {};
  for (let t = 1; t <= r5.turns; t += 1) byTurn[t] = { ...generic };
  const dialogue = est.character_move_dialogue;
  byTurn[est.turn_index] = {
    forceMockInferenceProfiles: true,
    beatOptions: {
      mockCharacterResponses: [JSON.stringify({
        ...MOVE_BASE,
        beats: [{ type: 'speech', dialogue }],
      })],
      mockNarratorResponses: [`Ayame said, "${dialogue}"`],
    },
  };
  return byTurn;
}

export async function runAgingPantryRegression({ evidenceRoot = null } = {}) {
  const root = evidenceRoot ?? fs.mkdtempSync(path.join(os.tmpdir(), 'aging-pantry-'));
  const agingFixture = loadAgingFixtureManifest();
  const item = trackedItemById(agingFixture, 'TRK-AYA-MEAL-ALCOVE');
  const planA = buildR5CampaignPlan().sequences.find((s) => s.blind_label === 'R5-A1');
  const seq = await executeR5MockSequence({
    sequencePlan: planA,
    evidenceRoot: root,
    mockOverridesByTurn: buildR5PantryMockOverrides(),
    forceMockInferenceProfiles: true,
  });
  const t14 = seq.turns?.find((t) => t.turn_index === 14);
  const t6 = seq.turns?.find((t) => t.turn_index === 6);
  const estT6 = evaluateSemanticEstablishment(item, `${t6?.move_text ?? ''}\n${t6?.presentation_text ?? ''}`);
  const obs = classifyTrackedItemAvailability({
    fixture: agingFixture,
    trackedItem: item,
    assembledRequest: t14?.assembled_request_character,
    playerStimulus: t14?.exact_player_stimulus ?? '',
    continuitySnapshot: t14?.continuity_snapshot,
  });
  let registry = buildTrackedItemRegistry(agingFixture);
  let regItem = syntheticEstablishedRegistryItem(agingFixture, item.tracked_item_id);
  regItem = {
    ...regItem,
    establishment_state: estT6.established ? ESTABLISHMENT_STATES.ESTABLISHED : regItem.establishment_state,
    aging_clock_started: estT6.established,
    aging_clock_start_turn_a: estT6.established ? 6 : null,
  };
  for (const t of seq.turns ?? []) {
    if (t.turn_index < 6) continue;
    const o = classifyTrackedItemAvailability({
      fixture: agingFixture,
      trackedItem: item,
      assembledRequest: t.assembled_request_character,
      playerStimulus: t.exact_player_stimulus ?? '',
      continuitySnapshot: t.continuity_snapshot,
    });
    regItem = applyAgingObservation({
      registryItem: regItem,
      observation: o,
      turnIndex: t.turn_index,
      arm: 'lh_a',
    });
  }
  const { policy } = loadAgingPolicy();
  const sched = resolvePlayerStimulusForTurn({
    policy,
    turnIndex: 14,
    registry: { tracked_items: [regItem] },
    lhARegistryItems: [regItem],
  });
  return {
    seq_ok: !seq.failed,
    t6_establishment_match: Boolean(t6?.move_text?.includes('pantry alcove')),
    t14_observation: obs,
    t14_state: regItem.aging_state,
    scheduler: sched,
    t6_semantic_establishment: estT6,
    pass: estT6.established === true
      && obs.availability_state === AGING_STATES.PRESENT_RAW
      && sched.fired === false
      && regItem.opportunity_eligible !== true,
  };
}

export async function runAgingApparatusQualification({ evidenceRoot = null, skipPantryRegression = false } = {}) {
  const fixture = loadAgingFixtureManifest();
  const { policy } = loadAgingPolicy();
  const gates = [];
  const registry = buildTrackedItemRegistry(fixture);
  const itemA = trackedItemById(fixture, 'TRK-AYA-MEAL-ALCOVE');
  const itemB = trackedItemById(fixture, 'TRK-AYA-PROMISE-GATE');
  const itemC = trackedItemById(fixture, 'TRK-AYA-DORMANT-RECORD');

  gates.push(gate('AG1_tracked_establishment', itemA.establishment_turn === 6
    && itemB.establishment_turn === 8
    && itemC.establishment_turn === 5, {
    turns: { a: 6, b: 8, c: 5 },
  }));

  const r5Manifest = loadR5FixtureManifest();
  const pantryObs = classifyTrackedItemAvailability({
    fixture,
    trackedItem: itemA,
    assembledRequest: {
      contributions: [
        { source_kind: 'recent_scene_transcript', content: 'Ayame: For your trial week, meals for staff are taken in the pantry alcove off this corridor.' },
      ],
    },
    playerStimulus: 'neutral',
  });
  gates.push(gate('AG2_proposition_detectable', pantryObs.availability_state === AGING_STATES.PRESENT_RAW, pantryObs));

  let regA = syntheticEstablishedRegistryItem(fixture, itemA.tracked_item_id);
  const obsRaw = classifyTrackedItemAvailability({
    fixture,
    trackedItem: itemA,
    assembledRequest: syntheticManifest({
      transcript: 'pantry alcove trial week household dining table guests formal meal',
    }),
  });
  regA = applyAgingObservation({ registryItem: regA, observation: obsRaw, turnIndex: 10 });
  const obsLean = classifyTrackedItemAvailability({
    fixture,
    trackedItem: itemA,
    assembledRequest: syntheticManifest({
      transcript: 'tea tray and linens only',
      retrieval: 'trial staff take meals in the staff pantry alcove',
    }),
  });
  regA = applyAgingObservation({ registryItem: regA, observation: obsLean, turnIndex: 20 });
  gates.push(gate('AG3_lifecycle_transitions', regA.aging_state === AGING_STATES.PRESENT_LEAN_OTHER
    && obsRaw.availability_state === AGING_STATES.PRESENT_RAW, {
    after_raw: obsRaw.availability_state,
    after_lean: obsLean.availability_state,
  }));

  const regRaw = applyAgingObservation({
    registryItem: { ...regA, aging_history: [] },
    observation: obsRaw,
    turnIndex: 14,
  });
  const schedRaw = resolvePlayerStimulusForTurn({
    policy,
    turnIndex: 14,
    registry: { tracked_items: [regRaw] },
    lhARegistryItems: [regRaw],
  });
  gates.push(gate('AG4_no_opportunity_present_raw', schedRaw.fired === false, schedRaw));

  const regLean = applyAgingObservation({
    registryItem: { ...regA, aging_history: [] },
    observation: obsLean,
    turnIndex: 21,
  });
  const schedLean = resolvePlayerStimulusForTurn({
    policy,
    turnIndex: 14,
    registry: { tracked_items: [regLean] },
    lhARegistryItems: [regLean],
  });
  gates.push(gate('AG5_no_opportunity_lean_other', schedLean.fired === false, schedLean));

  const obsAged1 = classifyTrackedItemAvailability({
    fixture,
    trackedItem: itemA,
    assembledRequest: syntheticManifest({ transcript: 'Ayame: The blue service is ready. Kizzie: Thank you.' }),
  });
  const obsAged2 = classifyTrackedItemAvailability({
    fixture,
    trackedItem: itemA,
    assembledRequest: syntheticManifest({ transcript: 'Kizzie: Shall I fold the linens? Ayame: After tea.' }),
  });
  let regAged = { ...regA, aging_history: [] };
  regAged = applyAgingObservation({ registryItem: regAged, observation: obsAged1, turnIndex: 30 });
  regAged = applyAgingObservation({ registryItem: regAged, observation: obsAged2, turnIndex: 31 });
  const schedAged = resolvePlayerStimulusForTurn({
    policy,
    turnIndex: 14,
    registry: { tracked_items: [regAged] },
    lhARegistryItems: [regAged],
  });
  gates.push(gate('AG6_aged_out_permits_pending', confirmAgingFromConsecutiveObservations(obsAged1, obsAged2)
    && regAged.opportunity_eligible === true, {
    reg: regAged,
    sched: schedAged,
  }));

  gates.push(gate('AG7_persistence_provenance',
    syntheticManifest({
      persistence: { obligation_id: itemA.obligation_id, text: itemA.semantic_proposition },
    }).contributions[0]?.provenance?.lh0_obligation_id === itemA.obligation_id));

  const leak = stimulusLeakageCheckForOpportunity(itemA, itemA.opportunity.stimulus);
  gates.push(gate('AG8_stimulus_neutrality', leak.pass, leak));

  const evalFixture = {
    obligations: fixture.obligations,
    causal_design: { decision_forks: [forkShapeForTrackedItem(itemA, 40)] },
  };
  const posMove = 'Staff meals stay in the pantry alcove, not at the household dining table during guest meals.';
  const persistManifest = syntheticManifest({
    persistence: { obligation_id: itemA.obligation_id, text: itemA.semantic_proposition },
  });
  const forkEval = evaluateCharacterForkAtTurn({
    fixture: evalFixture,
    turnIndex: 40,
    manifest: persistManifest,
    finalizedProjection: persistManifest,
    moveText: posMove,
    playerStimulus: itemA.opportunity.stimulus,
    storeSnapshot: { obligations: [{ obligation_id: itemA.obligation_id }] },
  })[0];
  gates.push(gate('AG9_r0_r5_classification', forkEval?.r_stages?.stages?.R2_semantically_received === true
    && forkEval?.causal_evidence?.decision_influenced === true, {
    r_stages: forkEval?.r_stages,
    received: forkEval?.received_obligation_ids,
  }));

  const lhA = buildLh0ArmConfig(LH0_ARMS.LH_A);
  const lhB = buildLh0ArmConfig(LH0_ARMS.LH_B);
  gates.push(gate('AG10_arm_isolation', lhA.persistent_cognition_enabled === false
    && lhB.persistent_cognition_enabled === true));

  const regLhA = { tracked_items: [regAged] };
  const regLhB = syncLhBOpportunityEligibility(
    { tracked_items: [{ ...itemA, opportunity_eligible: false, aging_state: AGING_STATES.PRESENT_RAW }] },
    regLhA,
  );
  gates.push(gate('AG11_lh_a_authoritative',
    regLhA.tracked_items[0].opportunity_eligible === true
    && regLhB.tracked_items[0].opportunity_eligible === regLhA.tracked_items[0].opportunity_eligible, {
    a: regLhA.tracked_items[0].opportunity_eligible,
    b: regLhB.tracked_items[0].opportunity_eligible,
  }));

  const bSelfTriggerViolation = lhBCannotSelfTriggerOpportunity(
    { tracked_items: [{ ...itemA, opportunity_eligible: true }] },
    { tracked_items: [{ ...itemA, opportunity_eligible: false }] },
    itemA.tracked_item_id,
  );
  const bSelfTriggerOk = lhBCannotSelfTriggerOpportunity(
    { tracked_items: [{ ...itemA, opportunity_eligible: false }] },
    { tracked_items: [{ ...itemA, opportunity_eligible: false }] },
    itemA.tracked_item_id,
  );
  gates.push(gate('AG12_b_cannot_self_trigger', bSelfTriggerViolation.pass === false
    && bSelfTriggerOk.pass === true, {
    violation: bSelfTriggerViolation,
    ok: bSelfTriggerOk,
  }));

  const estGates = runEstablishmentQualificationGates();
  gates.push(...estGates.gates);
  gates.push(gate('AG13_divergence_fail_closed', estGates.run2Regression.no_stop_c_prose_diff === true, estGates.run2Regression));

  const stopA = evaluateCampaignStop({
    turnIndex: 50,
    registryLhA: { tracked_items: [markItemTested(itemA, 45)] },
    testedItems: [{ tracked_item_id: itemA.tracked_item_id, clean_aging_evidence: true, interpretable: true }],
  });
  gates.push(gate('AG14_stop_a_after_clean_tested', stopA.stop && stopA.reason === AGING_STOP_REASONS.STOP_A_CLEAN_RESULT, stopA));

  const stopB = evaluateCampaignStop({
    turnIndex: AGING_DEFAULT_MAX_TURNS,
    maxTurns: AGING_DEFAULT_MAX_TURNS,
    registryLhA: { tracked_items: [itemA] },
    testedItems: [],
  });
  gates.push(gate('AG15_stop_b_max_boundary', stopB.stop && stopB.reason === AGING_STOP_REASONS.STOP_B_MAX_BOUNDARY, stopB));

  let pantry = { pass: true, skipped: true };
  if (!skipPantryRegression) {
    pantry = await runAgingPantryRegression({ evidenceRoot });
    gates.push(gate('AG16_pantry_t14_regression', pantry.pass, pantry));
  } else {
    gates.push(gate('AG16_pantry_t14_regression', true, { skipped: true, note: 'use skipPantryRegression:false for runner path' }));
  }

  const r5App = runR5ApparatusQualification();
  const lh1bApp = runLh1bApparatusValidationSuite();

  const failures = gates.filter((g) => !g.pass).map((g) => g.name);
  return {
    schema: AGING_SCHEMAS.QUALIFICATION,
    pass: failures.length === 0 && r5App.pass && lh1bApp.pass,
    establishment_regression: estGates.run2Regression,
    candidate_sha: gitSha(),
    gates,
    failures,
    pantry_regression: pantry,
    mock_cases: {
      raw_retention: obsRaw,
      retrieval_preservation: obsLean,
      true_aged_out: obsAged2,
      persistence_survival: syntheticManifest({
        persistence: { obligation_id: itemA.obligation_id, text: itemA.semantic_proposition },
      }),
      paired_opportunity: schedAged,
    },
    r5_apparatus_regression: r5App.pass,
    lh1b_apparatus_regression: lh1bApp.pass,
    live_authorized: false,
  };
}


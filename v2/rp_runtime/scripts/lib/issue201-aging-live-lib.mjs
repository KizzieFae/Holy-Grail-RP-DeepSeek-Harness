/**
 * Issue #201 — live information-aging campaign (LH-A authoritative, paired stimuli).
 */
import fs from 'node:fs';
import path from 'node:path';

import { HolyGrailApplicationClient } from '../../src/application/hg-application-client.mjs';
import { G3_SCENARIOS } from './issue201-g3-scenarios.mjs';
import { buildLh0ArmConfig, LH0_ARMS } from './issue201-lh0-arms.mjs';
import { writeLh0Store, readLh0Store, lh0StorePath } from './issue201-lh0-persistent-store.mjs';
import { defaultSessionsDir } from '../../src/lib/runtime-config.mjs';
import { gitSha } from './issue201-lh0-lib.mjs';
import {
  AGING_DEFAULT_MAX_TURNS,
  AGING_SCHEMAS,
  AGING_STATES,
  AGING_STOP_REASONS,
} from './issue201-aging-contract.mjs';
import {
  buildTrackedItemRegistry,
  expandAgingPolicyTurns,
  forkShapeForTrackedItem,
  loadAgingFixtureManifest,
  loadAgingPolicy,
  sha256File,
  trackedItemById,
} from './issue201-aging-fixtures.mjs';
import { AGING_FIXTURE_ROOT } from './issue201-aging-fixtures.mjs';
import {
  applyAgingObservation,
  applyPersistenceObservation,
  buildTranscriptObservationRecord,
  classifyTrackedItemAvailability,
} from './issue201-aging-monitor.mjs';
import {
  resolvePlayerStimulusForTurn,
  stimulusLeakageCheckForOpportunity,
} from './issue201-aging-scheduler.mjs';
import { assertPairedComparability } from './issue201-aging-paired.mjs';
import { evaluateCampaignStop } from './issue201-aging-stopping.mjs';
import { runLh1bTurn } from './issue201-lh1b-live-lib.mjs';
import { evaluateCharacterForkAtTurn } from './issue201-lh1b-causal-classifier.mjs';
import { attemptsToInferenceEvents, buildLh1bCostRollup } from './issue201-lh1b-cost-accounting.mjs';
import { runAgingApparatusQualification } from './issue201-aging-qualification-lib.mjs';

const SCENARIO = G3_SCENARIOS.ayame_controlled;
export const AGING_APPARATUS_CANDIDATE_SHA = '94cba2d054a058c1e8dfff8621f37a51fae730f2';

const INTERVENING_REALIZATIONS = [
  'Kizzie asks whether the pantry stores should be inventoried before the weekend.',
  'Kizzie offers to air the guest-room linens while the weather is dry.',
  'Kizzie mentions the front hall clock needs winding and asks if that is within staff duties.',
  'Kizzie asks whether visitors usually arrive through the main entrance or the service door.',
  'Kizzie offers to polish the foyer table before the household receives mail.',
  'Kizzie asks if there are household pets she should account for during rounds.',
  'Kizzie asks whether the kitchen range has been serviced recently.',
  'Kizzie offers to reorganize the coat closet if it would help.',
];

async function verifyAgingLiveAnchor() {
  const fixturePath = path.join(AGING_FIXTURE_ROOT, 'ayame_aging_fixture_v1.json');
  const measured = { fixture_hash: sha256File(fixturePath) };
  const qual = await runAgingApparatusQualification({ skipPantryRegression: true });
  return {
    pass: qual.pass,
    execution_sha: gitSha(),
    apparatus_candidate_sha: AGING_APPARATUS_CANDIDATE_SHA,
    fixture_hash: measured.fixture_hash,
  };
}

async function createLiveClient(evidenceRoot, sessionsDir) {
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: { mountDeepSeek: true, executionEvidence: { enabled: true, root: evidenceRoot } },
      sessionsDir,
    },
  });
  await client.start();
  const openers = await client.listTemplateOpeners(SCENARIO.id);
  await client.createSession({
    characters: SCENARIO.characters,
    sceneTemplateId: SCENARIO.id,
    roleAssignments: SCENARIO.roleAssignments,
    playerCharacterFileId: SCENARIO.playerCharacterFileId,
    userPersonaId: SCENARIO.userName,
    opening: { mode: 'template', opener_id: openers[0].opener_id },
  });
  return client;
}

function updateRegistryForTurn({
  fixture,
  registry,
  turnRow,
  turnIndex,
  arm,
}) {
  const items = registry.tracked_items.map((item) => {
    if (turnIndex < item.establishment_turn) return item;
    const obs = classifyTrackedItemAvailability({
      fixture,
      trackedItem: item,
      assembledRequest: turnRow.assembled_request_character,
      playerStimulus: turnRow.exact_player_stimulus ?? '',
      continuitySnapshot: turnRow.continuity_snapshot,
    });
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
  });
  return { ...registry, tracked_items: items };
}

function evaluateTestedItem({
  fixture,
  trackedItemId,
  turnIndex,
  turnRowA,
  turnRowB,
  storeB,
}) {
  const item = trackedItemById(fixture, trackedItemId);
  const evalFixture = {
    obligations: fixture.obligations,
    causal_design: { decision_forks: [forkShapeForTrackedItem(item, turnIndex)] },
  };
  const manifestB = turnRowB?.assembled_request_character
    ? { contributions: turnRowB.assembled_request_character.contributions ?? [] }
    : null;
  const persistParts = (manifestB?.contributions ?? []).filter(
    (c) => c?.provenance?.lh0_obligation_id === item.obligation_id,
  );
  const forkEval = manifestB ? evaluateCharacterForkAtTurn({
    fixture: evalFixture,
    turnIndex,
    manifest: manifestB,
    finalizedProjection: persistParts.length ? { contributions: persistParts } : null,
    moveText: turnRowB.move_text ?? '',
    presentationText: turnRowB.presentation_text ?? '',
    playerStimulus: turnRowB.exact_player_stimulus ?? '',
    storeSnapshot: storeB,
  })[0] : null;
  const obsA = classifyTrackedItemAvailability({
    fixture,
    trackedItem: item,
    assembledRequest: turnRowA.assembled_request_character,
    playerStimulus: turnRowA.exact_player_stimulus ?? '',
    continuitySnapshot: turnRowA.continuity_snapshot,
  });
  return { forkEval, leanAtTestA: obsA, item };
}

export async function executeAgingLiveCampaign({
  outputDir,
  liveAuthorized = false,
  maxTurns = AGING_DEFAULT_MAX_TURNS,
}) {
  if (!liveAuthorized) {
    throw new Error('Information-aging live campaign not authorized');
  }
  const anchor = await verifyAgingLiveAnchor();
  if (!anchor.pass) {
    throw new Error(`Aging live anchor failed: ${JSON.stringify(anchor)}`);
  }

  fs.mkdirSync(outputDir, { recursive: true });
  const startedAt = new Date().toISOString();
  const fixture = loadAgingFixtureManifest();
  const { policy: basePolicy, policy_hash } = loadAgingPolicy();
  const policy = expandAgingPolicyTurns(basePolicy, maxTurns);
  const sessionsDir = defaultSessionsDir();
  const evidenceRoot = outputDir;
  const frozenHashGate = { pass: true, measured: anchor };

  let registryA = buildTrackedItemRegistry(fixture);
  const stimuliByTurn = {};
  const turnsA = [];
  const agingTimeline = [];
  let pendingFireItemId = null;
  let stopReason = null;
  let testedRecord = null;
  let failClosed = null;
  const establishmentA = {};
  const establishmentB = {};

  const clientA = await createLiveClient(evidenceRoot, sessionsDir);
  const hgSessionA = clientA.activeSessionId;
  const armConfigA = buildLh0ArmConfig(LH0_ARMS.LH_A);
  const sequenceIdA = `AGING-LIVE-LH-A-${Date.now()}`;

  try {
    for (let turnIndex = 1; turnIndex <= maxTurns; turnIndex += 1) {
      let sched;
      let testingItemId = null;
      if (pendingFireItemId) {
        const item = trackedItemById(fixture, pendingFireItemId);
        sched = {
          stimulus: item.opportunity.stimulus,
          fired: true,
          gated: true,
          tracked_item_id: pendingFireItemId,
        };
        testingItemId = pendingFireItemId;
        pendingFireItemId = null;
      } else {
        sched = resolvePlayerStimulusForTurn({
          policy,
          turnIndex,
          registry: registryA,
          lhARegistryItems: registryA.tracked_items,
        });
        if (sched.fired) testingItemId = sched.tracked_item_id;
      }
      stimuliByTurn[turnIndex] = sched.stimulus;

      const turnRow = await runLh1bTurn({
        client: clientA,
        armConfig: armConfigA,
        fixture,
        scenario: SCENARIO,
        turnIndex,
        playerStimulus: sched.stimulus,
        sceneId: null,
        sequenceId: sequenceIdA,
        evidenceRoot,
        sessionsDir,
        frozenHashGate,
      });
      turnsA.push({ ...turnRow, scheduler: sched, testing_item_id: testingItemId });
      if (!turnRow.committed) {
        failClosed = { reason: 'terminal_beat_failure', turn_index: turnIndex, arm: 'lh_a' };
        stopReason = AGING_STOP_REASONS.STOP_C_FAIL_CLOSED;
        break;
      }

      const beforePending = registryA.tracked_items.filter((t) => t.opportunity_eligible).map((t) => t.tracked_item_id);
      registryA = updateRegistryForTurn({
        fixture,
        registry: registryA,
        turnRow,
        turnIndex,
        arm: LH0_ARMS.LH_A,
      });
      const afterPending = registryA.tracked_items.filter((t) => t.opportunity_eligible).map((t) => t.tracked_item_id);
      const newlyPending = afterPending.filter((id) => !beforePending.includes(id));

      for (const item of fixture.tracked_items) {
        if (item.establishment_turn === turnIndex) {
          establishmentA[item.tracked_item_id] = {
            player_stimulus: turnRow.exact_player_stimulus,
            move_text: turnRow.move_text,
          };
        }
      }

      const obsRecord = buildTranscriptObservationRecord(
        registryA,
        turnIndex,
        Object.fromEntries(
          registryA.tracked_items.map((t) => [
            t.tracked_item_id,
            classifyTrackedItemAvailability({
              fixture,
              trackedItem: t,
              assembledRequest: turnRow.assembled_request_character,
              playerStimulus: turnRow.exact_player_stimulus ?? '',
              continuitySnapshot: turnRow.continuity_snapshot,
            }),
          ]),
        ),
      );
      agingTimeline.push(obsRecord);

      if (testingItemId && sched.fired) {
        const leak = stimulusLeakageCheckForOpportunity(
          trackedItemById(fixture, testingItemId),
          sched.stimulus,
        );
        testedRecord = {
          tracked_item_id: testingItemId,
          turn_index: turnIndex,
          scheduler: sched,
          stimulus_leakage: leak,
          awaiting_arm_b: true,
        };
        registryA = {
          ...registryA,
          tracked_items: registryA.tracked_items.map((t) => (
            t.tracked_item_id === testingItemId
              ? { ...t, aging_state: AGING_STATES.TESTED, tested_turn: turnIndex }
              : t
          )),
        };
        stopReason = AGING_STOP_REASONS.STOP_A_CLEAN_RESULT;
        break;
      }

      if (newlyPending.length && !pendingFireItemId) {
        pendingFireItemId = newlyPending[0];
      }

      const stopB = evaluateCampaignStop({
        turnIndex,
        maxTurns,
        registryLhA: registryA,
        testedItems: [],
      });
      if (stopB.stop && stopB.reason === AGING_STOP_REASONS.STOP_B_MAX_BOUNDARY) {
        stopReason = stopB.reason;
        break;
      }
    }
  } finally {
    await clientA.stop();
  }

  if (!stopReason && failClosed) stopReason = AGING_STOP_REASONS.STOP_C_FAIL_CLOSED;
  if (!stopReason) stopReason = AGING_STOP_REASONS.STOP_B_MAX_BOUNDARY;

  const lastTurnA = turnsA.length;
  const turnsB = [];
  const clientB = await createLiveClient(evidenceRoot, sessionsDir);
  const hgSessionB = clientB.activeSessionId;
  const armConfigB = buildLh0ArmConfig(LH0_ARMS.LH_B);
  writeLh0Store(sessionsDir, hgSessionB, {
    schema: 'issue201_lh0_persistent_store_v1',
    campaign: 'aging_live',
    fixture_id: fixture.fixture_id,
    obligations: [],
    events: [],
  });
  const sequenceIdB = `AGING-LIVE-LH-B-${Date.now()}`;

  try {
    for (let turnIndex = 1; turnIndex <= lastTurnA; turnIndex += 1) {
      const stimulus = stimuliByTurn[turnIndex];
      const turnRow = await runLh1bTurn({
        client: clientB,
        armConfig: armConfigB,
        fixture,
        scenario: SCENARIO,
        turnIndex,
        playerStimulus: stimulus,
        sceneId: null,
        sequenceId: sequenceIdB,
        evidenceRoot,
        sessionsDir,
        frozenHashGate,
      });
      turnsB.push(turnRow);
      if (!turnRow.committed) {
        failClosed = { reason: 'terminal_beat_failure', turn_index: turnIndex, arm: 'lh_b' };
        stopReason = AGING_STOP_REASONS.STOP_C_FAIL_CLOSED;
        break;
      }
      for (const item of fixture.tracked_items) {
        if (item.establishment_turn === turnIndex) {
          establishmentB[item.tracked_item_id] = {
            player_stimulus: turnRow.exact_player_stimulus,
            move_text: turnRow.move_text,
          };
        }
      }
    }
  } finally {
    await clientB.stop();
  }

  const storeB = readLh0Store(sessionsDir, hgSessionB);
  let pairedComparability = { pass: true };
  for (const item of fixture.tracked_items) {
    const cmp = assertPairedComparability({
      turnIndex: item.establishment_turn,
      establishmentRecordsA: establishmentA,
      establishmentRecordsB: establishmentB,
      trackedItemId: item.tracked_item_id,
    });
    if (!cmp.pass) pairedComparability = cmp;
  }

  if (!pairedComparability.pass && stopReason === AGING_STOP_REASONS.STOP_A_CLEAN_RESULT) {
    stopReason = AGING_STOP_REASONS.STOP_C_FAIL_CLOSED;
    failClosed = pairedComparability;
  }

  if (testedRecord?.awaiting_arm_b) {
    const tIdx = testedRecord.turn_index;
    const rowA = turnsA.find((t) => t.turn_index === tIdx);
    const rowB = turnsB.find((t) => t.turn_index === tIdx);
    const evalResult = evaluateTestedItem({
      fixture,
      trackedItemId: testedRecord.tracked_item_id,
      turnIndex: tIdx,
      turnRowA: rowA,
      turnRowB: rowB,
      storeB,
    });
    testedRecord = { ...testedRecord, ...evalResult, awaiting_arm_b: false };
  }

  const inferenceEventsA = turnsA.flatMap((t) => (t.inference?.events ?? []).map((e) => ({ ...e, turn_index: t.turn_index })));
  const inferenceEventsB = turnsB.flatMap((t) => (t.inference?.events ?? []).map((e) => ({ ...e, turn_index: t.turn_index })));
  const costA = buildLh1bCostRollup({ arm: LH0_ARMS.LH_A, sequenceId: sequenceIdA, inferenceEvents: attemptsToInferenceEvents(inferenceEventsA) });
  const costB = buildLh1bCostRollup({ arm: LH0_ARMS.LH_B, sequenceId: sequenceIdB, inferenceEvents: attemptsToInferenceEvents(inferenceEventsB) });

  const endedAt = new Date().toISOString();
  const report = {
    schema: AGING_SCHEMAS.QUALIFICATION,
    campaign: 'issue201_information_aging_live_v1',
    execution_sha: gitSha(),
    apparatus_candidate_sha: AGING_APPARATUS_CANDIDATE_SHA,
    policy_hash,
    started_at: startedAt,
    ended_at: endedAt,
    stop_reason: stopReason,
    fail_closed: failClosed,
    hg_session_id_lh_a: hgSessionA,
    hg_session_id_lh_b: hgSessionB,
    turns_completed_a: turnsA.length,
    turns_completed_b: turnsB.length,
    registry_lh_a_final: registryA,
    aging_timeline: agingTimeline,
    stimuli_by_turn: stimuliByTurn,
    turns_lh_a: turnsA,
    turns_lh_b: turnsB,
    establishment_a: establishmentA,
    establishment_b: establishmentB,
    paired_comparability: pairedComparability,
    tested_record: testedRecord,
    cost_rollup_a: costA,
    cost_rollup_b: costB,
    lh0_store_b_path: lh0StorePath(sessionsDir, hgSessionB),
    output_dir: outputDir,
    live_authorized: true,
  };

  fs.writeFileSync(path.join(outputDir, 'issue201-aging-live-campaign-report.json'), JSON.stringify(report, null, 2));
  fs.writeFileSync(path.join(outputDir, 'aging_timeline.jsonl'), agingTimeline.map((r) => JSON.stringify(r)).join('\n'));
  return report;
}

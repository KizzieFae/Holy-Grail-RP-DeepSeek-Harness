/**
 * Issue #201 LH-1B — runner-level mock qualification through authoritative turn path.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { HolyGrailApplicationClient } from '../../src/application/hg-application-client.mjs';
import { buildLh0ArmConfig, LH0_ARMS } from './issue201-lh0-arms.mjs';
import { loadLh1bFixtureManifest, forkForTurn } from './issue201-lh1b-fixtures.mjs';
import { buildLh1bCampaignPlan } from './issue201-lh1b-orchestrator.mjs';
import { LH1B_SCHEMAS } from './issue201-lh1b-contract.mjs';
import { classifyActualSubstrateUniqueness } from './issue201-lh1b-substrate-uniqueness.mjs';
import {
  runLh1bTurn,
  verifyLh1bFrozenHashes,
  buildLh1bBeatOptions,
  LH1B_TURN_ORDERING,
} from './issue201-lh1b-live-lib.mjs';
import { G3_SCENARIOS } from './issue201-g3-scenarios.mjs';
import { writeLh0Store, classifyLh0ObligationStates } from './issue201-lh0-persistent-store.mjs';
import { seedLh0ObligationFromFixture } from './issue201-lh0-semantic-content.mjs';
import { defaultSessionsDir } from '../../src/lib/runtime-config.mjs';

const SCENARIO = G3_SCENARIOS.ayame_controlled;
const FIXTURE = loadLh1bFixtureManifest();

const MOVE_BASE = {
  move_schema_version: 2,
  beats: [{ type: 'action', action: 'considers carefully' }],
  motivation: { goal: 'respond', tactic: 'measured', emotional_driver: 'neutral', risk_level: 'low' },
  semantic_evaluation: { decision: 'no_covered_change' },
};

function charMove(dialogue) {
  return JSON.stringify({
    ...MOVE_BASE,
    beats: [{ type: 'speech', dialogue }],
  });
}

const DIRECTOR_ESCALATE = JSON.stringify({
  next_actor: 'Ayame',
  end_round: false,
  reason: 'Threshold compensation remains unresolved; applicant not yet seated for full terms.',
  environment_event: '',
  tension_shift: 'escalate',
});

const DIRECTOR_SOFTEN = JSON.stringify({
  next_actor: 'Ayame',
  end_round: false,
  reason: 'Comfortable enough to move on.',
  environment_event: '',
  tension_shift: 'soften',
});

async function createQualificationClient(evidenceRoot) {
  const client = new HolyGrailApplicationClient({
    inferenceMode: 'live',
    runtime: {
      inference: {
        mountDeepSeek: true,
        executionEvidence: { enabled: true, root: evidenceRoot },
      },
    },
  });
  await client.start();
  const openers = await client.listTemplateOpeners(SCENARIO.id);
  return { client, openerId: openers[0].opener_id };
}

async function withMockSession({ arm, evidenceRoot, client, openerId, fn }) {
  const armConfig = buildLh0ArmConfig(arm);
  const sessionsDir = defaultSessionsDir();
  await client.createSession({
    characters: SCENARIO.characters,
    sceneTemplateId: SCENARIO.id,
    roleAssignments: SCENARIO.roleAssignments,
    playerCharacterFileId: SCENARIO.playerCharacterFileId,
    userPersonaId: SCENARIO.userName,
    opening: { mode: 'template', opener_id: openerId },
  });
  if (armConfig.persistent_cognition_enabled) {
    writeLh0Store(sessionsDir, client.activeSessionId, {
      schema: 'issue201_lh0_persistent_store_v1',
      campaign: 'lh1b_qual',
      fixture_id: FIXTURE.fixture_id,
      obligations: [],
      events: [],
    });
  }
  return fn({
    client,
    armConfig,
    fixture: FIXTURE,
    sessionsDir,
    evidenceRoot,
    scenario: SCENARIO,
  });
}

function proof(name, pass, detail = null) {
  return { name, pass, detail };
}

function seedLh1bQualificationStore(sessionsDir, hgSessionId, turnIndex, arm) {
  const obligations = FIXTURE.obligations.filter((o) => {
    if (o.negative_control) return false;
    if (arm === LH0_ARMS.LH_B && o.authorized_consumer === 'director_turn') return false;
    if (arm === LH0_ARMS.LH_A) return false;
    return true;
  });
  const store = {
    schema: 'issue201_lh0_persistent_store_v1',
    campaign: 'lh1b_qual',
    fixture_id: FIXTURE.fixture_id,
    obligations: obligations.map((o) => seedLh0ObligationFromFixture(o, {
      mechanism: 'plot_cognition_update',
      source: 'qualification_seed',
    })),
    events: [],
  };
  classifyLh0ObligationStates(store, turnIndex);
  writeLh0Store(sessionsDir, hgSessionId, store);
  return store;
}

export async function runLh1bRunnerMockQualification({ evidenceRoot = null } = {}) {
  const root = evidenceRoot ?? fs.mkdtempSync(path.join(os.tmpdir(), 'lh1b-runner-qual-'));
  fs.mkdirSync(root, { recursive: true });
  const campaignPlan = buildLh1bCampaignPlan();
  const planTurns = campaignPlan.sequences[0].turns;
  const proofs = [];
  const { client, openerId } = await createQualificationClient(root);
  const decisionMocks = {
    15: {
      beatOptions: {
        mockCharacterResponses: [charMove(
          'I cannot accept help with household accounts without noting the prior assistant was dismissed after copying ledger pages.',
        )],
      },
    },
    16: {
      beatOptions: {
        mockCharacterResponses: [charMove(
          'You committed not to enter restricted areas without written authorization from me, including the east wing.',
        )],
      },
    },
    17: {
      beatOptions: {
        mockCharacterResponses: [charMove(
          'During a trial week you receive only the pantry submaster key. The household master key is not issued.',
        )],
      },
    },
    18: {
      beatOptions: {
        mockCharacterResponses: [charMove(
          'Nightly rounds exclude the east wing because it has a separate alarm circuit and is not part of standard staff rounds.',
        )],
      },
    },
  };

  proofs.push(proof('frozen_hash_gate', verifyLh1bFrozenHashes(campaignPlan.sequences[0]).pass));
  proofs.push(proof(
    'authoritative_turn_ordering_documented',
    LH1B_TURN_ORDERING.includes('lh0_projection_transport_before_director'),
  ));

  const armSlots = [
    { arm: LH0_ARMS.LH_A, blind_label: 'S1' },
    { arm: LH0_ARMS.LH_B, blind_label: 'S2' },
    { arm: LH0_ARMS.LH_A, blind_label: 'S3' },
    { arm: LH0_ARMS.LH_B, blind_label: 'S4' },
    { arm: LH0_ARMS.LH_D, blind_label: 'S5' },
    { arm: LH0_ARMS.LH_A, blind_label: 'S6' },
  ];
  for (const seq of armSlots) {
    await withMockSession({
      arm: seq.arm,
      evidenceRoot: root,
      client,
      openerId,
      fn: async (ctx) => {
        const row = await runLh1bTurn({
          ...ctx,
          turnIndex: 1,
          playerStimulus: planTurns[0].player_stimulus,
          sceneId: planTurns[0].scene_id,
          sequenceId: `lh1b-qual-${seq.blind_label}`,
        });
        proofs.push(proof(`${seq.blind_label}_${seq.arm}_isolation`, row.arm_isolation.pass, row.arm_isolation.violations));
        if (seq.arm === LH0_ARMS.LH_A) {
          proofs.push(proof(`${seq.blind_label}_no_projection`, !row.lh1b_projection.projected));
        }
      },
    });
  }

  await withMockSession({
    arm: LH0_ARMS.LH_B,
    evidenceRoot: root,
    client,
    openerId,
    fn: async (ctx) => {
      seedLh1bQualificationStore(ctx.sessionsDir, ctx.client.activeSessionId, 14, LH0_ARMS.LH_B);
      const turnRows = {};
      for (const turnIndex of [15, 16, 17, 18]) {
        const planTurn = planTurns[turnIndex - 1];
        const row = await runLh1bTurn({
          ...ctx,
          turnIndex,
          playerStimulus: planTurn.player_stimulus,
          sceneId: planTurn.scene_id,
          sequenceId: 'lh1b-qual-lh-b-decision',
          mockOverrides: decisionMocks[turnIndex] ?? {},
        });
        turnRows[turnIndex] = row;
        if (!row.committed) throw new Error(`LH-B qualification failed at T${turnIndex}`);
      }
      const t15 = turnRows[15];
      const t16 = turnRows[16];
      const t17 = turnRows[17];
      const t18 = turnRows[18];
      proofs.push(proof('character_t15_fork_reachable', t15.causal_trace.fork_evaluations.some(
        (f) => f.fork_id === 'FORK-LH1B-DORMANT-RECORD',
      )));
      proofs.push(proof('character_t15_projection', t15.lh1b_projection.projected === true));
      proofs.push(proof('character_t15_receipt', Boolean(t15.provenance_audit?.received_obligation_ids?.length)));
      proofs.push(proof('character_t16_fork_reachable', t16.causal_trace.fork_evaluations.some(
        (f) => f.fork_id === 'FORK-LH1B-PROMISE-GATE',
      )));
      proofs.push(proof('character_t17_fork_reachable', t17.causal_trace.fork_evaluations.some(
        (f) => f.fork_id === 'FORK-LH1B-DEFERRED-KEY',
      )));
      const t17fork = t17.causal_trace.fork_evaluations.find((f) => f.fork_id === 'FORK-LH1B-DEFERRED-KEY');
      proofs.push(proof('character_mock_r3_r4_positive', t17fork?.causal_evidence?.decision_influenced === true));
      const r5Substrate = classifyActualSubstrateUniqueness({
        fixture: FIXTURE,
        fork: forkForTurn(FIXTURE, 17, { consumer: 'character_move' })[0],
        manifestContributions: [{
          source_kind: 'active_constraints',
          content: 'Trial staff receive only a pantry submaster key during a trial week.',
          provenance: { lh0_obligation_id: 'LH1B-AYA-DEFERRED-KEY' },
        }],
        playerStimulus: 'What are the evening access arrangements?',
      });
      proofs.push(proof('character_mock_r5_when_unique', r5Substrate.persistence_unique === true));
      proofs.push(proof('character_t18_fork_reachable', t18.causal_trace.fork_evaluations.some(
        (f) => f.fork_id === 'FORK-LH1B-FORESHADOW-ACCESS',
      )));

    },
  });

  await withMockSession({
    arm: LH0_ARMS.LH_B,
    evidenceRoot: root,
    client,
    openerId,
    fn: async (ctx) => {
      seedLh1bQualificationStore(ctx.sessionsDir, ctx.client.activeSessionId, 16, LH0_ARMS.LH_B);
      const t17neg = await runLh1bTurn({
        ...ctx,
        turnIndex: 17,
        playerStimulus: planTurns[16].player_stimulus,
        sceneId: planTurns[16].scene_id,
        sequenceId: 'lh1b-qual-char-t17-neg',
        stopOnFailure: false,
        mockOverrides: {
          forceMockInferenceProfiles: true,
          beatOptions: {
            mockCharacterResponses: [charMove('Of course — here is the master key from the hook; take full access for your rounds.')],
            mockNarratorResponses: ['Ayame answered without referencing trial key policy.'],
          },
        },
      });
      const t17negFork = t17neg.causal_trace.fork_evaluations.find((f) => f.fork_id === 'FORK-LH1B-DEFERRED-KEY');
      proofs.push(proof('character_negative_control', t17negFork?.causal_evidence?.decision_influenced !== true));
    },
  });

  await withMockSession({
    arm: LH0_ARMS.LH_D,
    evidenceRoot: root,
    client,
    openerId,
    fn: async (ctx) => {
      seedLh1bQualificationStore(ctx.sessionsDir, ctx.client.activeSessionId, 14, LH0_ARMS.LH_D);
      const t15 = await runLh1bTurn({
        ...ctx,
        turnIndex: 15,
        playerStimulus: planTurns[14].player_stimulus,
        sceneId: planTurns[14].scene_id,
        sequenceId: 'lh1b-qual-dir-t15',
        mockOverrides: {
          beatOptions: {
            mockDirectorResponses: [DIRECTOR_ESCALATE],
            mockCharacterResponses: [charMove('Ayame holds the foyer threshold tension without resolving compensation.')],
          },
        },
      });
      const dirFork = t15.causal_trace.fork_evaluations.find((f) => f.fork_id === 'FORK-LH1B-DIR-TRAJECTORY');
      proofs.push(proof('director_t15_fork_reachable', Boolean(dirFork)));
      proofs.push(proof('director_t15_llm_invoked', t15.lh1b_projection.director_llm_invoked === true));
      proofs.push(proof('director_projection_receipt', t15.lh1b_projection.director_receipt === true));
      proofs.push(proof('director_provenance', Boolean(t15.assembled_request_director)));
      proofs.push(proof('director_mock_r3_r4_positive', dirFork?.causal_evidence?.decision_influenced === true));
      proofs.push(proof('director_advisory_not_dictation', !String(
        t15.assembled_request_director?.contributions?.[0]?.content ?? '',
      ).toLowerCase().includes('choose ayame')));

      const t15neg = await runLh1bTurn({
        ...ctx,
        turnIndex: 15,
        playerStimulus: planTurns[14].player_stimulus,
        sceneId: planTurns[14].scene_id,
        sequenceId: 'lh1b-qual-dir-t15-neg',
        mockOverrides: { beatOptions: { mockDirectorResponses: [DIRECTOR_SOFTEN] } },
      });
      const dirNeg = t15neg.causal_trace.fork_evaluations.find((f) => f.fork_id === 'FORK-LH1B-DIR-TRAJECTORY');
      proofs.push(proof('director_negative_control', dirNeg?.causal_evidence?.decision_influenced !== true));
    },
  });

  await withMockSession({
    arm: LH0_ARMS.LH_A,
    evidenceRoot: root,
    client,
    openerId,
    fn: async (ctx) => {
      const t15 = await runLh1bTurn({
        ...ctx,
        turnIndex: 15,
        playerStimulus: planTurns[14].player_stimulus,
        sceneId: planTurns[14].scene_id,
        sequenceId: 'lh1b-qual-s6-t15',
      });
      proofs.push(proof('s6_lh_a_no_director_guidance', !t15.lh1b_projection.director_receipt));
    },
  });

  const fork17 = forkForTurn(FIXTURE, 17, { consumer: 'character_move' })[0];
  proofs.push(proof('complete_substrate_uniqueness_evaluator', classifyActualSubstrateUniqueness({
    fixture: FIXTURE,
    fork: fork17,
    manifestContributions: [{
      source_kind: 'active_constraints',
      content: 'Trial staff receive only a pantry submaster key.',
      provenance: { lh0_obligation_id: 'LH1B-AYA-DEFERRED-KEY' },
    }],
    playerStimulus: 'Will I receive the master key?',
  }).primary_classification != null));

  proofs.push(proof('runner_transcript_sufficiency', classifyActualSubstrateUniqueness({
    fixture: FIXTURE,
    fork: forkForTurn(FIXTURE, 16, { consumer: 'character_move' })[0],
    manifestContributions: [{
      source_kind: 'recent_scene_transcript',
      content: 'Kizzie committed not to enter any restricted area without written authorization.',
    }],
    playerStimulus: 'May I check the east wing radiator tonight?',
  }).flags.transcript_sufficient === true));

  proofs.push(proof('runner_continuity_sufficiency', classifyActualSubstrateUniqueness({
    fixture: FIXTURE,
    fork: fork17,
    manifestContributions: [],
    continuitySnapshot: { character_state: 'Trial staff receive only a pantry submaster key during trial week.' },
    playerStimulus: 'Will I receive the master key?',
  }).flags.continuity_sufficient === true));

  proofs.push(proof('runner_retrieval_sufficiency', classifyActualSubstrateUniqueness({
    fixture: FIXTURE,
    fork: forkForTurn(FIXTURE, 15, { consumer: 'character_move' })[0],
    manifestContributions: [],
    retrievalContributions: [{
      source_kind: 'indexed_retrieval',
      content: 'Previous assistant dismissed after copying household ledger pages.',
    }],
    playerStimulus: 'I could help with household accounts.',
  }).flags.retrieval_sufficient === true));

  proofs.push(proof('runner_memory_summary_sufficiency', classifyActualSubstrateUniqueness({
    fixture: FIXTURE,
    fork: fork17,
    manifestContributions: [{
      source_kind: 'character_memory',
      content: 'Trial staff receive only a pantry submaster key during trial week.',
    }],
    playerStimulus: 'Will I receive the master key?',
  }).flags.memory_or_summary_sufficient === true));

  proofs.push(proof('stop_hash_drift_gate', verifyLh1bFrozenHashes({
    scenario_key: 'ayame_controlled',
    policy_hash: '0'.repeat(64),
  }).pass === false));

  proofs.push(proof('stop_director_qualification_wiring', buildLh1bBeatOptions({
    armConfig: buildLh0ArmConfig(LH0_ARMS.LH_D),
    fixture: FIXTURE,
    turnIndex: 15,
    sessionsDir: defaultSessionsDir(),
    scenario: SCENARIO,
  }).lh1bForceDirectorInference === true));

  await client.stop();

  const failures = proofs.filter((p) => !p.pass);
  return {
    schema: LH1B_SCHEMAS.RUNNER_QUALIFICATION,
    pass: failures.length === 0,
    proof_count: proofs.length,
    proofs,
    failures: failures.map((f) => f.name),
    evidence_root: root,
    turn_ordering: LH1B_TURN_ORDERING,
  };
}
